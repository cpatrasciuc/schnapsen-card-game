#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from typing import Dict, Callable

from ai.heuristic_player import HeuristicPlayer, HeuristicPlayerOptions
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
}
