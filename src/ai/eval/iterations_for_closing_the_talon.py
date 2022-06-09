#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import functools
import multiprocessing
import os
from typing import Tuple

import numpy as np
from matplotlib import pyplot as plt
from pandas import DataFrame

from ai.cython_mcts_player.mcts_debug import run_mcts_and_collect_data
from ai.eval.utils import same_game_state_after_each_trick_scenarios
from ai.mcts_player_options import MctsPlayerOptions
from main_wrapper import main_wrapper
from model.game_state import GameState


def _min_iteration_to_fully_simulate_closing_the_talon(
    seed: int, options: MctsPlayerOptions, after_n_tricks: int = 0) -> Tuple[
  int, int]:
  if after_n_tricks <= 0:
    game_state = GameState.new(random_seed=seed)
  else:
    games_states = same_game_state_after_each_trick_scenarios(seed)
    game_state = games_states[
      f"GameState (seed={seed}), after {after_n_tricks} trick(s) played"]
  dataframe = run_mcts_and_collect_data(game_state, options,
                                        iterations_step=100)
  close_the_talon = dataframe[dataframe.action.str.startswith(
    "CloseTheTalon") & dataframe.fully_simulated]
  if len(close_the_talon) > 0:
    iteration = close_the_talon.iteration.min()
  else:
    iteration = np.nan
  print(f"Iteration for seed={seed}: {iteration}")
  return seed, iteration


def iterations_for_closing_the_talon():
  """
  This method runs the MctsPlayer on a series of game states to determine the
  average number of iterations required to fully simulate the CloseTheTalon
  action. It does this by first discarding the game states in which the
  algorithm decided it's not worth fully simulating the CloseTheTalon action
  within the given budget. For the remaining game states, it looks at the number
  of iterations after which the action was fully simulated.
  """
  options = MctsPlayerOptions(num_processes=1, max_iterations=10000)
  num_seeds = 1000

  with multiprocessing.Pool(processes=4) as pool:
    data = pool.map(functools.partial(
      _min_iteration_to_fully_simulate_closing_the_talon, options=options,
      after_n_tricks=5),
      list(range(num_seeds)))

  dataframe = DataFrame(data, columns=["seed", "iteration"])
  filename_template = os.path.join(os.path.dirname(__file__), "data",
                                   "iterations_for_closing_the_talon")
  # noinspection PyTypeChecker
  dataframe.to_csv(f"{filename_template}.csv", index=False)
  dataframe.iteration.hist()
  print(dataframe.iteration.describe())
  num_not_fully_simulated = len(dataframe[dataframe.iteration.isnull()])
  not_fully_simulated_pct = 100.0 * num_not_fully_simulated / num_seeds
  plt.title(
    f"In {not_fully_simulated_pct:.0f}% of the cases "
    f"({num_not_fully_simulated} out of {num_seeds}),\n"
    "closing the talon was not fully simulated.")
  plt.suptitle("Iterations required to fully simulate closing the talon")
  plt.xlabel("Iterations")
  plt.tight_layout()
  plt.savefig(f"{filename_template}.png")


if __name__ == "__main__":
  main_wrapper(iterations_for_closing_the_talon)
