#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from typing import List

from kivy.base import EventLoop
from kivy.tests.common import GraphicUnitTest

from ui.game_widget import GameWidget


class GameWidgetGraphicTest(GraphicUnitTest):
  # pylint: disable=invalid-name
  def assertListAlmostEqual(self, first: List, second: List,
                            places: int = 7, msg: str = ""):
    self.assertEqual(len(first), len(second), msg=msg + "\nDifferent lengths.")
    for i, item in enumerate(first):
      self.assertAlmostEqual(item, second[i],
                             msg=msg + f"\nFirst diff at index {i}.",
                             places=places)

  def test_create_empty_widget(self):
    EventLoop.ensure_window()
    game_widget = GameWidget()
    self.render(game_widget)

    # Creates all the cards without a parent widget.
    self.assertEqual(20, len(game_widget.cards.keys()))
    for card_widget in game_widget.cards.values():
      self.assertIsNone(card_widget.parent)

    # Tricks widgets are emtpy.
    trick_widgets = game_widget.tricks_widgets
    self.assertEqual(2, trick_widgets.one.rows)
    self.assertEqual(8, trick_widgets.one.cols)
    self.assertEqual((0, 0), trick_widgets.one.first_free_slot)
    self.assertEqual(2, trick_widgets.two.rows)
    self.assertEqual(8, trick_widgets.two.cols)
    self.assertEqual((0, 0), trick_widgets.two.first_free_slot)

    # No cards in players' hands.
    player_card_widgets = game_widget.player_card_widgets
    self.assertEqual(1, player_card_widgets.one.rows)
    self.assertEqual(5, player_card_widgets.one.cols)
    self.assertEqual((0, 0), player_card_widgets.one.first_free_slot)
    self.assertEqual(1, player_card_widgets.two.rows)
    self.assertEqual(5, player_card_widgets.two.cols)
    self.assertEqual((0, 0), player_card_widgets.two.first_free_slot)

    # No cards in the talon widget.
    self.assertIsNone(game_widget.talon_widget.pop_card())
    self.assertIsNone(game_widget.talon_widget.trump_card)

  # pylint: disable=too-many-statements
  def test_do_layout(self):
    EventLoop.ensure_window()
    game_widget = GameWidget()
    self.render(game_widget)

    # The default window size for tests is 320 x 240.
    self.assertEqual([320, 240], game_widget.size)
    self.assertEqual([112, 60], game_widget.tricks_widgets.one.size)
    self.assertEqual([208, 24], game_widget.tricks_widgets.one.pos)
    self.assertEqual([112, 60], game_widget.tricks_widgets.two.size)
    self.assertEqual([208, 180], game_widget.tricks_widgets.two.pos)
    self.assertEqual([112, 72], game_widget.talon_widget.size)
    self.assertEqual([208, 108], game_widget.talon_widget.pos)
    self.assertEqual([208, 84], game_widget.player_card_widgets.one.size)
    self.assertEqual([0, 0], game_widget.player_card_widgets.one.pos)
    self.assertEqual([208, 84], game_widget.player_card_widgets.two.size)
    self.assertListAlmostEqual([0, 216],
                               list(game_widget.player_card_widgets.two.pos))
    self.assertListAlmostEqual([166, 84], game_widget.play_area.size, places=0)
    self.assertListAlmostEqual([21, 108], game_widget.play_area.pos, places=0)

    # Stretch window horizontally to 640 x 240.
    EventLoop.window.size = 640, 240
    self.advance_frames(1)
    self.assertEqual([640, 240], game_widget.size)
    self.assertEqual([224, 60], game_widget.tricks_widgets.one.size)
    self.assertEqual([416, 24], game_widget.tricks_widgets.one.pos)
    self.assertEqual([224, 60], game_widget.tricks_widgets.two.size)
    self.assertEqual([416, 180], game_widget.tricks_widgets.two.pos)
    self.assertEqual([224, 72], game_widget.talon_widget.size)
    self.assertEqual([416, 108], game_widget.talon_widget.pos)
    self.assertEqual([416, 84], game_widget.player_card_widgets.one.size)
    self.assertEqual([0, 0], game_widget.player_card_widgets.one.pos)
    self.assertEqual([416, 84], game_widget.player_card_widgets.two.size)
    self.assertListAlmostEqual([0, 216],
                               list(game_widget.player_card_widgets.two.pos))
    self.assertListAlmostEqual([333, 84], game_widget.play_area.size, places=0)
    self.assertListAlmostEqual([42, 108], game_widget.play_area.pos, places=0)

    # Stretch window vertically to 320 x 480.
    EventLoop.window.size = 320, 480
    self.advance_frames(1)
    self.assertEqual([320, 480], game_widget.size)
    self.assertEqual([112, 120], game_widget.tricks_widgets.one.size)
    self.assertEqual([208, 48], game_widget.tricks_widgets.one.pos)
    self.assertEqual([112, 120], game_widget.tricks_widgets.two.size)
    self.assertEqual([208, 360], game_widget.tricks_widgets.two.pos)
    self.assertEqual([112, 144], game_widget.talon_widget.size)
    self.assertEqual([208, 216], game_widget.talon_widget.pos)
    self.assertEqual([208, 168], game_widget.player_card_widgets.one.size)
    self.assertEqual([0, 0], game_widget.player_card_widgets.one.pos)
    self.assertEqual([208, 168], game_widget.player_card_widgets.two.size)
    self.assertListAlmostEqual([0, 432],
                               list(game_widget.player_card_widgets.two.pos))
    self.assertListAlmostEqual([166, 168], game_widget.play_area.size, places=0)
    self.assertListAlmostEqual([21, 216], game_widget.play_area.pos, places=0)

    # Stretch window vertically and horizontally to 640 x 480.
    EventLoop.window.size = 640, 480
    self.advance_frames(1)
    self.assertEqual([640, 480], game_widget.size)
    self.assertEqual([224, 120], game_widget.tricks_widgets.one.size)
    self.assertEqual([416, 48], game_widget.tricks_widgets.one.pos)
    self.assertEqual([224, 120], game_widget.tricks_widgets.two.size)
    self.assertEqual([416, 360], game_widget.tricks_widgets.two.pos)
    self.assertEqual([224, 144], game_widget.talon_widget.size)
    self.assertEqual([416, 216], game_widget.talon_widget.pos)
    self.assertEqual([416, 168], game_widget.player_card_widgets.one.size)
    self.assertEqual([0, 0], game_widget.player_card_widgets.one.pos)
    self.assertEqual([416, 168], game_widget.player_card_widgets.two.size)
    self.assertListAlmostEqual([0, 432],
                               list(game_widget.player_card_widgets.two.pos))
    self.assertListAlmostEqual([333, 168], game_widget.play_area.size, places=0)
    self.assertListAlmostEqual([42, 216], game_widget.play_area.pos, places=0)
