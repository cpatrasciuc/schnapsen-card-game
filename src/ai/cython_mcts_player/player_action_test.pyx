#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from ai.cython_mcts_player.card cimport Card, Suit, CardValue
from ai.cython_mcts_player.game_state cimport GameState, from_python_game_state
from ai.cython_mcts_player.player_action cimport ActionType, PlayerAction, \
  get_available_actions
from model.game_state_test_utils import get_game_state_for_tests, \
  get_game_state_with_all_tricks_played


class AvailableActionsTest(unittest.TestCase):
  def test_actions_when_player_is_to_lead(self):
    cdef GameState game_state = from_python_game_state(
      get_game_state_for_tests())
    cdef PlayerAction[7] actions
    cdef PlayerAction[7] expected_actions_player_one = [
      PlayerAction(ActionType.ANNOUNCE_MARRIAGE, 0,
                   Card(Suit.HEARTS, CardValue.QUEEN)),
      PlayerAction(ActionType.ANNOUNCE_MARRIAGE, 0,
                   Card(Suit.HEARTS, CardValue.KING)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.HEARTS, CardValue.TEN)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.SPADES, CardValue.TEN)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.SPADES, CardValue.ACE)),
      PlayerAction(ActionType.CLOSE_THE_TALON, 0,
                   Card(Suit.SPADES, CardValue.ACE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NOSUIT, CardValue.NOVALUE))
    ]
    get_available_actions(&game_state, actions)
    self.assertEqual(expected_actions_player_one, actions)

    cdef PlayerAction[7] expected_actions_player_two = [
      PlayerAction(ActionType.PLAY_CARD, 1,
                   Card(Suit.DIAMONDS, CardValue.QUEEN)),
      PlayerAction(ActionType.ANNOUNCE_MARRIAGE, 1,
                   Card(Suit.CLUBS, CardValue.KING)),
      PlayerAction(ActionType.PLAY_CARD, 1, Card(Suit.CLUBS, CardValue.JACK)),
      PlayerAction(ActionType.PLAY_CARD, 1, Card(Suit.SPADES, CardValue.JACK)),
      PlayerAction(ActionType.ANNOUNCE_MARRIAGE, 1,
                   Card(Suit.CLUBS, CardValue.QUEEN)),
      PlayerAction(ActionType.EXCHANGE_TRUMP_CARD, 1,
                   Card(Suit.CLUBS, CardValue.QUEEN)),
      PlayerAction(ActionType.CLOSE_THE_TALON, 1,
                   Card(Suit.CLUBS, CardValue.QUEEN))
    ]

    game_state.next_player = 1
    get_available_actions(&game_state, actions)
    self.assertEqual(expected_actions_player_two, actions)

  def test_actions_when_player_is_to_lead(self):
    cdef GameState game_state = from_python_game_state(
      get_game_state_with_all_tricks_played())
    cdef PlayerAction[7] actions
    get_available_actions(&game_state, actions)
    self.assertEqual(ActionType.NO_ACTION, actions[0].action_type)
