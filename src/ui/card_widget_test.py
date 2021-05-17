#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

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

# TODO(ui): Add a graphic test for dragging a card with the mouse.
