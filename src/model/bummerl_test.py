#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import copy
import unittest
from pickle import dumps, loads

from model.bummerl import Bummerl
from model.game import Game
from model.game_state import GameState
from model.game_state_test_utils import get_actions_for_one_complete_game
from model.player_action import get_available_actions, PlayCardAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair


def _simulate_a_complete_game(game: Game):
  for action in get_actions_for_one_complete_game(game.game_state.next_player):
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
                     GameState.new(dealer=PlayerId.ONE, random_seed=456))

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
    self.assertFalse(bummerl.game.game_state.is_game_over)
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

  def test_seed_is_initialized_randomly_when_not_specified(self):
    """
    Tests that the Bummerl object picks a seed if it is not specified as an
    argument to start(). This seed needs to be saved in case the Game object is
    pickled and unpickled. Otherwise, during unpickling we will start with a
    different game state.
    """
    bummerl = Bummerl(next_dealer=PlayerId.ONE)
    bummerl.start_game()
    game = bummerl.game
    actions = get_available_actions(game.game_state)
    selected_action = \
      [action for action in actions if isinstance(action, PlayCardAction)][0]
    game.play_action(selected_action)
    expected_game_state = copy.deepcopy(game.game_state)

    unpickled_bummerl = loads(dumps(bummerl))

    self.assertIsNot(expected_game_state, unpickled_bummerl.game.game_state)
    self.assertEqual(expected_game_state, unpickled_bummerl.game.game_state)
