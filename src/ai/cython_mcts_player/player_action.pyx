#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from libc.string cimport memset

from ai.cython_mcts_player.card cimport is_null, CardValue
from ai.cython_mcts_player.game_state cimport is_to_lead, must_follow_suit, \
  opponent, is_talon_closed

cdef bint _is_following_suit(PlayerAction action, GameState *game_state):
  cdef PlayerId opp_id = opponent(action.player_id)
  cdef Card other = game_state.current_trick[opp_id]
  cdef Card *hand = game_state.cards_in_hand[action.player_id]
  if action.card.suit == other.suit:
    if action.card.card_value > other.card_value:
      return True
    for i in range(5):
      if is_null(hand[i]):
        break
      if hand[i].suit == other.suit and hand[i].card_value > other.card_value:
        return False
  elif action.card.suit == game_state.trump:
    for i in range(5):
      if is_null(hand[i]):
        break
      if hand[i].suit == other.suit:
        return False
  else:
    for i in range(5):
      if is_null(hand[i]):
        break
      if hand[i].suit == other.suit or hand[i].suit == game_state.trump:
        return False
  return True

# Assumes action.card is in game_state.cards_in_hand[action.player_id] and that
# action.player_id == game_state.next_player.
cdef bint _can_execute_on(PlayerAction action, GameState *game_state):
  cdef Card *hand = game_state.cards_in_hand[action.player_id]
  cdef CardValue marriage_pair = CardValue.QUEEN \
    if action.card.card_value == CardValue.KING else CardValue.KING

  if action.action_type == ActionType.PLAY_CARD:
    if not is_to_lead(game_state, action.player_id):
      if must_follow_suit(game_state):
        if not _is_following_suit(action, game_state):
          return False
    return True

  if action.action_type == ActionType.ANNOUNCE_MARRIAGE:
    if not is_to_lead(game_state, action.player_id):
      return False
    for i in range(5):
      if is_null(hand[i]):
        break
      if action.card.suit == hand[i].suit:
        if hand[i].card_value == marriage_pair:
          return True
    return False

  if action.action_type == ActionType.EXCHANGE_TRUMP_CARD:
    if not is_to_lead(game_state, action.player_id):
      return False
    if is_talon_closed(game_state):
      return False
    if is_null(game_state.trump_card):
      return False
    for i in range(5):
      if is_null(hand[i]):
        break
      if hand[i].suit == game_state.trump and \
          hand[i].card_value == CardValue.JACK:
        return True
    return False

  if action.action_type == ActionType.CLOSE_THE_TALON:
    if not is_to_lead(game_state, action.player_id):
      return False
    if is_talon_closed(game_state):
      return False
    if is_null(game_state.talon[0]):
      return False
    return True

  return False

cdef void get_available_actions(GameState *game_state, PlayerAction * actions):
  cdef int max_num_action = 7
  cdef PlayerId player_id = game_state.next_player
  cdef Card *hand = game_state.cards_in_hand[player_id]
  cdef bint to_lead = is_to_lead(game_state, player_id)
  cdef PlayerAction action
  cdef int action_index = 0
  action.player_id = player_id
  memset(actions, 0, max_num_action * sizeof(PlayerAction))
  for i in range(5):
    if is_null(hand[i]):
      break
    if to_lead:
      if hand[i].card_value == CardValue.QUEEN or \
          hand[i].card_value == CardValue.KING:
        action.action_type = ActionType.ANNOUNCE_MARRIAGE
        action.card = hand[i]
        if _can_execute_on(action, game_state):
          actions[action_index] = action
          action_index += 1
          continue
    action.action_type = ActionType.PLAY_CARD
    action.card = hand[i]
    if _can_execute_on(action, game_state):
      actions[action_index] = action
      action_index += 1
  if to_lead:
    action.action_type = ActionType.EXCHANGE_TRUMP_CARD
    if _can_execute_on(action, game_state):
      actions[action_index] = action
      action_index += 1
    action.action_type = ActionType.CLOSE_THE_TALON
    if _can_execute_on(action, game_state):
      actions[action_index] = action
      action_index += 1
