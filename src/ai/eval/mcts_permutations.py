#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# pylint: disable=too-many-locals

import logging
import os
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import pandas
from pandas import DataFrame

from ai.cython_mcts_player.player import CythonMctsPlayer
from ai.mcts_player_options import MctsPlayerOptions
from main_wrapper import main_wrapper
from model.game_state import GameState
from model.player_action import PlayerAction, get_available_actions, \
  AnnounceMarriageAction, PlayCardAction
from model.player_id import PlayerId

_folder = os.path.join(os.path.dirname(__file__), "data")


def _get_csv_path(options: MctsPlayerOptions):
  return os.path.join(_folder,
                      f"mcts_permutations_{options.max_iterations}iter.csv")


def _play_one_trick(game_state: GameState) -> GameState:
  for _ in range(2):
    actions = get_available_actions(game_state)
    actions = [action for action in actions if
               isinstance(action, (PlayCardAction, AnnounceMarriageAction))]
    game_state = actions[0].execute(game_state)
  return game_state


def _get_dataframe_from_actions_and_scores(
    actions_and_scores: List[Tuple[PlayerAction, float]]) -> DataFrame:
  dataframe = DataFrame(
    [(score, str(action)) for action, score in actions_and_scores],
    columns=["score", "action"])
  dataframe["rank"] = dataframe["score"].sort_values().rank(method="min",
                                                            ascending=False)
  return dataframe


def _run_mcts_step_by_step(game_state: GameState,
                           options: MctsPlayerOptions) -> DataFrame:
  options.num_processes = 1
  max_permutations = options.max_permutations
  permutations = 10
  dataframes = []
  while True:
    options.max_permutations = permutations
    mcts_player = CythonMctsPlayer(game_state.next_player, False, options)
    actions_and_scores = mcts_player.get_actions_and_scores(
      game_state.next_player_view())
    dataframe = _get_dataframe_from_actions_and_scores(actions_and_scores)
    dataframe["permutations"] = permutations
    dataframes.append(dataframe)
    if max_permutations is not None and permutations >= max_permutations:
      break
    permutations += 10
  options.max_permutations = max_permutations
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
  seed = 20
  game_state = GameState.new(dealer=PlayerId.ONE, random_seed=seed)
  same_game_state_after_each_trick = {}
  for i in range(5):
    game_state = _play_one_trick(game_state)
    same_game_state_after_each_trick[
      f"GameState (seed=0), after {i + 1} trick(s) played"] = game_state
  dataframes.extend(_run_simulations(same_game_state_after_each_trick, options))
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
  for i, scenario in enumerate(scenarios):
    scenario_df = dataframe[dataframe.scenario.eq(scenario)]
    for action in scenario_df.action.drop_duplicates():
      action_df = scenario_df[scenario_df.action.eq(action)].sort_values(
        "permutations")
      axes[i, 0].plot(action_df.permutations, action_df.score, label=action)
      axes[i, 1].plot(action_df.permutations, action_df["rank"], label=action)
    axes[i, 0].set_title(scenario)
    axes[i, 0].legend(loc=0)
    axes[i, 0].hlines([1, 0.66, 0.33, 0, -0.33, -0.66, -1], xmin=0,
                      xmax=max(scenario_df.permutations), color="k", alpha=0.25,
                      linestyles="--")
    axes[i, 0].set_ylim(min(scenario_df.score) - 0.05,
                        max(scenario_df.score) + 0.05)
    axes[i, 1].set_title(scenario)
  output_png = csv_path.replace(".csv", ".png")
  plt.tight_layout()
  plt.savefig(output_png)


def main():
  options = MctsPlayerOptions(max_iterations=5000, max_permutations=150)
  _generate_data(options)
  _plot_results(options)


if __name__ == "__main__":
  main_wrapper(main)
