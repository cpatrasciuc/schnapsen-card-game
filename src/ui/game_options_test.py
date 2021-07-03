#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from ui.game_options import GameOptions


class GameOptionsTest(unittest.TestCase):
  def test_default_options(self):
    game_options = GameOptions()
    self.assertTrue(game_options.resource_path)
    self.assertTrue(game_options.cards_path)
    self.assertTrue(game_options.enable_animations)
    self.assertEqual(1, game_options.animation_duration_multiplier)
    self.assertEqual(0.5, game_options.play_card_duration)
    self.assertEqual(1.5, game_options.exchange_trump_duration)
    self.assertEqual(0.5, game_options.close_talon_duration)
    self.assertEqual(0.5, game_options.trick_completed_duration)
    self.assertEqual(0.5, game_options.draw_cards_duration)
    self.assertFalse(game_options.computer_cards_visible)

  def test_custom_options(self):
    game_options = GameOptions(animation_duration_multiplier=10,
                               close_talon_duration=2,
                               resource_path="/test/folder/",
                               cards_path="/test/cards/folder/",
                               enable_animations=False,
                               computer_cards_visible=True)
    self.assertEqual("/test/folder/", game_options.resource_path)
    self.assertEqual("/test/cards/folder/", game_options.cards_path)
    self.assertFalse(game_options.enable_animations)
    self.assertEqual(10, game_options.animation_duration_multiplier)
    self.assertEqual(5, game_options.play_card_duration)
    self.assertEqual(15, game_options.exchange_trump_duration)
    self.assertEqual(20, game_options.close_talon_duration)
    self.assertEqual(5, game_options.trick_completed_duration)
    self.assertEqual(5, game_options.draw_cards_duration)
    self.assertTrue(game_options.computer_cards_visible)

  def test_custom_options_with_no_default(self):
    with self.assertRaisesRegex(AssertionError,
                                "No default value for option: no_default"):
      GameOptions(no_default="test")
