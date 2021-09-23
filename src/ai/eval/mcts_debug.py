#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from matplotlib import pyplot as plt
from pandas import DataFrame

from ai.cython_mcts_player.mcts_debug import run_mcts_and_collect_data, \
  run_mcts_player_step_by_step
from ai.mcts_player_options import MctsPlayerOptions
from main_wrapper import main_wrapper
from model.game_state import GameState

_hlines_for_scores = [1, 0.66, 0.33, 0, -0.33, -0.66, -1]


def _plot_data(dataframe: DataFrame, column: str, ax, hlines=None,
               confidence_columns=None):
  colors = "bgrcmyk"
  for i, action in enumerate(sorted(dataframe.action.drop_duplicates())):
    action_df = dataframe[dataframe.action.eq(action)].sort_values(
      "iteration")
    ax.plot(action_df.iteration, action_df[column], label=action,
            color=colors[i])
    if confidence_columns is not None and \
        confidence_columns[0] in dataframe.columns and \
        confidence_columns[1] in dataframe.columns:
      low = action_df[confidence_columns[0]]
      upp = action_df[confidence_columns[1]]
      ax.fill_between(action_df.iteration, low, upp, alpha=0.1, color=colors[i])
  ax.set_title(column)
  ax.legend(loc=0)
  min_value = dataframe[column].min()
  max_value = dataframe[column].max()
  ax.set_ylim(
    (min_value - 0.1 * abs(min_value), max_value + 0.1 * abs(max_value)))
  if hlines is not None:
    ax.hlines(hlines, xmin=0, xmax=max(dataframe.iteration), color="k",
              alpha=0.25, linestyles="--")


def mcts_debug(game_state: GameState, options: MctsPlayerOptions):
  print("Collecting data...")
  dataframe = run_mcts_and_collect_data(game_state, options,
                                        iterations_step=100)
  csv_path = "mcts_debug.csv"
  dataframe.to_csv(csv_path, index=False)

  print("Plotting results...")
  rows = 4
  cols = 1

  # noinspection PyTypeChecker
  _, axes = plt.subplots(rows, cols, figsize=(10 * cols, 5 * rows * cols),
                         squeeze=False, sharex=False, sharey=False)
  _plot_data(dataframe, "q", axes[0, 0], _hlines_for_scores)
  _plot_data(dataframe, "n", axes[1, 0])
  _plot_data(dataframe, "score", axes[2, 0], _hlines_for_scores,
             ("score_low", "score_upp"))
  _plot_data(dataframe, "exp_comp", axes[3, 0])
  plt.tight_layout()
  plt.savefig("mcts_debug.png")


def mcts_player_debug(game_state: GameState, options: MctsPlayerOptions):
  print("Collecting data...")
  dataframe = run_mcts_player_step_by_step(game_state, options,
                                           iterations_step=500)
  csv_path = "mcts_player_debug.csv"
  dataframe.to_csv(csv_path, index=False)

  print("Plotting results...")
  _plot_data(dataframe, "score", plt.gca(), _hlines_for_scores,
             confidence_columns=("score_low", "score_upp"))
  plt.tight_layout()
  plt.savefig("mcts_player_debug.png")


if __name__ == "__main__":
  main_wrapper(
    lambda: mcts_player_debug(GameState.new(random_seed=60).next_player_view(),
                              MctsPlayerOptions(max_iterations=4000,
                                                max_permutations=20,
                                                select_best_child=True)))
