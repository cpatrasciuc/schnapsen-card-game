#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import functools
import multiprocessing
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import DataFrame

from ai.cython_mcts_player.mcts_debug import overlap_between_mcts_and_heuristic
from ai.eval.utils import same_game_state_after_each_trick_scenarios
from ai.mcts_player_options import MctsPlayerOptions
from main_wrapper import main_wrapper
from model.game_state import GameState


def _get_overlap_for_seed(seed: int, options: MctsPlayerOptions) -> DataFrame:
  print(f"Processing GameState(random_seed={seed})")
  initial_game_state = GameState.new(random_seed=seed)
  game_states_after_n_tricks = same_game_state_after_each_trick_scenarios(seed)
  game_states = [initial_game_state] + list(game_states_after_n_tricks.values())
  dataframes = [overlap_between_mcts_and_heuristic(game_state, options)
                for game_state in game_states]
  dataframe = pd.concat(dataframes, ignore_index=True)
  return dataframe[dataframe.max_visits.gt(10)]


# NOTE: This was submitted just in case it can be reused/repurposed in the
# future. Measuring in how many instances the most visited node corresponds to
# the action deemed best by the HeuristicPlayer is not relevant. We don't want
# to maximize this overlap since we want the MctsPlayer to be better, so there
# must be instances where it considers other actions as being the best. Also,
# the maximum overlap can be achieved if we visit all nodes equally (e.g.,
# random selection), but that doesn't lead to a better player.
def get_overlap_for_multiple_game_states():
  num_seeds = 10
  options = MctsPlayerOptions(num_processes=1, max_iterations=667,
                              max_permutations=150)

  # Process the game states and extract the data.
  with multiprocessing.Pool(processes=4) as pool:
    dataframes = pool.map(
      functools.partial(_get_overlap_for_seed, options=options),
      list(range(num_seeds)))
  dataframe = pd.concat(dataframes, ignore_index=True)

  # Save to CSV.
  file_template = os.path.join(os.path.dirname(__file__), "data",
                               "overlap_between_mcts_and_heuristic")
  # noinspection PyTypeChecker
  dataframe.to_csv(f"{file_template}.csv", index=False)

  # Compute additional metrics.
  dataframe["diff_visits"] = \
    dataframe["max_visits"] - dataframe["heuristic_visits"]
  dataframe["diff_visits_pct"] = \
    dataframe["diff_visits"] / dataframe["max_visits"]

  # Print results.
  print(dataframe.describe())

  # Generate plots.
  fig, axes = plt.subplots(nrows=2, ncols=1, squeeze=False)
  dataframe.plot.scatter(x="max_visits", y="heuristic_visits", alpha=0.02,
                         ax=axes[0, 0])
  fit = np.polyfit(dataframe["max_visits"], dataframe["heuristic_visits"], 1)
  regression = np.poly1d(fit)
  dataframe["reg"] = regression(dataframe["max_visits"])
  axes[0, 0].plot(dataframe.max_visits, dataframe.reg, color="r")
  axes[1, 0].hist(dataframe.heuristic_rank, bins=list(range(8)), density=True,
                  rwidth=0.9, align="left")
  axes[1, 0].set_xlabel("Rank of the action deemed best by the HeuristicPlayer")
  axes[1, 0].set_ylabel("Fraction of nodes")
  fig.set_size_inches(5, 5)
  plt.suptitle("Overlap between Heuristic and Mcts")
  plt.tight_layout()
  plt.savefig(f"{file_template}.png")


if __name__ == "__main__":
  main_wrapper(get_overlap_for_multiple_game_states)
