#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import logging
import os
import time

import matplotlib.pyplot as plt
from cpuinfo import cpuinfo
from pandas import DataFrame

from ai.mcts_algorithm import MCTS
from model.game_state import GameState


def iterations_and_time():
  data = []
  for seed in range(10):
    game_state = GameState.new(random_seed=seed)
    iterations = 10
    duration_sec = 0
    while duration_sec < 10:
      mcts = MCTS(game_state.next_player)
      start_time = time.process_time()
      mcts.build_tree(game_state, iterations)
      end_time = time.process_time()
      duration_sec = end_time - start_time
      logging.info("Run %s iterations in %.5f seconds (seed=%s)", iterations,
                   duration_sec, seed)
      data.append((seed, iterations, duration_sec))
      iterations *= 2
  dataframe = DataFrame(data, columns=["seed", "iterations", "duration_sec"])
  folder = os.path.join(os.path.dirname(__file__), "data")
  csv_path = os.path.join(folder, "iterations_and_time.csv")
  # noinspection PyTypeChecker
  dataframe.to_csv(csv_path, index=False)
  for seed in sorted(dataframe.seed.drop_duplicates()):
    filtered_dataframe = dataframe[dataframe["seed"].eq(seed)]
    plt.plot(filtered_dataframe.iterations, filtered_dataframe.duration_sec,
             label=f"seed={seed}")
    plt.scatter(filtered_dataframe.iterations, filtered_dataframe.duration_sec,
                s=10)
  plt.grid(which="both", linestyle="--")
  plt.legend(loc=0)
  plt.xlabel("Iterations")
  plt.ylabel("Duration (seconds)")
  plt.xscale("log")
  plt.title(cpuinfo.get_cpu_info()["brand_raw"])
  plt.savefig(os.path.join(folder, "iterations_and_time.png"))


if __name__ == "__main__":
  logging.basicConfig(level=logging.DEBUG)
  iterations_and_time()
