#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import cProfile
import logging
import multiprocessing
import os
import pstats
import timeit
from pstats import SortKey
from typing import Callable, Tuple

import matplotlib.pyplot as plt
from cpuinfo import cpuinfo
from pandas import DataFrame

from ai.cython_mcts_player.player import CythonMctsPlayer
from ai.mcts_player_options import MctsPlayerOptions
from main_wrapper import main_wrapper
from model.game_state import GameState

NUM_SEEDS = 10


def _get_file_suffix(max_permutations):
  return "" if max_permutations == 1 else f"_{max_permutations}perm"


Closure = Callable[[], None]


def _get_algorithm_closure(game_state: GameState,
                           iterations: int) -> Tuple[Closure, Closure]:
  mcts = CythonMctsPlayer(game_state.next_player, cheater=True,
                          options=MctsPlayerOptions(
                            max_permutations=10,  # Won't matter if cheater=True
                            max_iterations=iterations,
                            num_processes=1))

  def _run():
    mcts.request_next_action(game_state)

  return _run, mcts.cleanup


def _get_player_closure(game_state: GameState,
                        iterations: int,
                        max_permutations: int) -> Tuple[Closure, Closure]:
  mcts = CythonMctsPlayer(game_state.next_player, cheater=False,
                          options=MctsPlayerOptions(
                            max_permutations=max_permutations,
                            max_iterations=iterations,
                            num_processes=1))

  def _run():
    mcts.request_next_action(game_state.next_player_view())

  return _run, mcts.cleanup


def iterations_and_time(max_permutations: int):
  # pylint: disable=too-many-locals
  data = []
  for seed in range(NUM_SEEDS):
    game_state = GameState.new(random_seed=seed)
    iterations = 10
    duration_sec = 0
    while duration_sec < 10:
      if max_permutations == 1:
        closure_to_profile, cleanup = _get_algorithm_closure(game_state,
                                                             iterations)
      else:
        closure_to_profile, cleanup = _get_player_closure(game_state,
                                                          iterations,
                                                          max_permutations)
      timer = timeit.Timer(closure_to_profile)
      number, time_taken = timer.autorange()
      duration_sec = time_taken / number
      logging.info("Run %s iterations in %.5f seconds (seed=%s)", iterations,
                   duration_sec, seed)
      data.append((seed, iterations, duration_sec))
      cleanup()
      iterations *= 2

  suffix = _get_file_suffix(max_permutations)

  # Save the dataframe with the timing info.
  dataframe = DataFrame(data, columns=["seed", "iterations", "duration_sec"])
  folder = os.path.join(os.path.dirname(__file__), "data")
  csv_path = os.path.join(folder, f"iterations_and_time{suffix}.csv")
  # noinspection PyTypeChecker
  dataframe.to_csv(csv_path, index=False)

  # Plot the timing data obtained.
  for seed in sorted(dataframe.seed.drop_duplicates()):
    filtered_dataframe = dataframe[dataframe["seed"].eq(seed)]
    plt.plot(filtered_dataframe.iterations, filtered_dataframe.duration_sec,
             label=f"seed={seed}", alpha=0.5)
    plt.scatter(filtered_dataframe.iterations, filtered_dataframe.duration_sec,
                s=10)
  mean = dataframe.groupby("iterations").mean().sort_index()
  plt.plot(mean.index, mean.duration_sec, label="Average", color="r",
           linewidth=3)
  plt.grid(which="both", linestyle="--")
  plt.legend(loc=0)
  plt.xlabel("Iterations")
  plt.ylabel("Duration (seconds)")
  plt.xscale("log")
  plt.yscale("log")
  plt.title(cpuinfo.get_cpu_info()["brand_raw"])
  plt.savefig(os.path.join(folder, f"iterations_and_time{suffix}.png"))


def profile(max_permutations: int, max_iterations: int = 1000):
  profiler = cProfile.Profile()

  for seed in range(NUM_SEEDS):
    game_state = GameState.new(random_seed=seed)
    if max_permutations == 1:
      closure_to_profile, cleanup = _get_algorithm_closure(game_state,
                                                           max_iterations)
    else:
      closure_to_profile, cleanup = _get_player_closure(game_state,
                                                        max_iterations,
                                                        max_permutations)
    profiler.enable()
    closure_to_profile()
    profiler.disable()
    cleanup()

  # Save and print the profile info.
  folder = os.path.join(os.path.dirname(__file__), "data")
  suffix = _get_file_suffix(max_permutations)
  profiler_path = os.path.join(folder, f"iterations_and_time{suffix}.profile")
  profiler.dump_stats(profiler_path)
  with open(profiler_path + ".txt", "w") as output_file:
    stats = pstats.Stats(profiler, stream=output_file).strip_dirs().sort_stats(
      SortKey.CUMULATIVE)
    stats.print_stats()


def _main():
  max_permutations = 1  # multiprocessing.cpu_count()
  # iterations_and_time(max_permutations)
  profile(max_permutations)


if __name__ == "__main__":
  main_wrapper(_main)
