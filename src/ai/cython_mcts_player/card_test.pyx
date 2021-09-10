#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from ai.cython_mcts_player.card cimport Card, Suit, CardValue, wins, \
  marriage_pair, is_null


class CardTest(unittest.TestCase):
  def test_wins(self):
    # Different suits, no trumps. The card played first always wins.
    card1 = Card(Suit.HEARTS, CardValue.KING)
    card2 = Card(Suit.SPADES, CardValue.QUEEN)
    self.assertFalse(wins(card1, card2, trump_suit=Suit.DIAMONDS))
    self.assertFalse(wins(card2, card1, trump_suit=Suit.DIAMONDS))

    # Same suit, no trumps. The greater card wins.
    card1 = Card(Suit.HEARTS, CardValue.KING)
    card2 = Card(Suit.HEARTS, CardValue.QUEEN)
    self.assertTrue(wins(card1, card2, trump_suit=Suit.DIAMONDS))
    self.assertFalse(wins(card2, card1, trump_suit=Suit.DIAMONDS))

    # Same suit, both trump. The greater card wins.
    card1 = Card(Suit.HEARTS, CardValue.KING)
    card2 = Card(Suit.HEARTS, CardValue.QUEEN)
    self.assertTrue(wins(card1, card2, trump_suit=Suit.HEARTS))
    self.assertFalse(wins(card2, card1, trump_suit=Suit.HEARTS))

    # Different suits, one trump. The trump card wins.
    card1 = Card(Suit.HEARTS, CardValue.KING)
    card2 = Card(Suit.SPADES, CardValue.QUEEN)
    self.assertFalse(wins(card1, card2, trump_suit=Suit.SPADES))
    self.assertTrue(wins(card2, card1, trump_suit=Suit.SPADES))

  def test_marriage_pair(self):
    for suit in range(4):
      king = Card(<Suit> suit, CardValue.KING)
      queen = Card(<Suit> suit, CardValue.QUEEN)
      self.assertEqual(king, marriage_pair(queen))
      self.assertEqual(queen, marriage_pair(king))

  def test_is_null(self):
    self.assertTrue(is_null(Card(Suit.NOSUIT, CardValue.NOVALUE)))
    self.assertTrue(is_null(Card(Suit.CLUBS, CardValue.NOVALUE)))
    self.assertTrue(is_null(Card(Suit.NOSUIT, CardValue.KING)))
    self.assertFalse(is_null(Card(Suit.CLUBS, CardValue.KING)))
