#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from model.game_state_test_utils import get_game_state_for_tests, \
  get_game_state_with_empty_talon_for_tests, \
  get_game_state_with_all_tricks_played, \
  get_game_state_for_you_first_no_you_first_puzzle, \
  get_game_state_for_elimination_play_puzzle
from model.game_state_validation import validate


class GameStateTestUtilsTest(unittest.TestCase):
  @staticmethod
  def test_get_simple_game_state_for_tests():
    """Verify that get_simple_game_state_for_tests() returns a valid state."""
    game_state = get_game_state_for_tests()
    validate(game_state)

  @staticmethod
  def test_get_game_state_with_empty_talon_for_tests():
    """
    Verify that get_game_state_with_empty_talon_for_tests() returns a valid
    game state.
    """
    game_state = get_game_state_with_empty_talon_for_tests()
    validate(game_state)

  @staticmethod
  def test_get_game_state_with_all_tricks_played():
    """
    Verify that get_game_state_with_all_tricks_played() returns a valid game
    state.
    """
    game_state = get_game_state_with_all_tricks_played()
    validate(game_state)

  @staticmethod
  def test_get_game_state_for_you_first_no_you_first_puzzle():
    """
    Verify that get_game_state_for_you_first_no_you_first_puzzle() returns a
    valid state.
    """
    game_state = get_game_state_for_you_first_no_you_first_puzzle()
    validate(game_state)

  @staticmethod
  def test_get_game_state_for_elimination_play_puzzle():
    """
    Verify that get_game_state_for_elimination_play_puzzle() returns a valid
    state.
    """
    game_state = get_game_state_for_elimination_play_puzzle()
    validate(game_state)
