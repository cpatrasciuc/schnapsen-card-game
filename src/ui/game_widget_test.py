#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from kivy.base import EventLoop
from kivy.tests.common import GraphicUnitTest

from ui.game_widget import GameWidget


class GameWidgetGraphicTest(GraphicUnitTest):
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
