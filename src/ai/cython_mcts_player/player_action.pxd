#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from ai.cython_mcts_player.card cimport Card
from ai.cython_mcts_player.game_state cimport GameState, PlayerId

cdef enum ActionType:
  NO_ACTION = 0
  PLAY_CARD = 1
  ANNOUNCE_MARRIAGE = 2
  EXCHANGE_TRUMP_CARD = 3
  CLOSE_THE_TALON = 4

cdef struct PlayerAction:
  ActionType action_type
  PlayerId player_id
  Card card

cdef void get_available_actions(GameState *game_state, PlayerAction * actions)
cdef GameState execute(GameState *game_state, PlayerAction action)
cdef PlayerAction from_python_player_action(py_player_action)
cdef to_python_player_action(PlayerAction action)
