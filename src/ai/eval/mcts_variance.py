#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import matplotlib.pyplot as plt
import numpy as np
from pandas import DataFrame
from pandas.plotting import table

from ai.cython_mcts_player.player import CythonMctsPlayer
from ai.mcts_player_options import MctsPlayerOptions
from main_wrapper import main_wrapper
from model.game_state import GameState


def _get_dataframe(game_state: GameState, cheater: bool,
                   options: MctsPlayerOptions, num_samples: int) -> DataFrame:
  data = []
  game_view = game_state if cheater else game_state.next_player_view()
  for _ in range(num_samples):
    player = CythonMctsPlayer(game_state.next_player, cheater, options)
    actions_and_scores = player.get_actions_and_scores(game_view)
    for action, score in actions_and_scores:
      data.append((str(action), score))
  dataframe = DataFrame(data, columns=["action", "score"])
  dataframe = dataframe.pivot(columns=["action"], values=["score"])
  dataframe.columns = dataframe.columns.droplevel()
  return dataframe


def mcts_variance(game_state: GameState, cheater: bool,
                  options: MctsPlayerOptions, num_samples: int):
  dataframe = _get_dataframe(game_state, cheater, options, num_samples)
  print(dataframe.describe())
  dataframe.boxplot()
  details = dataframe.describe()
  details.columns = [""] * len(details.columns)
  table(plt.gca(), np.round(details, 2))
  plt.gca().xaxis.tick_top()
  plt.xticks(rotation=45, ha='left')
  plt.gcf().set_size_inches((5, 10))
  plt.tight_layout()
  plt.savefig("mcts_variance.png")


def mcts_variance_across_multiple_game_states(cheater: bool,
                                              options: MctsPlayerOptions,
                                              num_samples: int,
                                              num_game_states: int):
  data = []
  for seed in range(num_game_states):
    print(f"Evaluating on GameState.new(random_seed={seed})")
    dataframe = _get_dataframe(GameState.new(random_seed=seed),
                               cheater, options, num_samples)
    details = dataframe.describe().T.sort_values(by="mean", ascending=False)
    std_dev = list(details["std"].values)
    while len(std_dev) < 7:
      std_dev.append(np.nan)
    data.append(tuple(std_dev))
  dataframe = DataFrame(
    data, columns=["BestAction"] + [f"Action #{i}" for i in range(2, 8)])
  csv_path = "mcts_variance_across_game_states.csv"
  # noinspection PyTypeChecker
  dataframe.to_csv(csv_path, index=False)
  # dataframe = pandas.read_csv(csv_path)
  dataframe.boxplot()
  plt.xticks(rotation=45, ha='right')
  plt.gcf().set_size_inches((5, 5))
  plt.tight_layout()
  plt.savefig("mcts_variance_across_game_states.png")


def main():
  cheater = False
  options = MctsPlayerOptions(num_processes=1,
                              max_iterations=500,
                              max_permutations=20,
                              select_best_child=True)
  num_samples = 100
  # mcts_variance(GameState.new(random_seed=0), cheater, options, num_samples)
  mcts_variance_across_multiple_game_states(cheater, options, num_samples,
                                            num_game_states=30)


if __name__ == "__main__":
  main_wrapper(main)
