#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from kivy.tests.common import GraphicUnitTest

from model.card import Card
from model.card_value import CardValue
from model.suit import Suit
from ui.card_widget import CardWidget
from ui.talon_widget import TalonWidget


def _get_test_card(ratio=0.5):
  card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=ratio)
  card_widget.do_rotation = False
  card_widget.do_translation = False
  card_widget.do_scaling = False
  return card_widget


class TalonWidgetTest(unittest.TestCase):
  def test_set_and_remove_trump_card(self):
    talon_widget = TalonWidget(aspect_ratio=0.5)
    with self.assertRaisesRegex(AssertionError, "No trump card set"):
      talon_widget.remove_trump_card()
    with self.assertRaisesRegex(AssertionError,
                                "Trump card cannot be set to None"):
      # noinspection PyTypeChecker
      talon_widget.set_trump_card(None)
    trump_card = _get_test_card()
    talon_widget.set_trump_card(trump_card)
    with self.assertRaisesRegex(AssertionError, "Trump card is already set"):
      talon_widget.set_trump_card(_get_test_card())
    self.assertIs(trump_card, talon_widget.remove_trump_card())
    with self.assertRaisesRegex(AssertionError, "No trump card set"):
      talon_widget.remove_trump_card()

  def test_add_and_remove_cards(self):
    talon_widget = TalonWidget(aspect_ratio=0.5)
    with self.assertRaisesRegex(AssertionError, "The talon is empty"):
      talon_widget.pop_card()
    with self.assertRaisesRegex(AssertionError, "Card widget cannot be None"):
      # noinspection PyTypeChecker
      talon_widget.push_card(None)
    card_1 = _get_test_card()
    talon_widget.push_card(card_1)
    card_2 = _get_test_card()
    talon_widget.push_card(card_2)
    card_3 = _get_test_card()
    talon_widget.push_card(card_3)
    self.assertIs(card_3, talon_widget.pop_card())
    self.assertIs(card_2, talon_widget.pop_card())
    self.assertIs(card_1, talon_widget.pop_card())
    with self.assertRaisesRegex(AssertionError, "The talon is empty"):
      talon_widget.pop_card()


