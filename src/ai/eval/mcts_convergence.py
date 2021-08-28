#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# pylint: disable=too-many-locals

import logging
import multiprocessing
import os
from multiprocessing.connection import Connection, Pipe
from typing import Optional, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas
from pandas import DataFrame

from ai.mcts_algorithm import MCTS, SchnapsenNode, ucb_for_player
from ai.permutations import sims_table_perm_generator
from ai.utils import get_unseen_cards, populate_game_view
from model.game_state import GameState
from model.game_state_test_utils import \
  get_game_state_for_you_first_no_you_first_puzzle, \
  get_game_state_for_elimination_play_puzzle, \
  get_game_state_for_playing_to_win_the_last_trick_puzzle, \
  get_game_state_for_tempo_puzzle, get_game_state_for_who_laughs_last_puzzle, \
  get_game_state_for_forcing_the_issue_puzzle, get_game_state_for_tests
from model.player_action import PlayerAction
from model.player_id import PlayerId

STEP = 100

_folder = os.path.join(os.path.dirname(__file__), "data")


def _get_csv_path(cheater: bool):
  suffix = "_cheater" if cheater else ""
  return os.path.join(_folder, f"mcts_convergence{suffix}.csv")


def _add_action_rank_column(dataframe: DataFrame):
  dataframe["rank"] = dataframe["score"].sort_values().rank(method="min",
                                                            ascending=False)


def _get_children_data(node: SchnapsenNode) -> DataFrame:
  children_and_scores = \
    [(ucb_for_player(child, node.player), str(action))
     for action, child in node.children.items() if child is not None]
  dataframe = DataFrame(children_and_scores, columns=["score", "action"])
  _add_action_rank_column(dataframe)
  return dataframe


def _get_dataframe_from_actions_and_scores(
    actions_and_scores: List[Tuple[PlayerAction, float]]) -> DataFrame:
  dataframe = DataFrame(
    [(score, str(action)) for action, score in actions_and_scores],
    columns=["score", "action"])
  _add_action_rank_column(dataframe)
  return dataframe


def _run_simulation_out_of_process(game_state: GameState,
                                   max_iterations: Optional[int],
                                   output: Connection):
  player_id = game_state.next_player
  mcts = MCTS(player_id)
  root_node = SchnapsenNode(game_state, None)
  iteration = 0
  is_fully_simulated = False
  while True:
    iteration += STEP
    for _ in range(STEP):
      is_fully_simulated = mcts.run_one_iteration(root_node)
      if is_fully_simulated:
        break
    actions_and_scores = [
      (action, child.ucb if child.player == player_id else -child.ucb)
      for action, child in root_node.children.items() if child is not None]
    output.send(actions_and_scores)
    output.send(is_fully_simulated)
    if is_fully_simulated:
      break
    if max_iterations is not None and iteration >= max_iterations:
      break
  output.close()


def _simulate_game_view(game_view: GameState,
                        max_iterations: Optional[int],
                        max_permutations: Optional[int] = 7) -> DataFrame:
  if max_permutations > multiprocessing.cpu_count() - 1:
    raise ValueError("Too many permutations")
  cards_set = get_unseen_cards(game_view)
  player_id = game_view.next_player
  num_opponent_unknown_cards = len(
    [card for card in game_view.cards_in_hand[player_id.opponent()] if
     card is None])
  permutations = sims_table_perm_generator(cards_set,
                                           num_opponent_unknown_cards,
                                           max_permutations)
  game_states = [populate_game_view(game_view, permutation) for permutation in
                 permutations]
  pipes = [Pipe(duplex=False) for _ in range(len(permutations))]
  processes = [multiprocessing.Process(target=_run_simulation_out_of_process,
                                       args=(
                                         game_state, max_iterations, pipe[1]))
               for game_state, pipe in zip(game_states, pipes)]
  for process in processes:
    process.start()
  iteration = 0
  dataframes = []
  actions_and_scores_for_each_permutation = [[] for _ in game_states]
  is_fully_simulated = [False for _ in game_states]
  while True:
    iteration += STEP
    for i, pipe in enumerate(pipes):
      if is_fully_simulated[i]:
        continue
      actions_and_scores_for_each_permutation[i] = pipe[0].recv()
      is_fully_simulated[i] = pipe[0].recv()
    stats: Dict[PlayerAction, List[float]] = {}
    for actions_and_scores in actions_and_scores_for_each_permutation:
      for action, score in actions_and_scores:
        stats[action] = stats.get(action, []) + [score]
    merged_actions_and_scores = \
      [(action, float(np.mean(scores))) for action, scores in stats.items()]
    dataframe = _get_dataframe_from_actions_and_scores(
      merged_actions_and_scores)
    dataframe["iteration"] = iteration
    dataframes.append(dataframe)
    if np.all(is_fully_simulated):
      break
    if max_iterations is not None and iteration >= max_iterations:
      break
  for process in processes:
    process.join()
  return pandas.concat(dataframes, ignore_index=True)


