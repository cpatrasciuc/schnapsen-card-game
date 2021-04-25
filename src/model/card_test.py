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
    deck = Card.get_all_cards()
    for card in deck:
      print(repr(card), card)

  # noinspection PyTypeChecker
  def test_card_value_and_suit_cannot_be_none(self):
    with self.assertRaisesRegex(ValueError,
                                "card_value and suit cannot be None"):
      print(Card(None, CardValue.ACE))
    with self.assertRaisesRegex(ValueError,
                                "card_value and suit cannot be None"):
      print(Card(Suit.DIAMONDS, None))
    with self.assertRaisesRegex(ValueError,
                                "card_value and suit cannot be None"):
      print(Card(None, None))

  # noinspection PyTypeChecker
  def test_init_args_order_and_type(self):
    # Swaps the order of the arguments.
    with self.assertRaisesRegex(TypeError, "suit must be an instance of Suit"):
      Card(CardValue.ACE, Suit.DIAMONDS)
    with self.assertRaisesRegex(TypeError,
                                "card_value must be an instance of CardValue"):
      Card(Suit.DIAMONDS, Suit.DIAMONDS)

  def test_immutable(self):
    card = Card(Suit.DIAMONDS, CardValue.ACE)
    with self.assertRaisesRegex(dataclasses.FrozenInstanceError,
                                "cannot assign to field"):
      # noinspection PyDataclass
      card.suit = Suit.HEARTS

  def test_serialization(self):
    from pickle import dumps, loads
    for card_value in CardValue:
      for suit in Suit:
        card = Card(suit, card_value)
        self.assertEqual(card, loads(dumps(card)))

  def test_hash_and_eq(self):
    s = {Card(Suit.DIAMONDS, CardValue.ACE),
         Card(Suit.DIAMONDS, CardValue.KING)}
    self.assertEqual(2, len(s), s)
    s = {Card(Suit.DIAMONDS, CardValue.ACE), Card(Suit.DIAMONDS, CardValue.ACE)}
    self.assertEqual(1, len(s), s)

  def test_display_order(self):
    # Sort by suit first.
    self.assertLess(Card(Suit.HEARTS, CardValue.ACE),
                    Card(Suit.DIAMONDS, CardValue.KING))

    # For same suit, sort by card value.
    self.assertLess(Card(Suit.HEARTS, CardValue.KING),
                    Card(Suit.HEARTS, CardValue.ACE))

    # Sort the whole deck, check the first and last card.
    deck = Card.get_all_cards()
    # Shuffle it in case it is already sorted.
    shuffled_deck = deck[:]
    import random
    random.seed(1234)
    random.shuffle(shuffled_deck)
    self.assertNotEqual(deck, shuffled_deck)
    sorted_deck = list(sorted(shuffled_deck))
    self.assertEqual(sorted_deck[0], Card(Suit.HEARTS, CardValue.JACK))
    self.assertEqual(sorted_deck[-1], Card(Suit.CLUBS, CardValue.ACE))
