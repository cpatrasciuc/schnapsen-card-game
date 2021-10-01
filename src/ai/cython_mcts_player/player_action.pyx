#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from libc.string cimport memset

from ai.cython_mcts_player.card cimport CardValue, is_null, Suit, wins
from ai.cython_mcts_player.game_state cimport is_to_lead, must_follow_suit, \
  opponent, is_talon_closed, Points, from_python_player_id, to_python_player_id
from model.card import Card as PyCard
from model.card_value import CardValue as PyCardValue
from model.player_action import PlayCardAction, AnnounceMarriageAction, \
  ExchangeTrumpCardAction, CloseTheTalonAction
from model.suit import Suit as PySuit

cdef bint _is_following_suit(PlayerAction action, GameState *game_state) nogil:
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
cdef bint _can_execute_on(PlayerAction action, GameState *game_state) nogil:
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

cdef void get_available_actions(GameState *game_state,
                                PlayerAction *actions) nogil:
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

cdef int _remove_card_from_hand(Card *cards_in_hand, Card card) nogil:
  cdef int i, j, empty_slot
  for i in range(5):
    if is_null(cards_in_hand[i]):
      break
    if cards_in_hand[i].suit == card.suit \
        and cards_in_hand[i].card_value == card.card_value:
      if i < 4:
        # TODO(debug): Revert this after debugging GitHub failure.
        # memcpy(&cards_in_hand[i], &cards_in_hand[i + 1],
        #        (5 - i - 1) * sizeof(Card))
        for j in range(5 - i - 1):
          cards_in_hand[i + j] = cards_in_hand[i + j + 1]
      cards_in_hand[4].suit = Suit.NO_SUIT
      cards_in_hand[4].card_value = CardValue.NO_VALUE
      empty_slot = i
      while i < 5 and not is_null(cards_in_hand[empty_slot]):
        empty_slot += 1
      return empty_slot
  raise ValueError(
    f"The card {card.suit, card.card_value} was not found in player's hand")

cdef GameState _execute_play_card_action(GameState *game_state,
                                         PlayerAction action) nogil:
  cdef GameState new_game_state = game_state[0]
  cdef PlayerId player_id = action.player_id
  cdef PlayerId opp_id = opponent(player_id)

  new_game_state.current_trick[player_id] = action.card
  if is_null(new_game_state.current_trick[opp_id]):
    # The player lead the trick. Wait for the other player to play a card.
    new_game_state.next_player = opp_id
    return new_game_state

  # The player completes a trick. Check who won it.
  cdef int winner
  if wins(action.card, game_state.current_trick[opp_id], game_state.trump):
    winner = player_id
  else:
    winner = opp_id

  # If it's the first trick won by this player, check if there are any
  # pending marriage points to be added.
  if new_game_state.trick_points[winner] == 0:
    new_game_state.trick_points[winner] = \
      game_state.pending_trick_points[winner]
    new_game_state.pending_trick_points[winner] = 0

  # Update trick_points.
  new_game_state.trick_points[winner] += \
    new_game_state.current_trick[0].card_value
  new_game_state.trick_points[winner] += \
    new_game_state.current_trick[1].card_value

  # Remove the cards from players' hands.
  cdef int player_one_index = _remove_card_from_hand(
    new_game_state.cards_in_hand[0],
    new_game_state.current_trick[0])
  cdef int player_two_index = _remove_card_from_hand(
    new_game_state.cards_in_hand[1],
    new_game_state.current_trick[1])

  # Clear current trick.
  memset(&new_game_state.current_trick[0], 0, 2 * sizeof(Card))

  # Maybe draw new cards from the talon.
  cdef Card first_card = new_game_state.talon[0]
  cdef Card second_card = new_game_state.talon[1]
  cdef int i
  if not is_null(first_card) and \
      not is_talon_closed(&new_game_state):
    # TODO(debug): Revert this after debugging GitHub failure.
    # memcpy(new_game_state.talon, &new_game_state.talon[2], 7 * sizeof(Card))
    for i in range(7):
      new_game_state.talon[i] = new_game_state.talon[i + 2]
    new_game_state.talon[7].suit = Suit.NO_SUIT
    new_game_state.talon[8].suit = Suit.NO_SUIT
    if is_null(second_card):
      second_card = new_game_state.trump_card
      new_game_state.trump_card.suit = Suit.NO_SUIT

    # TODO(optimization): If we want to reuse the the nodes in the Mcts tree we
    #  have to sort the card here, so the order won't matter.
    if winner == 0:
      new_game_state.cards_in_hand[0][player_one_index] = first_card
      new_game_state.cards_in_hand[1][player_two_index] = second_card
    else:
      new_game_state.cards_in_hand[0][player_one_index] = second_card
      new_game_state.cards_in_hand[1][player_two_index] = first_card

  # Update the next player
  new_game_state.next_player = winner

  return new_game_state