def _simulate_game_state(game_state: GameState,
                         max_iterations: Optional[int]) -> DataFrame:
  mcts = MCTS(game_state.next_player)
  root_node = SchnapsenNode(game_state, None)
  iteration = 0
  dataframes = []
  while True:
    iteration += 1
    is_fully_simulated = mcts.run_one_iteration(root_node)
    dataframe = _get_children_data(root_node)
    dataframe["iteration"] = iteration
    dataframes.append(dataframe)
    if is_fully_simulated:
      break
    if max_iterations is not None and iteration >= max_iterations:
      break
  return pandas.concat(dataframes, ignore_index=True)


def _run_simulations(game_states: Dict[str, GameState],
                     cheater: bool,
                     max_iterations: Optional[int]) -> List[DataFrame]:
  dataframes = []
  for name, game_state in game_states.items():
    logging.info("Scenario: %s", name)
    if cheater:
      dataframe = _simulate_game_state(game_state, max_iterations)
    else:
      dataframe = _simulate_game_view(game_state.next_player_view(),
                                      max_iterations)
    dataframe["scenario"] = name
    dataframes.append(dataframe)
  return dataframes


def _generate_data(cheater: bool, max_iterations: int = 10000):
  fully_simulated_game_states = {
    "You first. No, you first":
      get_game_state_for_you_first_no_you_first_puzzle(),
    "Elimination play": get_game_state_for_elimination_play_puzzle(),
    "Playing to win the last trick":
      get_game_state_for_playing_to_win_the_last_trick_puzzle(),
    "Tempo": get_game_state_for_tempo_puzzle(),
    "Who laughs last": get_game_state_for_who_laughs_last_puzzle(),
    "Forcing the issue": get_game_state_for_forcing_the_issue_puzzle(),
    "Game state for tests": get_game_state_for_tests(),
  }
  dataframes = _run_simulations(fully_simulated_game_states, cheater,
                                max_iterations)
  partially_simulated_game_states = {}
  for seed in [0, 20, 40, 60, 100]:
    partially_simulated_game_states[f"Random GameState (seed={seed})"] = \
      GameState.new(dealer=PlayerId.ONE, random_seed=seed)
  dataframes.extend(
    _run_simulations(partially_simulated_game_states, cheater, max_iterations))
  dataframe = pandas.concat(dataframes, ignore_index=True)
  # noinspection PyTypeChecker
  dataframe.to_csv(_get_csv_path(cheater), index=False)


