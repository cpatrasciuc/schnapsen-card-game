#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# pylint: disable=too-many-locals,duplicate-code

import copy
import logging
import os
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas
from pandas import DataFrame

from ai.cython_mcts_player.mcts_debug import run_mcts_player_step_by_step
from ai.eval.utils import same_game_state_after_each_trick_scenarios
from ai.mcts_player_options import MctsPlayerOptions
from ai.merge_scoring_infos_func_with_deps import lower_ci_bound_on_raw_rewards
from main_wrapper import main_wrapper
from model.game_state import GameState
from model.player_id import PlayerId

_folder = os.path.join(os.path.dirname(__file__), "data")


def _get_csv_path(options: MctsPlayerOptions):
  return os.path.join(_folder,
                      f"mcts_permutations_{options.max_iterations}iter.csv")


def _run_mcts_step_by_step(game_state: GameState,
                           input_options: MctsPlayerOptions,
                           constant_budget: bool = True) -> DataFrame:
  options = copy.copy(input_options)
  options.num_processes = 1
  max_permutations = options.max_permutations
  total_budget = options.max_permutations * options.max_iterations
  permutations = 10
  dataframes = []
  while True:
    options.max_permutations = permutations
    if constant_budget:
      options.max_iterations = total_budget // options.max_permutations
    dataframe = run_mcts_player_step_by_step(game_state.next_player_view(),
                                             options, options.max_iterations)
    dataframe["permutations"] = permutations
    dataframes.append(dataframe)
    if max_permutations is not None and permutations >= max_permutations:
      break
    permutations *= 2
    permutations = min(permutations, 250)
  return pandas.concat(dataframes, ignore_index=True)


def _run_simulations(game_states: Dict[str, GameState],
                     options: MctsPlayerOptions) -> List[DataFrame]:
  dataframes = []
  for name, game_state in game_states.items():
    logging.info("Scenario: %s", name)
    dataframe = _run_mcts_step_by_step(game_state, options)
    dataframe["scenario"] = name
    dataframes.append(dataframe)
  return dataframes


def _generate_data(options: MctsPlayerOptions):
  partially_simulated_game_states = {}
  for seed in [0, 20, 40, 60, 100]:
    partially_simulated_game_states[f"Random GameState (seed={seed})"] = \
      GameState.new(dealer=PlayerId.ONE, random_seed=seed)
  dataframes = _run_simulations(partially_simulated_game_states, options)
  dataframes.extend(
    _run_simulations(same_game_state_after_each_trick_scenarios(20), options))
  dataframe = pandas.concat(dataframes, ignore_index=True)
  # noinspection PyTypeChecker
  dataframe.to_csv(_get_csv_path(options), index=False)


def _plot_results(options: MctsPlayerOptions):
  # pylint: disable=no-member,unsubscriptable-object
  logging.info("Plotting results")
  csv_path = _get_csv_path(options)
  dataframe: DataFrame = pandas.read_csv(csv_path)
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
        "permutations")
      axes[i, 0].plot(action_df.permutations, action_df.score, label=action,
                      color=colors[j])
      if "score_low" in action_df.columns:
        axes[i, 0].fill_between(action_df.permutations, action_df.score_low,
                                action_df.score_upp, alpha=0.1,
                                color=colors[j])
      axes[i, 1].plot(action_df.permutations, action_df["rank"], label=action,
                      color=colors[j])
    axes[i, 0].set_title(scenario)
    axes[i, 0].legend(loc=0)
    axes[i, 0].hlines([1, 0.66, 0.33, 0, -0.33, -0.66, -1], xmin=0,
                      xmax=max(scenario_df.permutations), color="k", alpha=0.25,
                      linestyles="--")
    axes[i, 0].set_ylim(min(scenario_df.score) - 0.05,
                        max(scenario_df.score) + 0.05)
    axes[i, 1].set_title(scenario)
    axes[i, 0].set_xscale("log")
    axes[i, 1].set_xscale("log")
  output_png = csv_path.replace(".csv", ".png")
  plt.tight_layout()
  plt.savefig(output_png)


def main():
  options = MctsPlayerOptions(
    max_iterations=667, max_permutations=150, save_rewards=True,
    merge_scoring_info_func=lower_ci_bound_on_raw_rewards)
  _generate_data(options)
  _plot_results(options)


if __name__ == "__main__":
  main_wrapper(main)
