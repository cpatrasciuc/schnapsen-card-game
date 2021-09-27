#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import math
from typing import Dict, Callable

from ai.cython_mcts_player.player import CythonMctsPlayer

from ai.heuristic_player import HeuristicPlayer, HeuristicPlayerOptions
from ai.lib_mcts_player import LibMctsPlayer
from ai.mcts_player_options import MctsPlayerOptions
from ai.player import Player
from ai.random_player import RandomPlayer
from model.player_id import PlayerId

CreatePlayerFn = Callable[[PlayerId], Player]

# A dictionary containing all the evaluated player names and the functions that
# instantiates them.
PLAYER_NAMES: Dict[str, CreatePlayerFn] = {
  "Random": RandomPlayer,
  "RandomTalon": lambda player_id: RandomPlayer(player_id,
                                                never_close_talon=True),
  "RandomTrump": lambda player_id: RandomPlayer(player_id,
                                                force_trump_exchange=True),
  "RandomMarriage":
    lambda player_id: RandomPlayer(player_id, force_marriage_announcement=True),
  "RandomTalonTrump": lambda player_id: RandomPlayer(player_id,
                                                     force_trump_exchange=True,
                                                     never_close_talon=True),
  "RandomTalonMarriage":
    lambda player_id: RandomPlayer(player_id, never_close_talon=True,
                                   force_marriage_announcement=True),
  "RandomTrumpMarriage":
    lambda player_id: RandomPlayer(player_id, force_trump_exchange=True,
                                   force_marriage_announcement=True),
  "RandomTalonTrumpMarriage":
    lambda player_id: RandomPlayer(player_id, force_trump_exchange=True,
                                   never_close_talon=True,
                                   force_marriage_announcement=True),
  "Heuristic": HeuristicPlayer,
  "HeuristicNoPriorityDiscard":
    lambda player_id: HeuristicPlayer(player_id, HeuristicPlayerOptions(
      priority_discard=False)),
  "HeuristicNoCloseTalon":
    lambda player_id: HeuristicPlayer(player_id, HeuristicPlayerOptions(
      can_close_talon=False)),
  "HeuristicNoSaveMarriages":
    lambda player_id: HeuristicPlayer(player_id, HeuristicPlayerOptions(
      save_marriages=False)),
  "HeuristicNoTrumpForMarriages":
    lambda player_id: HeuristicPlayer(player_id, HeuristicPlayerOptions(
      trump_for_marriage=False)),
  "HeuristicNoAvoidDirectLoss":
    lambda player_id: HeuristicPlayer(player_id, HeuristicPlayerOptions(
      avoid_direct_loss=False)),
  "HeuristicWithTrumpControl":
    lambda player_id: HeuristicPlayer(player_id, HeuristicPlayerOptions(
      trump_control=True)),

  "LibMctsPlayer": LibMctsPlayer,

  # Same permutations, different iterations
  "MctsPlayer30perm10000iter":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=30,
                                         max_iterations=10000,
                                         select_best_child=True,
                                         exploration_param=math.sqrt(2)
                                       )),
  "MctsPlayer30perm5000iter":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=30,
                                         max_iterations=5000,
                                         select_best_child=True,
                                         exploration_param=math.sqrt(2))),
  "MctsPlayer30perm2500iter":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=30,
                                         max_iterations=2500,
                                         select_best_child=True,
                                         exploration_param=math.sqrt(2))),
  "MctsPlayer30perm1000iter":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=30,
                                         max_iterations=1000,
                                         select_best_child=True,
                                         exploration_param=math.sqrt(2))),

  # Same iterations, different permutations
  "MctsPlayer1perm2500iter":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=1,
                                         max_iterations=2500,
                                         select_best_child=True,
                                         exploration_param=math.sqrt(2))),
  "MctsPlayer5perm2500iter":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=5,
                                         max_iterations=2500,
                                         select_best_child=True,
                                         exploration_param=math.sqrt(2))),
  "MctsPlayer10perm2500iter":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=10,
                                         max_iterations=2500,
                                         select_best_child=True,
                                         exploration_param=math.sqrt(2))),
  "MctsPlayer40perm2500iter":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=40,
                                         max_iterations=2500,
                                         select_best_child=True,
                                         exploration_param=math.sqrt(2))),
  "MctsPlayer80perm2500iter":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=80,
                                         max_iterations=2500,
                                         select_best_child=True,
                                         exploration_param=math.sqrt(2))),
  "MctsPlayer150perm2500iter":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=150,
                                         max_iterations=2500,
                                         select_best_child=True,
                                         exploration_param=math.sqrt(2))),

  # Tune exploration_param
  "MctsPlayer20perm5000iterRandomSelection":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=20,
                                         max_iterations=5000,
                                         select_best_child=False)),
  "MctsPlayer20perm5000iter0exp":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=20,
                                         max_iterations=5000,
                                         select_best_child=True,
                                         exploration_param=0)),
  "MctsPlayer20perm5000iter1/Sqrt(2)exp":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=20,
                                         max_iterations=5000,
                                         select_best_child=True,
                                         exploration_param=1.0 / math.sqrt(2))),
  "MctsPlayer20perm5000iter1exp":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=20,
                                         max_iterations=5000,
                                         select_best_child=True,
                                         exploration_param=1)),
  "MctsPlayer20perm5000iterSqrt(2)exp":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=20,
                                         max_iterations=5000,
                                         select_best_child=True,
                                         exploration_param=math.sqrt(2))),
  "MctsPlayer20perm5000iter20exp":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=20,
                                         max_iterations=5000,
                                         select_best_child=True,
                                         exploration_param=20)),
  "MctsPlayer20perm5000iter5000exp":
    lambda player_id: CythonMctsPlayer(player_id, False,
                                       MctsPlayerOptions(
                                         num_processes=1,
                                         max_permutations=20,
                                         max_iterations=5000,
                                         select_best_child=True,
                                         exploration_param=5000)),
}
