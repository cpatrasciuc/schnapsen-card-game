#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

cdef enum Suit:
  HEARTS = 1
  SPADES = 2
  DIAMONDS = 3
  CLUBS = 4

cdef enum CardValue:
  JACK = 2
  QUEEN = 3
  KING = 4
  TEN = 10
  ACE = 11

cdef struct Card:
  Suit suit
  CardValue card_value

cdef bint wins(Card this, Card other, Suit trump_suit)
cdef Card marriage_pair(Card card)
