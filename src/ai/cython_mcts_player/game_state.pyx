#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from ai.cython_mcts_player.card cimport is_null
from libc.string cimport memset
from model.player_id import PlayerId as PyPlayerId

cdef PlayerId opponent(PlayerId id):
  if id == 0:
    return 1
  return 0

cdef PlayerId from_py_player_id(player_id):
  return 0 if player_id == PyPlayerId.ONE else 1

cdef bint is_to_lead(GameState *this, PlayerId player_id):
  return this.next_player == player_id and is_null(
    this.current_trick[0]) and is_null(this.current_trick[1])

cdef bint is_talon_closed(GameState *this):
  return this.player_that_closed_the_talon != -1

cdef bint must_follow_suit(GameState *this):
  return is_talon_closed(this) or is_null(this.talon[0])

cdef bint is_game_over(GameState *this):
  cdef int target_score = 66
  if this.trick_points[0] >= target_score:
    return True
  if this.trick_points[1] >= target_score:
    return True
  if is_null(this.cards_in_hand[0][0]):
    return True
  return False

cdef Points _get_game_points_won(Points opponent_points):
  if opponent_points >= 33:
    return 1
  if opponent_points > 0:
    return 2
  return 3

cdef (Points, Points) game_points(GameState *this):
  cdef PlayerId winner
  cdef PlayerId closed_the_talon = this.player_that_closed_the_talon
  cdef int points
  if closed_the_talon != -1:
    if this.trick_points[closed_the_talon] >= 66:
      winner = closed_the_talon
      points = _get_game_points_won(this.opponent_points_when_talon_was_closed)
    else:
      winner = opponent(closed_the_talon)
      points = max(2,
                   _get_game_points_won(
                     this.opponent_points_when_talon_was_closed))
  else:
    if this.trick_points[0] >= 66:
      winner = 0
      points = _get_game_points_won(this.trick_points[1])
    elif this.trick_points[1] >= 66:
      winner = 1
      points = _get_game_points_won(this.trick_points[0])
    else:
      winner = this.next_player
      points = 1
  if winner == 0:
    return points, 0
  return 0, points

cdef GameState from_python_game_state(py_game_state):
  cdef GameState game_state
  memset(&game_state, 0, sizeof(game_state))
  for i, card in enumerate(py_game_state.cards_in_hand.one):
    game_state.cards_in_hand[0][i].suit = card.suit
    game_state.cards_in_hand[0][i].card_value = card.card_value
  for i, card in enumerate(py_game_state.cards_in_hand.two):
    game_state.cards_in_hand[1][i].suit = card.suit
    game_state.cards_in_hand[1][i].card_value = card.card_value
  game_state.trump = py_game_state.trump
  if py_game_state.trump_card is not None:
    game_state.trump_card.suit = py_game_state.trump_card.suit
    game_state.trump_card.card_value = py_game_state.trump_card.card_value
  for i, card in enumerate(py_game_state.talon):
    game_state.talon[i].suit = card.suit
    game_state.talon[i].card_value = card.card_value
  game_state.next_player = from_py_player_id(py_game_state.next_player)
  if py_game_state.player_that_closed_the_talon is not None:
    game_state.player_that_closed_the_talon = from_py_player_id(
      py_game_state.player_that_closed_the_talon)
    game_state.opponent_points_when_talon_was_closed = int(
      py_game_state.opponent_points_when_talon_was_closed)
  else:
    game_state.player_that_closed_the_talon = -1
  if py_game_state.trick_points.one == 0:
    for suit in py_game_state.marriage_suits.one:
      game_state.pending_trick_points[
        0] += 40 if suit == py_game_state.trump else 20
  if py_game_state.trick_points.two == 0:
    for suit in py_game_state.marriage_suits.two:
      game_state.pending_trick_points[
        1] += 40 if suit == py_game_state.trump else 20
  game_state.trick_points[0] = py_game_state.trick_points.one
  game_state.trick_points[1] = py_game_state.trick_points.two
  if py_game_state.current_trick.one is not None:
    game_state.current_trick[0].suit = py_game_state.current_trick.one.suit
    game_state.current_trick[
      0].card_value = py_game_state.current_trick.one.card_value
  if py_game_state.current_trick.two is not None:
    game_state.current_trick[1].suit = py_game_state.current_trick.two.suit
    game_state.current_trick[
      1].card_value = py_game_state.current_trick.two.card_value
  return game_state