class TalonWidgetGraphicTest(GraphicUnitTest):
  def test_use_all_height(self):
    # pylint: disable=too-many-statements
    talon_widget = TalonWidget(aspect_ratio=0.5)
    talon_widget.size = 800, 100
    talon_widget.pos = 0, 0

    talon_card = _get_test_card()
    talon_card.pos = 12, 34
    talon_card.size = 56, 112
    trump_card = _get_test_card()
    trump_card.pos = 98, 76
    trump_card.size = 54, 108

    self.assertEqual((12, 34), talon_card.pos)
    self.assertEqual([56, 112], talon_card.size)
    self.assertEqual(0, talon_card.rotation)
    self.assertEqual((98, 76), trump_card.pos)
    self.assertEqual([54, 108], trump_card.size)
    self.assertEqual(0, trump_card.rotation)

    talon_widget.push_card(talon_card)
    self.advance_frames(1)
    self.assertEqual((400, 0), talon_card.pos)
    self.assertEqual([50, 100], talon_card.size)
    self.assertEqual(0, talon_card.rotation)
    self.assertEqual((98, 76), trump_card.pos)
    self.assertEqual([54, 108], trump_card.size)
    self.assertEqual(0, trump_card.rotation)

    talon_widget.set_trump_card(trump_card)
    self.advance_frames(1)
    self.assertEqual((400, 0), talon_card.pos)
    self.assertEqual([50, 100], talon_card.size)
    self.assertEqual(0, talon_card.rotation)
    self.assertEqual((350, 25), trump_card.pos)
    self.assertEqual([50, 100], trump_card.size)
    self.assertEqual(90, trump_card.rotation)

    talon_widget.size = 80, 10
    self.advance_frames(1)
    self.assertEqual((40, 0), talon_card.pos)
    self.assertEqual([5, 10], talon_card.size)
    self.assertEqual(0, talon_card.rotation)
    self.assertEqual((35, 2.5), trump_card.pos)
    self.assertEqual([5, 10], trump_card.size)
    self.assertEqual(90, trump_card.rotation)

    talon_widget.pos = 50, 50
    self.advance_frames(1)
    self.assertEqual((90, 50), talon_card.pos)
    self.assertEqual([5, 10], talon_card.size)
    self.assertEqual(0, talon_card.rotation)
    self.assertEqual((85, 52.5), trump_card.pos)
    self.assertEqual([5, 10], trump_card.size)
    self.assertEqual(90, trump_card.rotation)

    self.assertIs(trump_card, talon_widget.remove_trump_card())
    self.assertIs(talon_card, talon_widget.pop_card())
    talon_widget.pos = 0, 0
    self.advance_frames(1)
    self.assertEqual((90, 50), talon_card.pos)
    self.assertEqual([5, 10], talon_card.size)
    self.assertEqual(0, talon_card.rotation)
    self.assertEqual((85, 52.5), trump_card.pos)
    self.assertEqual([5, 10], trump_card.size)
    self.assertEqual(90, trump_card.rotation)

  def test_use_all_width(self):
    # pylint: disable=too-many-statements
    talon_widget = TalonWidget(aspect_ratio=0.5)
    talon_widget.size = 100, 800
    talon_widget.pos = 0, 0

    talon_card = _get_test_card()
    talon_card.pos = 12, 34
    talon_card.size = 56, 112
    trump_card = _get_test_card()
    trump_card.pos = 98, 76
    trump_card.size = 54, 108

    self.assertEqual((12, 34), talon_card.pos)
    self.assertEqual([56, 112], talon_card.size)
    self.assertEqual(0, talon_card.rotation)
    self.assertEqual((98, 76), trump_card.pos)
    self.assertEqual([54, 108], trump_card.size)
    self.assertEqual(0, trump_card.rotation)

    talon_widget.push_card(talon_card)
    self.advance_frames(1)
    self.assertEqual((50, 350), talon_card.pos)
    self.assertEqual([50, 100], talon_card.size)
    self.assertEqual(0, talon_card.rotation)
    self.assertEqual((98, 76), trump_card.pos)
    self.assertEqual([54, 108], trump_card.size)
    self.assertEqual(0, trump_card.rotation)

    talon_widget.set_trump_card(trump_card)
    self.advance_frames(1)
    self.assertEqual((50, 350), talon_card.pos)
    self.assertEqual([50, 100], talon_card.size)
    self.assertEqual(0, talon_card.rotation)
    self.assertEqual((0, 375), trump_card.pos)
    self.assertEqual([50, 100], trump_card.size)
    self.assertEqual(90, trump_card.rotation)

    talon_widget.size = 10, 80
    self.advance_frames(1)
    self.assertEqual((5, 35), talon_card.pos)
    self.assertEqual([5, 10], talon_card.size)
    self.assertEqual(0, talon_card.rotation)
    self.assertEqual((0, 37.5), trump_card.pos)
    self.assertEqual([5, 10], trump_card.size)
    self.assertEqual(90, trump_card.rotation)

    talon_widget.pos = 50, 50
    self.advance_frames(1)
    self.assertEqual((55, 85), talon_card.pos)
    self.assertEqual([5, 10], talon_card.size)
    self.assertEqual(0, talon_card.rotation)
    self.assertEqual((50, 87.5), trump_card.pos)
    self.assertEqual([5, 10], trump_card.size)
    self.assertEqual(90, trump_card.rotation)

    self.assertIs(trump_card, talon_widget.remove_trump_card())
    self.assertIs(talon_card, talon_widget.pop_card())
    talon_widget.pos = 0, 0
    self.advance_frames(1)
    self.assertEqual((55, 85), talon_card.pos)
    self.assertEqual([5, 10], talon_card.size)
    self.assertEqual(0, talon_card.rotation)
    self.assertEqual((50, 87.5), trump_card.pos)
    self.assertEqual([5, 10], trump_card.size)
    self.assertEqual(90, trump_card.rotation)

  def test_extreme_aspect_ratios(self):
    test_cases = [
      (0.1, (1000, 100), [10, 100], (500, 0), (450, 45)),
      (1.0, (1000, 100), [100, 100], (500, 0), (450, 0)),
      (10.0, (1000, 100), [100, 10], (500, 45), (495, 0)),
      (10.0, (100, 1000), [50, 5], (50, 497.5), (47.5, 475)),
      (1.0, (100, 1000), [50, 50], (50, 475), (25, 475)),
      (0.1, (100, 1000), [10, 100], (50, 450), (0, 495)),
      (0.1, (1000, 1000), [100, 1000], (500, 0), (0, 450)),
      (1.0, (1000, 1000), [500, 500], (500, 250), (250, 250)),
      (10.0, (1000, 1000), [500, 50], (500, 475), (475, 250))
    ]

    for i, test_case in enumerate(test_cases):
      ratio, size, card_size, talon_pos, trump_pos = test_case
      talon_widget = TalonWidget(aspect_ratio=ratio)
      talon_widget.size = size

      talon_card = _get_test_card(ratio)
      talon_card.pos = 12, 34
      talon_card.size = 56, 56 / ratio
      trump_card = _get_test_card(ratio)
      trump_card.pos = 98, 76
      trump_card.size = 54, 54 / ratio

      talon_widget.set_trump_card(trump_card)
      talon_widget.push_card(talon_card)
      self.advance_frames(1)
      self.assertEqual(talon_pos, talon_card.pos, msg=i)
      self.assertEqual(card_size, talon_card.size, msg=i)
      self.assertEqual(0, talon_card.rotation, msg=i)
      self.assertEqual(trump_pos, trump_card.pos, msg=i)
      self.assertEqual(card_size, trump_card.size, msg=i)
      self.assertEqual(90, trump_card.rotation, msg=i)