def _plot_results(cheater: bool):
  # pylint: disable=no-member,unsubscriptable-object
  logging.info("Plotting results")
  dataframe: DataFrame = pandas.read_csv(_get_csv_path(cheater))
  scenarios = dataframe.scenario.drop_duplicates()
  num_scenarios = len(scenarios)
  # noinspection PyTypeChecker
  _, axes = plt.subplots(num_scenarios, 2, figsize=(20, 5 * num_scenarios),
                         squeeze=False, sharex=False, sharey=False)
  for i, scenario in enumerate(scenarios):
    scenario_df = dataframe[dataframe.scenario.eq(scenario)]
    for action in scenario_df.action.drop_duplicates():
      action_df = scenario_df[scenario_df.action.eq(action)].sort_values(
        "iteration")
      axes[i, 0].plot(action_df.iteration, action_df.score, label=action)
      axes[i, 1].plot(action_df.iteration, action_df["rank"], label=action)
    axes[i, 0].set_title(scenario)
    axes[i, 0].legend(loc=0)
    axes[i, 0].hlines([1, 0.66, 0.33, 0, -0.33, -0.66, -1], xmin=0,
                      xmax=max(scenario_df.iteration), color="k", alpha=0.25,
                      linestyles="--")
    axes[i, 0].set_ylim(min(scenario_df.score) - 0.05,
                        max(scenario_df.score) + 0.05)
    axes[i, 1].set_title(scenario)
  suffix = "_cheater" if cheater else ""
  plt.savefig(os.path.join(_folder, f"mcts_convergence{suffix}.png"))


def _min_iterations_to_find_the_best_action(
    num_game_states: int = 100,
    cheater: bool = True,
    num_samples_per_game_state: int = 10,
    max_iterations: int = 10000):
  """
  This functions computes the number of iterations required until the best
  action seems to be found. It looks for the moment when an action becomes the
  best action and it remains the best action even if we continue to run up to
  max_iterations iterations. It measures this for num_game_states different game
  states and plots a histogram.
  """
  max_permutations = 7
  data = []
  for seed in range(num_game_states):
    for sample_index in range(num_samples_per_game_state):
      game_state = GameState.new(dealer=PlayerId.ONE, random_seed=seed)
      if cheater:
        dataframe = _simulate_game_state(game_state, max_iterations)
      else:
        dataframe = _simulate_game_view(game_state.next_player_view(),
                                        max_iterations, max_permutations)
      last_iteration = dataframe.iteration.max()
      best_actions = dataframe[
        dataframe.iteration.eq(last_iteration) & dataframe["rank"].eq(
          1)].action
      best_actions_per_iteration = dataframe[dataframe["rank"].eq(1)]
      iterations_with_other_best_actions = [
        iteration for iteration in dataframe.iteration.drop_duplicates() if
        iteration not in best_actions_per_iteration[
          best_actions_per_iteration.action.isin(
            best_actions)].iteration.values]
      found_at_iteration = 0
      if len(iterations_with_other_best_actions) > 0:
        found_at_iteration = max(iterations_with_other_best_actions)
      best_action = min(best_actions)
      logging.info("Best action for seed %s: %s, found at iteration %s",
                   seed, best_action, found_at_iteration)
      data.append((seed, sample_index, best_action, found_at_iteration))
  dataframe = DataFrame(data,
                        columns=["seed", "sample_index", "action", "iteration"])
  suffix = "_cheater" if cheater else f"_{max_permutations}perm"
  csv_path = os.path.join(_folder,
                          f"min_iterations_to_find_the_best_action{suffix}.csv")
  # noinspection PyTypeChecker
  dataframe.to_csv(csv_path, index=False)
  # dataframe = pandas.read_csv(csv_path)
  dataframe.iteration.plot(kind="kde", label="Overall", color="r", linewidth=3)
  for seed in dataframe.seed.drop_duplicates():
    filtered_dataframe = dataframe[dataframe.seed.eq(seed)]
    filtered_dataframe.iteration.plot(kind="kde", alpha=0.5,
                                      label=f"GameState.new(seed={seed})")
  plt.legend(loc=0)
  plt.xlabel("Iterations")
  title_suffix = "" if cheater else f" ({max_permutations} permutations)"
  plt.title(
    f"Number of iterations until the best action is found{title_suffix}")
  plt.gcf().set_size_inches(10, 5)
  plt.savefig(
    os.path.join(_folder,
                 f"min_iterations_to_find_the_best_action{suffix}.png"))
  logging.info("Overall results: %s", dataframe.iteration.describe())


if __name__ == "__main__":
  logging.basicConfig(level=logging.DEBUG)
  # _generate_data(False)
  # _plot_results(False)
  _min_iterations_to_find_the_best_action(10, False, 10, 10000)
