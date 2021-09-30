#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import hashlib
import os
import pickle
import unittest

from libc.string cimport memset

from ai.cython_mcts_player.card cimport Card, Suit, CardValue
from ai.cython_mcts_player.game_state cimport GameState, \
  from_python_game_state, is_to_lead, is_talon_closed, must_follow_suit, \
  is_game_over, game_points
from ai.cython_mcts_player.player_action cimport ActionType, PlayerAction, \
  execute, get_available_actions, from_python_player_action, \
  to_python_player_action

from model.card import Card as PyCard
from model.card_value import CardValue as PyCardValue
from model.game_state import GameState as PyGameState
from model.game_state_test_utils import get_game_state_for_tests, \
  get_game_state_with_all_tricks_played, \
  get_game_state_with_empty_talon_for_tests
from model.player_action import PlayCardAction, AnnounceMarriageAction, \
  ExchangeTrumpCardAction, CloseTheTalonAction
from model.player_id import PlayerId as PyPlayerId
from model.suit import Suit as PySuit


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
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE))
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

  def test_actions_after_the_opponent_played_one_card(self):
    cdef GameState game_state = from_python_game_state(
      get_game_state_for_tests())
    cdef PlayerAction[7] actions
    cdef PlayerAction action = PlayerAction(ActionType.PLAY_CARD, 0,
                                            Card(Suit.SPADES, CardValue.TEN))
    game_state = execute(&game_state, action)
    get_available_actions(&game_state, actions)
    cdef PlayerAction[7] expected_actions = [
      PlayerAction(ActionType.PLAY_CARD, 1,
                   Card(Suit.DIAMONDS, CardValue.QUEEN)),
      PlayerAction(ActionType.PLAY_CARD, 1, Card(Suit.CLUBS, CardValue.KING)),
      PlayerAction(ActionType.PLAY_CARD, 1, Card(Suit.CLUBS, CardValue.JACK)),
      PlayerAction(ActionType.PLAY_CARD, 1, Card(Suit.SPADES, CardValue.JACK)),
      PlayerAction(ActionType.PLAY_CARD, 1, Card(Suit.CLUBS, CardValue.QUEEN)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
    ]
    self.assertEqual(expected_actions, actions)

    game_state = from_python_game_state(get_game_state_for_tests())
    game_state.next_player = 1
    action = PlayerAction(ActionType.PLAY_CARD, 1,
                          Card(Suit.DIAMONDS, CardValue.QUEEN))
    game_state = execute(&game_state, action)
    get_available_actions(&game_state, actions)
    expected_actions = [
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.HEARTS, CardValue.QUEEN)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.HEARTS, CardValue.KING)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.HEARTS, CardValue.TEN)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.SPADES, CardValue.TEN)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.SPADES, CardValue.ACE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
    ]
    self.assertEqual(expected_actions, actions)

  def test_actions_when_player_is_to_lead_talon_is_closed(self):
    cdef GameState game_state = from_python_game_state(
      get_game_state_for_tests())
    cdef PlayerAction[7] actions
    cdef PlayerAction action = PlayerAction(ActionType.CLOSE_THE_TALON, 0,
                                            Card(Suit.NO_SUIT,
                                                 CardValue.NO_VALUE))
    game_state = execute(&game_state, action)
    get_available_actions(&game_state, actions)

    expected_actions = [
      PlayerAction(ActionType.ANNOUNCE_MARRIAGE, 0,
                   Card(Suit.HEARTS, CardValue.QUEEN)),
      PlayerAction(ActionType.ANNOUNCE_MARRIAGE, 0,
                   Card(Suit.HEARTS, CardValue.KING)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.HEARTS, CardValue.TEN)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.SPADES, CardValue.TEN)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.SPADES, CardValue.ACE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
    ]
    self.assertEqual(expected_actions, actions)

    game_state = from_python_game_state(get_game_state_for_tests())
    game_state.next_player = 1
    action.player_id = 1
    game_state = execute(&game_state, action)
    get_available_actions(&game_state, actions)

    expected_actions = [
      PlayerAction(ActionType.PLAY_CARD, 1,
                   Card(Suit.DIAMONDS, CardValue.QUEEN)),
      PlayerAction(ActionType.ANNOUNCE_MARRIAGE, 1,
                   Card(Suit.CLUBS, CardValue.KING)),
      PlayerAction(ActionType.PLAY_CARD, 1, Card(Suit.CLUBS, CardValue.JACK)),
      PlayerAction(ActionType.PLAY_CARD, 1, Card(Suit.SPADES, CardValue.JACK)),
      PlayerAction(ActionType.ANNOUNCE_MARRIAGE, 1,
                   Card(Suit.CLUBS, CardValue.QUEEN)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
    ]
    self.assertEqual(expected_actions, actions)

  def test_actions_after_the_opponent_played_one_card_talon_is_closed(self):
    cdef GameState game_state = from_python_game_state(
      get_game_state_for_tests())
    cdef PlayerAction[7] actions
    cdef PlayerAction close_talon_action = PlayerAction(
      ActionType.CLOSE_THE_TALON, 0, Card(Suit.NO_SUIT, CardValue.NO_VALUE))
    cdef PlayerAction action = PlayerAction(ActionType.PLAY_CARD, 0,
                                            Card(Suit.SPADES, CardValue.TEN))
    game_state = execute(&game_state, close_talon_action)
    game_state = execute(&game_state, action)
    get_available_actions(&game_state, actions)

    expected_actions = [
      PlayerAction(ActionType.PLAY_CARD, 1, Card(Suit.SPADES, CardValue.JACK)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
    ]
    self.assertEqual(expected_actions, actions)

    game_state = from_python_game_state(get_game_state_for_tests())
    game_state.next_player = 1
    close_talon_action.player_id = 1
    action = PlayerAction(ActionType.PLAY_CARD, 1,
                          Card(Suit.SPADES, CardValue.JACK))
    game_state = execute(&game_state, close_talon_action)
    game_state = execute(&game_state, action)
    get_available_actions(&game_state, actions)

    expected_actions = [
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.SPADES, CardValue.TEN)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.SPADES, CardValue.ACE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
    ]
    self.assertEqual(expected_actions, actions)

  def test_actions_when_player_is_to_lead_talon_is_empty(self):
    cdef GameState game_state = from_python_game_state(
      get_game_state_with_empty_talon_for_tests())
    cdef PlayerAction[7] actions

    get_available_actions(&game_state, actions)
    expected_actions = [
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.CLUBS, CardValue.ACE)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.HEARTS, CardValue.KING)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.HEARTS, CardValue.TEN)),
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.SPADES, CardValue.TEN)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
    ]
    self.assertEqual(expected_actions, actions)

    game_state.next_player = 1
    get_available_actions(&game_state, actions)
    expected_actions = [
      PlayerAction(ActionType.PLAY_CARD, 1,
                   Card(Suit.DIAMONDS, CardValue.JACK)),
      PlayerAction(ActionType.ANNOUNCE_MARRIAGE, 1,
                   Card(Suit.CLUBS, CardValue.KING)),
      PlayerAction(ActionType.PLAY_CARD, 1, Card(Suit.CLUBS, CardValue.JACK)),
      PlayerAction(ActionType.ANNOUNCE_MARRIAGE, 1,
                   Card(Suit.CLUBS, CardValue.QUEEN)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
    ]
    self.assertEqual(expected_actions, actions)

  def test_actions_after_the_opponent_played_one_card_talon_is_empty(self):
    cdef GameState game_state = from_python_game_state(
      get_game_state_with_empty_talon_for_tests())
    cdef PlayerAction[7] actions
    cdef PlayerAction action = PlayerAction(
      ActionType.PLAY_CARD, 0, Card(Suit.SPADES, CardValue.TEN))

    game_state = execute(&game_state, action)
    get_available_actions(&game_state, actions)
    expected_actions = [
      PlayerAction(ActionType.PLAY_CARD, 1, Card(Suit.CLUBS, CardValue.KING)),
      PlayerAction(ActionType.PLAY_CARD, 1, Card(Suit.CLUBS, CardValue.JACK)),
      PlayerAction(ActionType.PLAY_CARD, 1, Card(Suit.CLUBS, CardValue.QUEEN)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
    ]
    self.assertEqual(expected_actions, actions)

    game_state = from_python_game_state(
      get_game_state_with_empty_talon_for_tests())
    game_state.next_player = 1
    action = PlayerAction(ActionType.PLAY_CARD, 1,
                          Card(Suit.CLUBS, CardValue.JACK))
    game_state = execute(&game_state, action)
    get_available_actions(&game_state, actions)
    expected_actions = [
      PlayerAction(ActionType.PLAY_CARD, 0, Card(Suit.CLUBS, CardValue.ACE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
      PlayerAction(ActionType.NO_ACTION, 0,
                   Card(Suit.NO_SUIT, CardValue.NO_VALUE)),
    ]
    self.assertEqual(expected_actions, actions)


class ExecutePlayerActionsTest(unittest.TestCase):
  def test_simulate_bummerl(self):
    cdef GameState game_state
    cdef PlayerAction action
    filename = os.path.join(os.path.dirname(__file__),
                            "bummerl_for_tests.pickle")
    # TODO(cleanup): Remove this after debugging the GitHub failure.
    with open(filename, "rb") as binary_file:
      print("MD5 for bummerl_for_tests.pickle:",
            hashlib.md5(binary_file.read()).hexdigest())
    bummerl = None
    with open(filename, "rb") as binary_file:
      bummerl = pickle.load(binary_file)

    for i, game in enumerate(bummerl.completed_games):
      print(f"===== Game #{i + 1} =======")
      py_game_state = PyGameState.new(game.dealer, game.seed)
      memset(&game_state, 0, sizeof(game_state))
      game_state = from_python_game_state(py_game_state)

      for py_action in game.actions:
        action = from_python_player_action(py_action)
        print(py_action, action)
        py_game_state = py_action.execute(py_game_state)
        game_state = execute(&game_state, action)
        print(game_state)
        self.assertEqual(py_game_state.trick_points.one,
                         game_state.trick_points[0])
        self.assertEqual(py_game_state.trick_points.two,
                         game_state.trick_points[1])
        self.assertEqual(py_game_state.next_player == PyPlayerId.ONE,
                         game_state.next_player == 0)
        self.assertEqual(py_game_state.is_to_lead(PyPlayerId.ONE),
                         is_to_lead(&game_state, 0))
        self.assertEqual(py_game_state.is_talon_closed,
                         is_talon_closed(&game_state))
        self.assertEqual(py_game_state.must_follow_suit(),
                         must_follow_suit(&game_state))
        self.assertEqual(py_game_state.is_game_over, is_game_over(&game_state))
        if py_game_state.is_game_over:
          py_game_points = py_game_state.game_points
          self.assertEqual((py_game_points.one, py_game_points.two),
                           game_points(&game_state))


class ToPythonPlayerActionTest(unittest.TestCase):
  def test_play_card_action(self):
    self.assertEqual(
      PlayCardAction(PyPlayerId.ONE, PyCard(PySuit.HEARTS, PyCardValue.KING)),
      to_python_player_action(PlayerAction(ActionType.PLAY_CARD, 0,
                                           Card(Suit.HEARTS, CardValue.KING))))

  def test_announce_marriage_action(self):
    self.assertEqual(
      AnnounceMarriageAction(PyPlayerId.TWO,
                             PyCard(PySuit.HEARTS, PyCardValue.KING)),
      to_python_player_action(PlayerAction(ActionType.ANNOUNCE_MARRIAGE, 1,
                                           Card(Suit.HEARTS, CardValue.KING))))

  def test_exchange_trump_card_action(self):
    self.assertEqual(ExchangeTrumpCardAction(PyPlayerId.ONE),
                     to_python_player_action(
                       PlayerAction(ActionType.EXCHANGE_TRUMP_CARD, 0,
                                    Card(Suit.HEARTS, CardValue.KING))))

  def test_exchange_trump_card_action(self):
    self.assertEqual(ExchangeTrumpCardAction(PyPlayerId.ONE),
                     to_python_player_action(
                       PlayerAction(ActionType.EXCHANGE_TRUMP_CARD, 0,
                                    Card(Suit.HEARTS, CardValue.KING))))

  def test_close_the_talon_action(self):
    self.assertEqual(CloseTheTalonAction(PyPlayerId.TWO),
                     to_python_player_action(
                       PlayerAction(ActionType.CLOSE_THE_TALON, 1,
                                    Card(Suit.HEARTS, CardValue.KING))))

  def test_unrecognized_player_action(self):
    with self.assertRaisesRegexp(ValueError, "Unrecognized player action"):
      to_python_player_action(PlayerAction(<ActionType> 10, 1,
                                           Card(Suit.HEARTS, CardValue.KING)))
