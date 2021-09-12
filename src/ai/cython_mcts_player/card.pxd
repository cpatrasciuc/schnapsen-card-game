#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

cdef enum Suit:
  # TODO(refactor): Rename this to NO_SUIT.
  NOSUIT = 0
  HEARTS = 1
  SPADES = 2
  DIAMONDS = 3
  CLUBS = 4
  UNKNOWN_SUIT = 5

cdef enum CardValue:
  NOVALUE = 0
  UNKNOWN_VALUE = 1
  JACK = 2
  QUEEN = 3
  KING = 4
  TEN = 10
  ACE = 11

cdef struct Card:
  Suit suit
  CardValue card_value

# In the Cython GameState we use arrays of length 5 and 9 to represent the
# cards in hand and the talon. During the game, the player might have less than
# 5 cards in their hand and the talon can have less than 9 cards (or even be
# empty). We use null cards (NO_SUIT and/or NO_VALUE) to represent the fact that
# there is no card in such a slot (similar to NULL terminated strings). We use
# unknown cards (UNKNOWN_SUIT and/or UNKNOWN_VALUE) in game views, to represent
# the fact that there is a card in such a slot, but the current player cannot
# see it.
cdef bint is_null(Card this)
cdef bint is_unknown(Card this)

cdef bint wins(Card this, Card other, Suit trump_suit)
cdef Card marriage_pair(Card card)
