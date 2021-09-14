#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import logging
import os
import timeit

import matplotlib.pyplot as plt
from cpuinfo import cpuinfo
from pandas import DataFrame

from ai.cython_mcts_player.player import CythonMctsPlayer
from ai.mcts_player_options import MctsPlayerOptions
from main_wrapper import main_wrapper
from model.game_state import GameState

NUM_SEEDS = 10


def num_threads_and_time(class_under_test, options: MctsPlayerOptions):
  # pylint: disable=too-many-locals,cell-var-from-loop
  data = []
  for seed in range(NUM_SEEDS):
    game_state = GameState.new(random_seed=seed)
    for num_threads in [1, 2, 4, 6, 8]:
      options.num_processes = num_threads
      mcts = class_under_test(game_state.next_player, cheater=False,
                              options=options)
      timer = timeit.Timer(
        lambda: mcts.request_next_action(game_state.next_player_view()))
      number, time_taken = timer.autorange()
      duration_sec = time_taken / number
      logging.info("Mcts took %.5f seconds using %d threads (seed=%s)",
                   duration_sec, num_threads, seed)
      data.append((seed, num_threads, duration_sec))
      mcts.cleanup()

  # Save the dataframe with the timing info.
  dataframe = DataFrame(data, columns=["seed", "num_threads", "duration_sec"])
  folder = os.path.join(os.path.dirname(__file__), "data")
  csv_path = os.path.join(folder, "num_threads_and_time.csv")
  # noinspection PyTypeChecker
  dataframe.to_csv(csv_path, index=False)

  # Plot the timing data obtained.
  for seed in sorted(dataframe.seed.drop_duplicates()):
    filtered_dataframe = dataframe[dataframe["seed"].eq(seed)]
    plt.plot(filtered_dataframe.num_threads, filtered_dataframe.duration_sec,
             label=None, alpha=0.5)
    plt.scatter(filtered_dataframe.num_threads, filtered_dataframe.duration_sec,
                s=10)
  mean = dataframe.groupby("num_threads").mean().sort_index()
  plt.plot(mean.index, mean.duration_sec, label="Average", color="r",
           linewidth=3)
  plt.grid(which="both", linestyle="--")
  plt.legend(loc=0)
  plt.xlabel("Number of threads")
  plt.ylabel("Duration (seconds)")
  plt.title(f"{class_under_test.__name__}: " +
            f"{options.max_permutations} permutations x " +
            f"{options.max_iterations} iterations on\n" +
            cpuinfo.get_cpu_info()["brand_raw"])
  plt.savefig(os.path.join(folder, "num_threads_and_time.png"))


def _main():
  options = MctsPlayerOptions(max_iterations=4000, max_permutations=100)
  num_threads_and_time(CythonMctsPlayer, options)


if __name__ == "__main__":
  main_wrapper(_main)
