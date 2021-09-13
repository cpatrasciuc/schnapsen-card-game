#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import os
import timeit

from pandas import DataFrame

from ai.mcts_algorithm import Mcts
from ai.mcts_player import MctsPlayer
from ai.mcts_player_options import MctsPlayerOptions
from main_wrapper import main_wrapper
from model.game_state import GameState


def time_algorithm(max_iterations: int) -> float:
  # Run the Mcts algorithm, no player
  game_state = GameState.new(random_seed=0)
  mcts = Mcts(game_state.next_player)
  timer = timeit.Timer(lambda: mcts.build_tree(game_state, max_iterations))
  number, time_taken = timer.autorange()
  avg_time = time_taken / number
  print(f"Run the Mcts algorithm {number} time(s)\n" +
        f"Total time: {time_taken} seconds\n" +
        f"Average time: {avg_time} seconds\n")
  return avg_time


def time_player(player_class, cheater: bool,
                options: MctsPlayerOptions) -> float:
  game_state = GameState.new(random_seed=0)
  if not cheater:
    game_state = game_state.next_player_view()
  mcts = player_class(game_state.next_player, cheater=cheater, options=options)
  timer = timeit.Timer(lambda: mcts.request_next_action(game_state))
  number, time_taken = timer.autorange()
  avg_time = time_taken / number
  print(f"Run player {number} time(s)\n" +
        f"Total time: {time_taken} seconds\n" +
        f"Average time: {avg_time} seconds\n")
  mcts.cleanup()
  return avg_time


def run_timing_progression(player_class, max_iterations: int):
  data = [("Mcts algorithm", time_algorithm(max_iterations))]

  scenarios = {
    "Cheater player w/o parallelism": (True, 1, 1),
    "Cheater player w/ parallelism": (True, 1, 8),
    "1 permutation, w/o parallelism": (False, 1, 1),
    "1 permutation, w/ parallelism": (False, 1, 8),
    "8 permutations, w/o parallelism": (False, 8, 1),
    "8 permutations, w/ parallelism": (False, 8, 8),
    "16 permutations, w/o parallelism": (False, 16, 1),
    "16 permutations, w/ parallelism": (False, 16, 8),
  }

  for scenario, params in scenarios.items():
    cheater, max_permutations, num_processes = params
    options = MctsPlayerOptions(max_iterations=max_iterations,
                                max_permutations=max_permutations,
                                num_processes=num_processes)
    print(f"Runing scenario: {scenario}")
    avg_time = time_player(player_class, cheater, options)
    data.append((scenario, avg_time))

  dataframe = DataFrame(data, columns=[
    "scenario", f"{player_class.__name__} ({max_iterations} iterations)"])
  folder = os.path.join(os.path.dirname(__file__), "data")
  csv_path = os.path.join(folder, "mcts_algorithm_and_player_time.csv")
  # noinspection PyTypeChecker
  dataframe.to_csv(csv_path, index=False)


if __name__ == "__main__":
  main_wrapper(lambda: run_timing_progression(MctsPlayer, 4000))
