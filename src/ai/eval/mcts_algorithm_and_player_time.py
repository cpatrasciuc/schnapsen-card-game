#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import multiprocessing
import os
import timeit
from typing import Tuple

from pandas import DataFrame

from ai.mcts_player import MctsPlayer, run_mcts
from ai.mcts_player_options import MctsPlayerOptions
from ai.utils import get_unseen_cards
from main_wrapper import main_wrapper
from model.game_state import GameState


def time_algorithm_and_player(options: MctsPlayerOptions) -> Tuple[
  float, float]:
  game_state = GameState.new(random_seed=0)
  mcts = MctsPlayer(game_state.next_player, cheater=False, options=options)
  game_view = game_state.next_player_view()
  permutation = options.perm_generator(get_unseen_cards(game_view), 5, 1)[0]

  timer = timeit.Timer(
    lambda: run_mcts(list(permutation), game_view, game_state.next_player,
                     options.max_iterations))
  number, time_taken = timer.autorange()
  algorithm_avg_time = time_taken / number
  print(f"Run the Mcts algorithm {number} time(s)\n" +
        f"Total time: {time_taken} seconds\n" +
        f"Average time: {algorithm_avg_time} seconds\n")

  timer = timeit.Timer(lambda: mcts.request_next_action(game_view))
  number, time_taken = timer.autorange()
  player_avg_time = time_taken / number
  print(f"Run the MctsPlayer {number} time(s)\n" +
        f"Total time: {time_taken} seconds\n" +
        f"Average time: {player_avg_time} seconds\n")

  mcts.cleanup()
  return algorithm_avg_time, player_avg_time


def measure_time_for_multiple_setups():
  cpu_count = multiprocessing.cpu_count()
  num_processes_scenarios = [1, cpu_count - 1, cpu_count]
  max_permutations_multiplier_scenarios = [1, 2]
  max_iterations_scenarios = [100, 1000, 10000]

  data = []

  for num_processes in num_processes_scenarios:
    for max_permutations_multiplier in max_permutations_multiplier_scenarios:
      max_permutations = num_processes * max_permutations_multiplier
      for max_iterations in max_iterations_scenarios:
        print(f"Measuring time for: max_permutations={max_permutations}, " +
              f"max_iterations={max_iterations}, num_processes={num_processes}")
        options = MctsPlayerOptions(max_permutations=max_permutations,
                                    max_iterations=max_iterations,
                                    num_processes=num_processes)
        algorithm_time, player_time = time_algorithm_and_player(options)
        data.append((num_processes, max_permutations, max_iterations,
                     algorithm_time, player_time))

  dataframe = DataFrame(data, columns=["num_processes", "max_permutation",
                                       "max_iterations", "algorithm_time",
                                       "player_time"])
  folder = os.path.join(os.path.dirname(__file__), "data")
  csv_path = os.path.join(folder, "mcts_algorithm_and_player_time.csv")
  # noinspection PyTypeChecker
  dataframe.to_csv(csv_path, index=False)


def run_once():
  options = MctsPlayerOptions(max_permutations=8,
                              max_iterations=5000,
                              num_processes=8)
  time_algorithm_and_player(options)


if __name__ == "__main__":
  main_wrapper(run_once)
