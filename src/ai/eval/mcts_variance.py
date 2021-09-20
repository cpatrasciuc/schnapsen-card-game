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


def mcts_variance(game_state: GameState, cheater: bool,
                  options: MctsPlayerOptions, num_samples: int):
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


if __name__ == "__main__":
  main_wrapper(lambda: mcts_variance(GameState.new(random_seed=0),
                                     False,
                                     MctsPlayerOptions(num_processes=1,
                                                       max_iterations=5000,
                                                       max_permutations=20,
                                                       select_best_child=True,
                                                       exploration_param=5000),
                                     100))
