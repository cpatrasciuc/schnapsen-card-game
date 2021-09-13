#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from ai.cython_mcts_player.card cimport Card, Suit

ctypedef int PlayerId

cdef PlayerId opponent(PlayerId id) nogil
cdef PlayerId from_python_player_id(player_id)
cdef to_python_player_id(PlayerId player_id)

ctypedef int Points

ctypedef Card[5] CardsInHand

cdef struct GameState:
  CardsInHand[2] cards_in_hand
  Suit trump
  Card trump_card
  Card[9] talon
  PlayerId next_player
  PlayerId player_that_closed_the_talon
  Points opponent_points_when_talon_was_closed
  Points[2] pending_trick_points
  Points[2] trick_points
  Card[2] current_trick

cdef bint is_to_lead(GameState *this, PlayerId player_id) nogil
cdef bint is_talon_closed(GameState *this) nogil
cdef bint must_follow_suit(GameState *this) nogil
cdef bint is_game_over(GameState *this) nogil
cdef (Points, Points) game_points(GameState *this) nogil

cdef GameState from_python_game_state(py_game_state)
