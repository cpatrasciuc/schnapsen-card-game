#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import dataclasses

from model.card_value import CardValue
from model.suit import Suit


@dataclasses.dataclass(order=True, frozen=True)
class Card:
  """
  Class representing a playing card. Card instances are immutable.

  The sorting order is for display purposes only. It groups first by suit and
  then by card value. Comparison operators should not be used to check whether
  one card wins a trick or not.
  TODO: add a method that checks if a card wins a trick.
  """
  suit: Suit
  card_value: CardValue

  def __post_init__(self):
    if self.card_value is None or self.suit is None:
      raise ValueError("card_value and suit cannot be None")
    if not isinstance(self.suit, Suit):
      raise TypeError(
        "Suit must be an instance of Suit, not %s." % type(self.suit))
    if not isinstance(self.card_value, CardValue):
      raise TypeError(
        "card_value must be an instance of CardValue, not %s." % type(
          self.card_value))

  def __str__(self):
    return "%s%s" % (self.card_value, self.suit)

  @staticmethod
  def get_all_cards():
    deck = []
    for suit in Suit:
      for card_value in CardValue:
        deck.append(Card(suit, card_value))
    return deck
