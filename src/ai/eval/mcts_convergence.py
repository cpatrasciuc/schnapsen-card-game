#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import logging
import os
from typing import Optional, Dict, List

import matplotlib.pyplot as plt
import pandas
from pandas import DataFrame

from ai.mcts_algorithm import MCTS, SchnapsenNode, ucb_for_player
from model.game_state import GameState
from model.game_state_test_utils import \
  get_game_state_for_you_first_no_you_first_puzzle, \
  get_game_state_for_elimination_play_puzzle, \
  get_game_state_for_playing_to_win_the_last_trick_puzzle, \
  get_game_state_for_tempo_puzzle, get_game_state_for_who_laughs_last_puzzle, \
  get_game_state_for_forcing_the_issue_puzzle, get_game_state_for_tests
from model.player_id import PlayerId

_folder = os.path.join(os.path.dirname(__file__), "data")
_csv_path = os.path.join(_folder, "mcts_convergence.csv")


def _get_children_data(node: SchnapsenNode) -> DataFrame:
  children_and_scores = \
    [(ucb_for_player(child, node.player), str(action))
     for action, child in node.children.items() if child is not None]
  dataframe = DataFrame(children_and_scores, columns=["score", "action"])
  dataframe["rank"] = dataframe["score"].sort_values().rank(method="min",
                                                            ascending=False)
  return dataframe


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
                     max_iterations: Optional[int]) -> List[DataFrame]:
  dataframes = []
  for name, game_state in game_states.items():
    logging.info("Scenario: %s", name)
    dataframe = _simulate_game_state(game_state, max_iterations)
    dataframe["scenario"] = name
    dataframes.append(dataframe)
  return dataframes


def _generate_data():
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
  dataframes = _run_simulations(fully_simulated_game_states, None)
  partially_simulated_game_states = {}
  for seed in [0, 20, 40, 60, 100]:
    partially_simulated_game_states[f"Random GameState (seed={seed})"] = \
      GameState.new(dealer=PlayerId.ONE, random_seed=seed)
  dataframes.extend(_run_simulations(partially_simulated_game_states, 10000))
  dataframe = pandas.concat(dataframes, ignore_index=True)
  # noinspection PyTypeChecker
  dataframe.to_csv(_csv_path, index=False)


def _plot_results():
  # pylint: disable=no-member,unsubscriptable-object
  logging.info("Plotting results")
  dataframe: DataFrame = pandas.read_csv(_csv_path)
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
  plt.savefig(os.path.join(_folder, "mcts_convergence.png"))


def _min_iterations_to_find_the_best_action(
    num_game_states: int = 100,
    num_samples_per_game_state: int = 10,
    max_iterations: int = 10000):
  """
  This functions computes the number of iterations required until the best
  action seems to be found. It looks for the moment when an action becomes the
  best action and it remains the best action even if we continue to run up to
  max_iterations iterations. It measures this for num_game_states different game
  states and plots a histogram.
  """
  data = []
  for seed in range(num_game_states):
    for sample_index in range(num_samples_per_game_state):
      game_state = GameState.new(dealer=PlayerId.ONE, random_seed=seed)
      dataframe = _simulate_game_state(game_state, max_iterations)
      last_iteration = dataframe.iteration.max()
      best_actions = dataframe[
        dataframe.iteration.eq(last_iteration) & dataframe["rank"].eq(
          1)].action
      best_actions_per_iteration = dataframe[dataframe["rank"].eq(1)]
      found_at_iteration = max(
        iteration for iteration in range(last_iteration) if
        iteration not in best_actions_per_iteration[
          best_actions_per_iteration.action.isin(
            best_actions)].iteration.values)
      best_action = min(best_actions)
      logging.info("Best action for seed %s: %s, found at iteration %s",
                   seed, best_action, found_at_iteration)
      data.append((seed, sample_index, best_action, found_at_iteration))
  dataframe = DataFrame(data,
                        columns=["seed", "sample_index", "action", "iteration"])
  csv_path = os.path.join(_folder, "min_iterations_to_find_the_best_action.csv")
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
  plt.title("Number of iterations until the best action is found")
  plt.gcf().set_size_inches(10, 5)
  plt.savefig(
    os.path.join(_folder, "min_iterations_to_find_the_best_action.png"))
  logging.info("Overall results: %s", dataframe.iteration.describe())


if __name__ == "__main__":
  logging.basicConfig(level=logging.DEBUG)
  _generate_data()
  _plot_results()
  _min_iterations_to_find_the_best_action(10, 10)
