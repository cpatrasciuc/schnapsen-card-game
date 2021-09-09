#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

cdef bint wins(Card this, Card other, Suit trump_suit):
  if this.suit == other.suit:
    return this.card_value > other.card_value
  return this.suit == trump_suit


cdef Card marriage_pair(Card self):
  cdef Card result
  result.suit = self.suit
  result.card_value = CardValue.KING
  if self.card_value == CardValue.KING:
    result.card_value = CardValue.QUEEN
  return result
