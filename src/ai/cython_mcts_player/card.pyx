#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

cdef bint is_null(Card this) nogil:
  return this.suit == Suit.NOSUIT or this.card_value == CardValue.NOVALUE

cdef bint is_unknown(Card this) nogil:
  return this.suit == Suit.UNKNOWN_SUIT or \
         this.card_value == CardValue.UNKNOWN_VALUE

cdef bint wins(Card this, Card other, Suit trump_suit) nogil:
  if this.suit == other.suit:
    return this.card_value > other.card_value
  return this.suit == trump_suit

cdef Card marriage_pair(Card self) nogil:
  cdef Card result
  result.suit = self.suit
  result.card_value = CardValue.KING
  if self.card_value == CardValue.KING:
    result.card_value = CardValue.QUEEN
  return result
