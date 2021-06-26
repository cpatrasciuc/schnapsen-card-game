#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from typing import List

from ai.utils import card_win_probabilities
from model.card import Card
from model.suit import Suit


def card_list_from_string(string_list: List[str]) -> List[Card]:
  return [Card.from_string(token) if token is not None else None \
          for token in string_list]


class CardWinProbabilitiesTest(unittest.TestCase):
  def test_default(self):
    test_cases = [
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        [None, None, None, None, None],
        Suit.CLUBS,
        False,
        [0, 0, 0, 0, 0]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        ["js", None, None, None, None],
        Suit.SPADES,
        False,
        [0, 0, 0, 1, 1]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        [None, None, None, None, None],
        Suit.SPADES,
        False,
        # The only case when the hearts are winning is when the only remaining
        # trump, the jack of spades, is not in the opponent's hand.
        [1 / 6, 1 / 6, 1 / 6, 1, 1]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        [None, None, None, None, None],
        Suit.HEARTS,
        False,
        [1, 1, 1, 1, 1]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        [None, None, None, None, None],
        Suit.CLUBS,
        True,
        [0, 0, 0, 5 / 6, 5 / 6]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        ["qd", "kc", "jc", "qc", "jd"],
        Suit.CLUBS,
        True,
        [0, 0, 0, 0, 0]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        ["qd", "kc", "js", "qc", None],
        Suit.CLUBS,
        True,
        [0, 0, 0, 1, 1]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        ["qd", "kc", "jc", "qc", None],
        Suit.CLUBS,
        True,
        [0, 0, 0, 0.5, 0.5]
      ),
    ]
    for num_test_case, test_case in enumerate(test_cases):
      cards_in_hand = card_list_from_string(test_case[0])
      remaining_cards = card_list_from_string(test_case[1])
      opp_cards = card_list_from_string(test_case[2])
      trump = test_case[3]
      must_follow_suit = test_case[4]
      expected_probabilities: List[float] = test_case[5]
      actual_probabilities = card_win_probabilities(cards_in_hand,
                                                    remaining_cards, opp_cards,
                                                    trump, must_follow_suit)
      for i, card in enumerate(cards_in_hand):
        self.assertAlmostEqual(expected_probabilities[i],
                               actual_probabilities[card],
                               msg=f"TestCase {num_test_case}, Card: {card}",
                               places=2)
