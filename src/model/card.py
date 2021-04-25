#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import dataclasses

from model.card_value import CardValue
from model.suit import Suit


@dataclasses.dataclass(order=False, frozen=True)
class Card:
  card_value: CardValue
  suit: Suit

  def __post_init__(self):
    if self.card_value is None or self.suit is None:
      raise ValueError("card_value and suit cannot be None")

  def __str__(self):
    return "%s%s" % (self.card_value, self.suit)

  @staticmethod
  def get_all_cards():
    deck = []
    for card_value in CardValue:
      for suit in Suit:
        deck.append(Card(card_value, suit))
    return deck
