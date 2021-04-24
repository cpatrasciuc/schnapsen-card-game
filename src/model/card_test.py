#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import dataclasses
import unittest

from model.card import Card
from model.card_value import CardValue
from model.suit import Suit


class CardTest(unittest.TestCase):
  @staticmethod
  def test_create_and_print_all_cards():
    for card_value in CardValue:
      for suit in Suit:
        card = Card(card_value, suit)
        print(repr(card), card)

  # noinspection PyTypeChecker
  def test_card_value_and_suit_cannot_be_none(self):
    with self.assertRaisesRegex(ValueError,
                                "card_value and suit cannot be None"):
      print(Card(CardValue.ACE, None))
    with self.assertRaisesRegex(ValueError,
                                "card_value and suit cannot be None"):
      print(Card(None, Suit.DIAMONDS))
    with self.assertRaisesRegex(ValueError,
                                "card_value and suit cannot be None"):
      print(Card(None, None))

  def test_immutable(self):
    card = Card(CardValue.ACE, Suit.DIAMONDS)
    with self.assertRaisesRegex(dataclasses.FrozenInstanceError,
                                "cannot assign to field"):
      # noinspection PyDataclass
      card.suit = Suit.HEARTS

  def test_serialization(self):
    from pickle import dumps, loads
    for card_value in CardValue:
      for suit in Suit:
        card = Card(card_value, suit)
        self.assertEqual(card, loads(dumps(card)))
