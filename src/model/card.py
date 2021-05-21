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
  To check if a card wins a trick against a different card, given a trump suit,
  use Card.wins().
  """
  suit: Suit
  card_value: CardValue

  def __post_init__(self):
    if self.card_value is None or self.suit is None:
      raise ValueError("card_value and suit cannot be None")
    if not isinstance(self.suit, Suit):
      raise TypeError(
        "suit must be an instance of Suit, not %s." % type(self.suit))
    if not isinstance(self.card_value, CardValue):
      raise TypeError(
        "card_value must be an instance of CardValue, not %s." % type(
          self.card_value))

  def __str__(self):
    return "%s%s" % (self.card_value, self.suit)

  @staticmethod
  def get_all_cards():
    """Returns all the 20 cards sorted in display order."""
    deck = []
    for suit in Suit:
      for card_value in CardValue:
        deck.append(Card(suit, card_value))
    return deck

  def wins(self, other: "Card", trump_suit: Suit) -> bool:
    """
    Returns True if this card wins a trick in which the other card was played
    first, given the trump suit provided as an argument.
    trump_suit cannot be None.
    other cannot be None and it must be different than this card.
    """
    if self.suit == other.suit:
      return self.card_value > other.card_value
    return self.suit == trump_suit

  @property
  def marriage_pair(self) -> "Card":
    """
    If this card is part of a marriage (i.e., it is a queen or a king), this
    property returns the other card from the marriage. This property should not
    be accessed for cards that cannot be part of a marriage (jacks, tens, aces).
    """
    assert self.card_value in [CardValue.QUEEN, CardValue.KING], self
    if self.card_value == CardValue.KING:
      pair_card_value = CardValue.QUEEN
    else:
      pair_card_value = CardValue.KING
    return Card(suit=self.suit, card_value=pair_card_value)
