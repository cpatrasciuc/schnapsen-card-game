#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from model.game_state_test_utils import \
  get_game_state_with_empty_talon_for_tests, get_game_state_for_tests
from model.player_action import CloseTheTalonAction


class CloseTheTalonActionTest(unittest.TestCase):
  """Tests for CloseTheTalonAction class."""

  def test_empty_talon_cannot_be_closed(self):
    game_state = get_game_state_with_empty_talon_for_tests()
    action = CloseTheTalonAction(game_state.next_player)
    self.assertFalse(action.can_execute_on(game_state))

  def test_cannot_close_the_talon_twice(self):
    game_state = get_game_state_for_tests()
    game_state.close_talon()
    action = CloseTheTalonAction(game_state.next_player)
    self.assertFalse(action.can_execute_on(game_state))

  def test_can_only_close_talon_before_a_new_trick_is_played(self):
    game_state = get_game_state_for_tests()
    action = CloseTheTalonAction(game_state.next_player)
    self.assertTrue(action.can_execute_on(game_state))
    action = CloseTheTalonAction(game_state.next_player.opponent())
    self.assertFalse(action.can_execute_on(game_state))

    game_state.current_trick[game_state.next_player] = \
      game_state.cards_in_hand[game_state.next_player][0]
    action = CloseTheTalonAction(game_state.next_player)
    self.assertFalse(action.can_execute_on(game_state))
    action = CloseTheTalonAction(game_state.next_player.opponent())
    self.assertFalse(action.can_execute_on(game_state))
    game_state.next_player = game_state.next_player.opponent()
    action = CloseTheTalonAction(game_state.next_player.opponent())
    self.assertFalse(action.can_execute_on(game_state))

  def test_execute(self):
    game_state = get_game_state_for_tests()
    next_player = game_state.next_player
    action = CloseTheTalonAction(next_player)
    self.assertTrue(action.can_execute_on(game_state))
    action.execute(game_state)
    self.assertEqual(next_player, game_state.next_player)
    self.assertTrue(game_state.is_talon_closed)
    self.assertEqual(next_player, game_state.player_that_closed_the_talon)
    self.assertEqual(53, game_state.opponent_points_when_talon_was_closed)
