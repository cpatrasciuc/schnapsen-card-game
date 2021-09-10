#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from ai.cython_mcts_player.game_state cimport from_python_game_state
from ai.cython_mcts_player.game_state cimport GameState, is_to_lead, \
  is_talon_closed, must_follow_suit, is_game_over, game_points, opponent
from ai.cython_mcts_player.card cimport Card, Suit, CardValue
from model.game_state import GameState as PyGameState
from model.game_state_test_utils import get_game_state_for_tests, \
  get_game_state_with_all_tricks_played
from model.player_id import PlayerId


class PlayerIdTest(unittest.TestCase):
  def test_opponent(self):
    self.assertEqual(1, opponent(0))
    self.assertEqual(0, opponent(1))


class GameStateTest(unittest.TestCase):
  @staticmethod
  def test_sizeof_game_state():
    print(f"Size of a GameState struct: {sizeof(GameState)} bytes")

  def test_get_game_state_for_tests(self):
    cdef GameState game_state = from_python_game_state(
      get_game_state_for_tests())
    self.assertEqual([Card(Suit.HEARTS, CardValue.QUEEN),
                      Card(Suit.HEARTS, CardValue.KING),
                      Card(Suit.HEARTS, CardValue.TEN),
                      Card(Suit.SPADES, CardValue.TEN),
                      Card(Suit.SPADES, CardValue.ACE)],
                     game_state.cards_in_hand[0])
    self.assertEqual([Card(Suit.DIAMONDS, CardValue.QUEEN),
                      Card(Suit.CLUBS, CardValue.KING),
                      Card(Suit.CLUBS, CardValue.JACK),
                      Card(Suit.SPADES, CardValue.JACK),
                      Card(Suit.CLUBS, CardValue.QUEEN)],
                     game_state.cards_in_hand[1])
    self.assertEqual(Suit.CLUBS, game_state.trump)
    self.assertEqual(Card(Suit.CLUBS, CardValue.ACE), game_state.trump_card)
    self.assertEqual([Card(Suit.DIAMONDS, CardValue.JACK),
                      Card(Suit.NOSUIT, CardValue.NOVALUE)],
                     list(game_state.talon)[:2])
    self.assertEqual(0, game_state.next_player)
    self.assertEqual(-1, game_state.player_that_closed_the_talon)
    self.assertEqual([0, 0], game_state.pending_trick_points)
    self.assertEqual([22, 53], game_state.trick_points)
    self.assertEqual([Card(Suit.NOSUIT, CardValue.NOVALUE),
                      Card(Suit.NOSUIT, CardValue.NOVALUE)],
                     game_state.current_trick)

    self.assertTrue(is_to_lead(&game_state, 0))
    self.assertFalse(is_to_lead(&game_state, 1))
    self.assertFalse(is_talon_closed(&game_state))
    self.assertFalse(must_follow_suit(&game_state))
    self.assertFalse(is_game_over(&game_state))

  def test_get_game_state_for_tests_closed_talon(self):
    py_game_state = get_game_state_for_tests()
    py_game_state.close_talon()
    cdef GameState game_state = from_python_game_state(py_game_state)
    self.assertEqual([Card(Suit.HEARTS, CardValue.QUEEN),
                      Card(Suit.HEARTS, CardValue.KING),
                      Card(Suit.HEARTS, CardValue.TEN),
                      Card(Suit.SPADES, CardValue.TEN),
                      Card(Suit.SPADES, CardValue.ACE)],
                     game_state.cards_in_hand[0])
    self.assertEqual([Card(Suit.DIAMONDS, CardValue.QUEEN),
                      Card(Suit.CLUBS, CardValue.KING),
                      Card(Suit.CLUBS, CardValue.JACK),
                      Card(Suit.SPADES, CardValue.JACK),
                      Card(Suit.CLUBS, CardValue.QUEEN)],
                     game_state.cards_in_hand[1])
    self.assertEqual(Suit.CLUBS, game_state.trump)
    self.assertEqual(Card(Suit.CLUBS, CardValue.ACE), game_state.trump_card)
    self.assertEqual([Card(Suit.DIAMONDS, CardValue.JACK),
                      Card(Suit.NOSUIT, CardValue.NOVALUE)],
                     list(game_state.talon)[:2])
    self.assertEqual(0, game_state.next_player)
    self.assertEqual(0, game_state.player_that_closed_the_talon)
    self.assertEqual(53, game_state.opponent_points_when_talon_was_closed)
    self.assertEqual([0, 0], game_state.pending_trick_points)
    self.assertEqual([22, 53], game_state.trick_points)
    self.assertEqual([Card(Suit.NOSUIT, CardValue.NOVALUE),
                      Card(Suit.NOSUIT, CardValue.NOVALUE)],
                     game_state.current_trick)

    self.assertTrue(is_to_lead(&game_state, 0))
    self.assertFalse(is_to_lead(&game_state, 1))
    self.assertTrue(is_talon_closed(&game_state))
    self.assertTrue(must_follow_suit(&game_state))
    self.assertFalse(is_game_over(&game_state))

  def test_get_game_state_with_all_tricks_played(self):
    cdef GameState game_state = from_python_game_state(
      get_game_state_with_all_tricks_played())
    self.assertEqual(Card(Suit.NOSUIT, CardValue.NOVALUE),
                     game_state.cards_in_hand[0][0])
    self.assertEqual(Card(Suit.NOSUIT, CardValue.NOVALUE),
                     game_state.cards_in_hand[1][0])
    self.assertEqual(Suit.CLUBS, game_state.trump)
    self.assertEqual(Card(Suit.NOSUIT, CardValue.NOVALUE),
                     game_state.trump_card)
    self.assertEqual(Card(Suit.NOSUIT, CardValue.NOVALUE), game_state.talon[0])
    self.assertEqual(0, game_state.next_player)
    self.assertEqual(-1, game_state.player_that_closed_the_talon)
    self.assertEqual([0, 0], game_state.pending_trick_points)
    self.assertEqual([60, 60], game_state.trick_points)
    self.assertEqual([Card(Suit.NOSUIT, CardValue.NOVALUE),
                      Card(Suit.NOSUIT, CardValue.NOVALUE)],
                     game_state.current_trick)

    self.assertTrue(is_to_lead(&game_state, 0))
    self.assertFalse(is_to_lead(&game_state, 1))
    self.assertFalse(is_talon_closed(&game_state))
    self.assertTrue(must_follow_suit(&game_state))
    self.assertTrue(is_game_over(&game_state))
    self.assertEqual((1, 0), game_points(&game_state))

  def test_initial_game_state(self):
    cdef GameState game_state = from_python_game_state(
      PyGameState.new(dealer=PlayerId.ONE, random_seed=123))
    self.assertEqual([Card(Suit.SPADES, CardValue.KING),
                      Card(Suit.CLUBS, CardValue.KING),
                      Card(Suit.HEARTS, CardValue.TEN),
                      Card(Suit.HEARTS, CardValue.ACE),
                      Card(Suit.DIAMONDS, CardValue.ACE)],
                     game_state.cards_in_hand[0])
    self.assertEqual([Card(Suit.DIAMONDS, CardValue.KING),
                      Card(Suit.DIAMONDS, CardValue.QUEEN),
                      Card(Suit.SPADES, CardValue.ACE),
                      Card(Suit.SPADES, CardValue.JACK),
                      Card(Suit.DIAMONDS, CardValue.JACK)],
                     game_state.cards_in_hand[1])
    self.assertEqual(Suit.CLUBS, game_state.trump)
    self.assertEqual(Card(Suit.CLUBS, CardValue.JACK), game_state.trump_card)
    self.assertEqual([Card(Suit.SPADES, CardValue.QUEEN),
                      Card(Suit.HEARTS, CardValue.JACK),
                      Card(Suit.CLUBS, CardValue.QUEEN),
                      Card(Suit.CLUBS, CardValue.ACE),
                      Card(Suit.CLUBS, CardValue.TEN),
                      Card(Suit.DIAMONDS, CardValue.TEN),
                      Card(Suit.HEARTS, CardValue.KING),
                      Card(Suit.SPADES, CardValue.TEN),
                      Card(Suit.HEARTS, CardValue.QUEEN), ],
                     game_state.talon)
    self.assertEqual(1, game_state.next_player)
    self.assertEqual(-1, game_state.player_that_closed_the_talon)
    self.assertEqual([0, 0], game_state.pending_trick_points)
    self.assertEqual([0, 0], game_state.trick_points)
    self.assertEqual([Card(Suit.NOSUIT, CardValue.NOVALUE),
                      Card(Suit.NOSUIT, CardValue.NOVALUE)],
                     game_state.current_trick)

    self.assertFalse(is_to_lead(&game_state, 0))
    self.assertTrue(is_to_lead(&game_state, 1))
    self.assertFalse(is_talon_closed(&game_state))
    self.assertFalse(must_follow_suit(&game_state))
    self.assertFalse(is_game_over(&game_state))
