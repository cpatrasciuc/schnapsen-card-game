#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import dataclasses
import random
import unittest
from pickle import dumps, loads

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
    for card_value in CardValue:
      for suit in Suit:
        card = Card(suit, card_value)
        self.assertEqual(card, loads(dumps(card)))

  def test_hash_and_eq(self):
    card_set = {Card(Suit.DIAMONDS, CardValue.ACE),
                Card(Suit.DIAMONDS, CardValue.KING)}
    self.assertEqual(2, len(card_set), card_set)
    card_set = {Card(Suit.DIAMONDS, CardValue.ACE),
                Card(Suit.DIAMONDS, CardValue.ACE)}
    self.assertEqual(1, len(card_set), card_set)

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
    random.seed(1234)
    random.shuffle(shuffled_deck)
    self.assertNotEqual(deck, shuffled_deck)
    sorted_deck = list(sorted(shuffled_deck))
    self.assertEqual(sorted_deck[0], Card(Suit.HEARTS, CardValue.JACK))
    self.assertEqual(sorted_deck[-1], Card(Suit.CLUBS, CardValue.ACE))

  def test_wins(self):
    # Different suits, no trumps. The card played first always wins.
    card1 = Card(Suit.HEARTS, CardValue.KING)
    card2 = Card(Suit.SPADES, CardValue.QUEEN)
    self.assertFalse(card1.wins(card2, trump_suit=Suit.DIAMONDS))
    self.assertFalse(card2.wins(card1, trump_suit=Suit.DIAMONDS))

    # Same suit, no trumps. The greater card wins.
    card1 = Card(Suit.HEARTS, CardValue.KING)
    card2 = Card(Suit.HEARTS, CardValue.QUEEN)
    self.assertTrue(card1.wins(card2, trump_suit=Suit.DIAMONDS))
    self.assertFalse(card2.wins(card1, trump_suit=Suit.DIAMONDS))

    # Same suit, both trump. The greater card wins.
    card1 = Card(Suit.HEARTS, CardValue.KING)
    card2 = Card(Suit.HEARTS, CardValue.QUEEN)
    self.assertTrue(card1.wins(card2, trump_suit=Suit.HEARTS))
    self.assertFalse(card2.wins(card1, trump_suit=Suit.HEARTS))

    # Different suits, one trump. The trump card wins.
    card1 = Card(Suit.HEARTS, CardValue.KING)
    card2 = Card(Suit.SPADES, CardValue.QUEEN)
    self.assertFalse(card1.wins(card2, trump_suit=Suit.SPADES))
    self.assertTrue(card2.wins(card1, trump_suit=Suit.SPADES))
