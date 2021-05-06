#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from pickle import dumps, loads

from model.bummerl import Bummerl
from model.card import Card
from model.card_value import CardValue
from model.game import Game
from model.game_state import GameState
from model.player_action import PlayCardAction, CloseTheTalonAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit


def _simulate_a_complete_game(game: Game):
  player_a = game.game_state.next_player
  player_b = player_a.opponent()
  actions = [
    # Player A wins the first trick. Score: 0-6.
    PlayCardAction(player_a, Card(Suit.HEARTS, CardValue.JACK)),
    PlayCardAction(player_b, Card(Suit.CLUBS, CardValue.KING)),

    # Player A closes the talon.
    CloseTheTalonAction(player_a),

    # Player A wins the second trick. Score: 0-18.
    PlayCardAction(player_a, Card(Suit.DIAMONDS, CardValue.TEN)),
    PlayCardAction(player_b, Card(Suit.DIAMONDS, CardValue.JACK)),

    # Player A wins the third trick. Score: 0-31.
    PlayCardAction(player_a, Card(Suit.HEARTS, CardValue.TEN)),
    PlayCardAction(player_b, Card(Suit.SPADES, CardValue.QUEEN)),

    # Player B wins the forth trick. Score: 13-31.
    PlayCardAction(player_a, Card(Suit.CLUBS, CardValue.JACK)),
    PlayCardAction(player_b, Card(Suit.CLUBS, CardValue.ACE)),

    # Player A wins the fifth trick. Score: 13-52.
    PlayCardAction(player_b, Card(Suit.SPADES, CardValue.TEN)),
    PlayCardAction(player_a, Card(Suit.SPADES, CardValue.ACE)),

    # Player A wins the sixth trick. Score: 13-67.
    PlayCardAction(player_a, Card(Suit.HEARTS, CardValue.ACE)),
    PlayCardAction(player_b, Card(Suit.SPADES, CardValue.KING))
  ]
  for action in actions:
    game.play_action(action)


class BummerlTest(unittest.TestCase):
  def test_create_with_no_arguments(self):
    bummerl = Bummerl()
    self.assertIsNone(bummerl.game)
    self.assertEqual([], bummerl.completed_games)
    self.assertEqual(PlayerPair(0, 0), bummerl.game_points)
    self.assertFalse(bummerl.is_over)

  def test_create_with_dealer_and_seed(self):
    bummerl = Bummerl(next_dealer=PlayerId.ONE)
    self.assertIsNone(bummerl.game)
    self.assertEqual([], bummerl.completed_games)
    self.assertEqual(PlayerPair(0, 0), bummerl.game_points)
    self.assertFalse(bummerl.is_over)

    game = bummerl.start_game(seed=456)
    self.assertEqual(game, bummerl.game)
    self.assertEqual([], bummerl.completed_games)
    self.assertIsNotNone(game)
    self.assertEqual(game.game_state,
                     GameState.new_game(dealer=PlayerId.ONE, random_seed=456))

  def test_play_a_complete_bummerl(self):
    bummerl = Bummerl(next_dealer=PlayerId.ONE)

    self.assertEqual(PlayerPair(0, 0), bummerl.game_points)
    self.assertEqual([], bummerl.completed_games)

    game_1 = bummerl.start_game(seed=2)
    _simulate_a_complete_game(game_1)
    bummerl.finalize_game()
    self.assertIsNone(bummerl.game)
    self.assertEqual(PlayerPair(0, 3), bummerl.game_points)
    self.assertEqual([game_1], bummerl.completed_games)
    self.assertFalse(bummerl.is_over)

    game_2 = bummerl.start_game(seed=2)
    _simulate_a_complete_game(game_2)
    bummerl.finalize_game()
    self.assertIsNone(bummerl.game)
    self.assertEqual(PlayerPair(3, 3), bummerl.game_points)
    self.assertEqual([game_1, game_2], bummerl.completed_games)
    self.assertFalse(bummerl.is_over)

    game_3 = bummerl.start_game(seed=2)
    _simulate_a_complete_game(game_3)
    bummerl.finalize_game()
    self.assertIsNone(bummerl.game)
    self.assertEqual(PlayerPair(3, 6), bummerl.game_points)
    self.assertEqual([game_1, game_2, game_3], bummerl.completed_games)
    self.assertFalse(bummerl.is_over)

    game_4 = bummerl.start_game(seed=2)
    _simulate_a_complete_game(game_4)
    bummerl.finalize_game()
    self.assertIsNone(bummerl.game)
    self.assertEqual(PlayerPair(6, 6), bummerl.game_points)
    self.assertEqual([game_1, game_2, game_3, game_4], bummerl.completed_games)
    self.assertFalse(bummerl.is_over)

    game_5 = bummerl.start_game(seed=2)
    _simulate_a_complete_game(game_5)
    bummerl.finalize_game()
    self.assertIsNone(bummerl.game)
    self.assertEqual(PlayerPair(6, 9), bummerl.game_points)
    self.assertEqual([game_1, game_2, game_3, game_4, game_5],
                     bummerl.completed_games)
    self.assertTrue(bummerl.is_over)

    with self.assertRaisesRegex(AssertionError,
                                r"Bummerl is over: PlayerPair\(one=6, two=9\)"):
      bummerl.start_game()

  def test_cannot_start_a_game_if_current_game_is_not_finalized(self):
    bummerl = Bummerl()
    bummerl.start_game()
    with self.assertRaisesRegex(AssertionError, "Game in progress"):
      bummerl.start_game()

  def test_cannot_finalize_the_current_game_if_it_is_not_over(self):
    bummerl = Bummerl()
    bummerl.start_game()
    self.assertFalse(bummerl.game.game_state.is_game_over())
    with self.assertRaisesRegex(AssertionError, "Current game is not over"):
      bummerl.finalize_game()

  def test_pickling(self):
    bummerl = Bummerl(next_dealer=PlayerId.ONE)
    _simulate_a_complete_game(bummerl.start_game(seed=2))
    bummerl.finalize_game()
    _simulate_a_complete_game(bummerl.start_game(seed=2))

    unpickled_bummerl = loads(dumps(bummerl))

    self.assertIsNot(bummerl, unpickled_bummerl)
    self.assertIsNotNone(unpickled_bummerl.game)
    self.assertEqual(PlayerPair(0, 3), unpickled_bummerl.game_points)
    self.assertEqual(1, len(unpickled_bummerl.completed_games))
    self.assertFalse(unpickled_bummerl.is_over)

    unpickled_bummerl.finalize_game()
    self.assertIsNone(unpickled_bummerl.game)
    self.assertEqual(PlayerPair(3, 3), unpickled_bummerl.game_points)
    self.assertEqual(2, len(unpickled_bummerl.completed_games))
    self.assertFalse(unpickled_bummerl.is_over)
