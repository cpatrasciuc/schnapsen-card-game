#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import enum


@enum.unique
class CardValue(enum.IntEnum):
  JACK = 2
  QUEEN = 3
  KING = 4
  TEN = 10
  ACE = 11

  def __str__(self):
    card_value_to_str = {
      CardValue.ACE: "A",
      CardValue.TEN: "X",
      CardValue.KING: "K",
      CardValue.QUEEN: "Q",
      CardValue.JACK: "J",
    }
    return card_value_to_str[self]
