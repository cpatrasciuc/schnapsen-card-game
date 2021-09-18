#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import math

from matplotlib import pyplot as plt
from pandas import DataFrame

from ai.cython_mcts_player.mcts_debug import run_mcts_and_collect_data
from ai.mcts_player_options import MctsPlayerOptions
from main_wrapper import main_wrapper
from model.game_state import GameState


def _plot_data(dataframe: DataFrame, column: str, ax, hlines=None):
  for action in sorted(dataframe.action.drop_duplicates()):
    action_df = dataframe[dataframe.action.eq(action)].sort_values(
      "iteration")
    ax.plot(action_df.iteration, action_df[column], label=action)
  ax.set_title(column)
  ax.legend(loc=0)
  if hlines is not None:
    ax.hlines(hlines, xmin=0, xmax=max(dataframe.iteration), color="k",
              alpha=0.25, linestyles="--")


def mcts_debug(game_state: GameState, options: MctsPlayerOptions):
  print("Collecting data...")
  dataframe = run_mcts_and_collect_data(game_state, options)
  csv_path = "mcts_debug.csv"
  dataframe.to_csv(csv_path, index=False)

  print("Plotting results...")
  rows = 4
  cols = 1

  # noinspection PyTypeChecker
  _, axes = plt.subplots(rows, cols, figsize=(10 * cols, 5 * rows * cols),
                         squeeze=False, sharex=False, sharey=False)

  hlines_for_scores = [1, 0.66, 0.33, 0, -0.33, -0.66, -1]
  _plot_data(dataframe, "q", axes[0, 0], hlines_for_scores)
  _plot_data(dataframe, "n", axes[1, 0])
  # TODO(mcts): Add some confidence boundaries to this plot.
  _plot_data(dataframe, "score", axes[2, 0], hlines_for_scores)
  _plot_data(dataframe, "exp_comp", axes[3, 0])

  plt.tight_layout()
  plt.savefig("mcts_debug.png")


if __name__ == "__main__":
  main_wrapper(
    lambda: mcts_debug(GameState.new(random_seed=0),
                       MctsPlayerOptions(max_iterations=25000,
                                         exploration_param=1 / math.sqrt(2),
                                         select_best_child=True)))
