#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import enum


@enum.unique
class Suit(enum.IntEnum):
  HEARTS = enum.auto()
  SPADES = enum.auto()
  DIAMONDS = enum.auto()
  CLUBS = enum.auto()

  def __str__(self):
    suit_to_unicode_char = {
      Suit.HEARTS: "\N{Black Heart Suit}",
      Suit.DIAMONDS: "\N{Black Diamond Suit}",
      Suit.SPADES: "\N{Black Spade Suit}",
      Suit.CLUBS: "\N{Black Club Suit}",
    }
    return suit_to_unicode_char[self]
