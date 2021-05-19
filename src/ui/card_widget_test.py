#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from kivy.base import EventLoop
from kivy.tests.common import UnitTestTouch, GraphicUnitTest

from model.card import Card
from model.card_value import CardValue
from model.suit import Suit
from ui.card_widget import CardWidget


class CardWidgetTest(unittest.TestCase):
  def test_create_widgets_for_all_cards(self):
    card_widgets = CardWidget.create_widgets_for_all_cards()
    self.assertEqual(20, len(card_widgets.keys()))

  def test_aspect_ratio_is_enforced(self):
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=0.5)
    card_widget.size = 10, 20
    card_widget.size = 25, 50
    card_widget.size = 26, 50
    card_widget.size = 24, 50
    with self.assertRaisesRegex(AssertionError, r"\(\[23, 50\], 0.5\)"):
      card_widget.size = 23, 50
    with self.assertRaisesRegex(AssertionError, r"\(\[27, 50\], 0.5\)"):
      card_widget.size = 27, 50

  def test_visibility(self):
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=0.5)
    self.assertTrue(card_widget.visible)
    card_front_filename = card_widget.children[0].source
    card_widget.visible = False
    self.assertFalse(card_widget.visible)
    card_back_filename = card_widget.children[0].source
    self.assertNotEqual(card_front_filename, card_back_filename)
    card_widget.visible = True
    self.assertTrue(card_widget.visible)
    self.assertEqual(card_front_filename, card_widget.children[0].source)

  def test_grayed_out(self):
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=0.5)
    self.assertFalse(card_widget.grayed_out)
    self.assertEqual(1.0, card_widget.opacity)
    card_widget.grayed_out = False
    self.assertFalse(card_widget.grayed_out)
    self.assertEqual(1.0, card_widget.opacity)
    card_widget.grayed_out = True
    self.assertTrue(card_widget.grayed_out)
    self.assertEqual(0.5, card_widget.opacity)
    card_widget.grayed_out = True
    self.assertTrue(card_widget.grayed_out)
    self.assertEqual(0.5, card_widget.opacity)
    card_widget.grayed_out = False
    self.assertFalse(card_widget.grayed_out)
    self.assertEqual(1.0, card_widget.opacity)


class CardWidgetGraphicTest(GraphicUnitTest):
  def test_dragging_a_card_with_the_mouse(self):
    EventLoop.ensure_window()
    window = EventLoop.window

    # Place the card in the center of the window.
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=0.5,
                             do_translation=True)
    min_dimension = min(window.width, window.height)
    card_widget.size = min_dimension / 4, min_dimension / 2
    window_center = window.width / 2, window.height / 2
    card_widget.center = window_center
    self.render(card_widget)

    # Touch down on the card, nothing happens to the card.
    touch = UnitTestTouch(*card_widget.center)
    touch.touch_down()
    self.assertEqual(window_center, card_widget.center)

    # Drag in a random direction, check that the card moved accordingly.
    new_position = window.width / 3, window.height / 3
    touch.touch_move(*new_position)
    self.assertAlmostEqual(new_position[0], card_widget.center_x)
    self.assertAlmostEqual(new_position[1], card_widget.center_y)

    # Drag in another random direction, check that the card moved accordingly.
    new_position = window.width * 0.7, window.height * 0.45
    touch.touch_move(*new_position)
    self.assertAlmostEqual(new_position[0], card_widget.center_x)
    self.assertAlmostEqual(new_position[1], card_widget.center_y)

    # Touch up, nothing happens to the card.
    touch.touch_up()
    self.assertAlmostEqual(new_position[0], card_widget.center_x)
    self.assertAlmostEqual(new_position[1], card_widget.center_y)

    # Move the card back to the window center.
    card_widget.center = window_center

    # Touch down in the bottom left corner of the window, outside of the card.
    # Nothing happens to the card.
    touch = UnitTestTouch(window.width * 0.1, window.height * 0.1)
    self.assertEqual(window_center, card_widget.center)

    # Drag to the window center, on the card. Nothing happens to the card.
    touch.touch_move(*window_center)
    self.assertEqual(window_center, card_widget.center)

    # Drag further to the top right corner of the window. Nothing happens to the
    # card.
    touch.touch_move(window.width * 0.95, window.height * 0.95)
    self.assertEqual(window_center, card_widget.center)

    # Touch up. Nothing happens to the card.
    touch.touch_up()
    self.assertEqual(window_center, card_widget.center)