cdef GameState _execute_marriage_action(GameState *game_state,
                                        PlayerAction action) nogil:
  cdef GameState new_game_state = game_state[0]
  cdef PlayerId player_id = action.player_id
  cdef Points marriage_points = \
    40 if action.card.suit == new_game_state.trump else 20
  new_game_state.current_trick[player_id] = action.card
  if new_game_state.trick_points[player_id] > 0:
    new_game_state.trick_points[player_id] += marriage_points
  else:
    new_game_state.pending_trick_points[player_id] += marriage_points
  new_game_state.next_player = opponent(player_id)
  return new_game_state

cdef GameState _execute_exchange_trump_card_action(GameState *game_state,
                                                   PlayerAction action) nogil:
  cdef GameState new_game_state = game_state[0]
  cdef PlayerId player_id = action.player_id
  cdef Card trump_jack
  trump_jack.suit = new_game_state.trump
  trump_jack.card_value = CardValue.JACK
  cdef int trump_jack_index = _remove_card_from_hand(
    new_game_state.cards_in_hand[player_id], trump_jack)
  new_game_state.cards_in_hand[player_id][trump_jack_index] = \
    new_game_state.trump_card
  new_game_state.trump_card = trump_jack
  return new_game_state

cdef GameState _execute_close_the_talon_action(GameState *game_state,
                                               PlayerAction action) nogil:
  cdef GameState new_game_state = game_state[0]
  new_game_state.player_that_closed_the_talon = action.player_id
  new_game_state.opponent_points_when_talon_was_closed = \
    new_game_state.trick_points[opponent(action.player_id)]
  return new_game_state

cdef GameState execute(GameState *game_state, PlayerAction action) nogil:
  if action.action_type == ActionType.PLAY_CARD:
    return _execute_play_card_action(game_state, action)
  if action.action_type == ActionType.ANNOUNCE_MARRIAGE:
    return _execute_marriage_action(game_state, action)
  if action.action_type == ActionType.EXCHANGE_TRUMP_CARD:
    return _execute_exchange_trump_card_action(game_state, action)
  if action.action_type == ActionType.CLOSE_THE_TALON:
    return _execute_close_the_talon_action(game_state, action)
  raise ValueError(f"Unrecognized action_type: {action.action_type}")

cdef PlayerAction from_python_player_action(py_player_action):
  cdef PlayerAction action
  memset(&action, 0, sizeof(action))
  action.player_id = from_python_player_id(py_player_action.player_id)
  if isinstance(py_player_action, PlayCardAction):
    action.action_type = ActionType.PLAY_CARD
    action.card.suit = py_player_action.card.suit
    action.card.card_value = py_player_action.card.card_value
  elif isinstance(py_player_action, AnnounceMarriageAction):
    action.action_type = ActionType.ANNOUNCE_MARRIAGE
    action.card.suit = py_player_action.card.suit
    action.card.card_value = py_player_action.card.card_value
  elif isinstance(py_player_action, ExchangeTrumpCardAction):
    action.action_type = ActionType.EXCHANGE_TRUMP_CARD
  elif isinstance(py_player_action, CloseTheTalonAction):
    action.action_type = ActionType.CLOSE_THE_TALON
  else:
    raise ValueError(f"Unrecognized player action: {repr(py_player_action)}")
  return action

cdef to_python_player_action(PlayerAction action):
  py_player_id = to_python_player_id(action.player_id)
  if action.action_type == ActionType.PLAY_CARD:
    return PlayCardAction(py_player_id,
                          PyCard(PySuit(action.card.suit),
                                 PyCardValue(action.card.card_value)))
  if action.action_type == ActionType.ANNOUNCE_MARRIAGE:
    return AnnounceMarriageAction(py_player_id,
                                  PyCard(PySuit(action.card.suit),
                                         PyCardValue(action.card.card_value)))
  if action.action_type == ActionType.EXCHANGE_TRUMP_CARD:
    return ExchangeTrumpCardAction(py_player_id)
  if action.action_type == ActionType.CLOSE_THE_TALON:
    return CloseTheTalonAction(py_player_id)
  raise ValueError(f"Unrecognized player action: {action}")
