#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# pylint: disable=too-many-locals,duplicate-code

import copy
import logging
import os
from typing import Optional, Dict, List

import matplotlib.pyplot as plt
import pandas
from pandas import DataFrame

from ai.cython_mcts_player.mcts_debug import run_mcts_player_step_by_step, \
  run_mcts_and_collect_data
from ai.eval.utils import same_game_state_after_each_trick_scenarios
from ai.mcts_player_options import MctsPlayerOptions
from main_wrapper import main_wrapper
from model.game_state import GameState
from model.game_state_test_utils import \
  get_game_state_for_you_first_no_you_first_puzzle, \
  get_game_state_for_elimination_play_puzzle, \
  get_game_state_for_playing_to_win_the_last_trick_puzzle, \
  get_game_state_for_tempo_puzzle, get_game_state_for_who_laughs_last_puzzle, \
  get_game_state_for_forcing_the_issue_puzzle, get_game_state_for_tests
from model.player_id import PlayerId

_folder = os.path.join(os.path.dirname(__file__), "data")


def _get_csv_path(cheater: bool):
  suffix = "_cheater" if cheater else ""
  return os.path.join(_folder, f"mcts_iterations{suffix}.csv")


def _run_simulations(game_states: Dict[str, GameState],
                     cheater: bool,
                     options: MctsPlayerOptions,
                     constant_budget: bool) -> List[DataFrame]:
  if constant_budget:
    return _run_simulations_with_constant_budget(game_states, cheater, options)
  dataframes = []
  for name, game_state in game_states.items():
    logging.info("Scenario: %s", name)
    game_view = game_state if cheater else game_state.next_player_view()
    dataframe = run_mcts_player_step_by_step(game_view, options,
                                             iterations_step=100)
    dataframe["scenario"] = name
    dataframes.append(dataframe)
  return dataframes


def _run_simulations_with_constant_budget(
    game_states: Dict[str, GameState],
    cheater: bool,
    input_options: MctsPlayerOptions) -> List[DataFrame]:
  dataframes = []
  max_iterations = input_options.max_iterations
  total_budget = input_options.max_permutations * input_options.max_iterations
  assert max_iterations is not None
  for name, game_state in game_states.items():
    logging.info("Scenario: %s", name)
    options = copy.copy(input_options)
    iterations = 100
    game_view = game_state if cheater else game_state.next_player_view()
    while True:
      options.max_iterations = iterations
      options.max_permutations = total_budget // options.max_iterations
      dataframe = run_mcts_player_step_by_step(game_view, options,
                                               iterations_step=iterations)
      dataframe["scenario"] = name
      dataframes.append(dataframe)
      if iterations >= max_iterations:
        break
      iterations *= 2
      iterations = min(iterations, 2500)
  return dataframes


def _generate_data(cheater: bool, options: MctsPlayerOptions,
                   constant_budget: bool):
  dataframes = []
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
  dataframes.extend(
    _run_simulations(fully_simulated_game_states, cheater, options,
                     constant_budget))
  partially_simulated_game_states = {}
  for seed in [0, 20, 40, 60, 100]:
    partially_simulated_game_states[f"Random GameState (seed={seed})"] = \
      GameState.new(dealer=PlayerId.ONE, random_seed=seed)
  dataframes.extend(
    _run_simulations(partially_simulated_game_states, cheater, options,
                     constant_budget))
  dataframes.extend(
    _run_simulations(same_game_state_after_each_trick_scenarios(20), cheater,
                     options, constant_budget))
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
  colors = "bgrcmyk"
  for i, scenario in enumerate(scenarios):
    scenario_df = dataframe[dataframe.scenario.eq(scenario)]
    for j, action in enumerate(scenario_df.action.drop_duplicates()):
      action_df = scenario_df[scenario_df.action.eq(action)].sort_values(
        "iteration")
      axes[i, 0].plot(action_df.iteration, action_df.score, label=action,
                      color=colors[j])
      axes[i, 0].fill_between(action_df.iteration, action_df.score_low,
                              action_df.score_upp, alpha=0.1,
                              color=colors[j])
      axes[i, 1].plot(action_df.iteration, action_df["rank"], label=action,
                      color=colors[j])
    axes[i, 0].set_title(scenario)
    axes[i, 0].legend(loc=0)
    axes[i, 0].hlines([1, 0.66, 0.33, 0, -0.33, -0.66, -1], xmin=0,
                      xmax=max(scenario_df.iteration), color="k", alpha=0.25,
                      linestyles="--")
    axes[i, 0].set_ylim(min(scenario_df.score) - 0.05,
                        max(scenario_df.score) + 0.05)
    axes[i, 1].set_title(scenario)
    if max(scenario_df.iteration) > 10000:
      axes[i, 0].set_xscale("log")
      axes[i, 1].set_xscale("log")
  suffix = "_cheater" if cheater else ""
  plt.tight_layout()
  plt.savefig(os.path.join(_folder, f"mcts_iterations{suffix}.png"))


def _min_iterations_to_find_the_best_action(
    num_game_states: int = 100,
    cheater: bool = True,
    num_samples_per_game_state: int = 10,
    options: Optional[MctsPlayerOptions] = None):
  """
  This functions computes the number of iterations required until the best
  action seems to be found. It looks for the moment when an action becomes the
  best action and it remains the best action even if we continue to run up to
  max_iterations iterations. It measures this for num_game_states different game
  states and plots a histogram.
  """
  options = options or MctsPlayerOptions()
  data = []
  for seed in range(num_game_states):
    for sample_index in range(num_samples_per_game_state):
      game_state = GameState.new(dealer=PlayerId.ONE, random_seed=seed)
      dataframe = run_mcts_and_collect_data(game_state, options)
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
  suffix = "_cheater" if cheater else f"_{options.max_permutations}perm"
  csv_path = os.path.join(_folder,
                          f"min_iterations_to_find_the_best_action{suffix}.csv")
  # noinspection PyTypeChecker
  dataframe.to_csv(csv_path, index=False)
  # dataframe = pandas.read_csv(csv_path)
  fig, ax = plt.subplots()
  ax2 = ax.twinx()
  dataframe.iteration.hist(color="b", linewidth=3, ax=ax)
  dataframe.iteration.plot(kind="kde", label="Overall", color="r", linewidth=3,
                           ax=ax2)
  plt.legend(loc=0)
  plt.xlabel("Iterations")
  title_suffix = \
    "" if cheater else f" ({options.max_permutations} permutations)"
  plt.title(
    f"Number of iterations until the best action is found{title_suffix}")
  fig.set_size_inches(10, 5)
  fig.savefig(
    os.path.join(_folder,
                 f"min_iterations_to_find_the_best_action{suffix}.png"))
  logging.info("Overall results: %s", dataframe.iteration.describe())
  logging.info("Value counts: %s", dataframe.iteration.value_counts())


def main():
  cheater = False
  options = MctsPlayerOptions(max_iterations=2500, max_permutations=40,
                              select_best_child=True)
  _generate_data(cheater, options, constant_budget=True)
  _plot_results(cheater)
  # _min_iterations_to_find_the_best_action(num_game_states=100, cheater=cheater,
  #                                         num_samples_per_game_state=1,
  #                                         options=options)


if __name__ == "__main__":
  main_wrapper(main)
