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

  @staticmethod
  def from_char(char: str) -> "CardValue":
    assert len(char) == 1, char
    char_to_card_value = {card_value.name.lower()[0]: card_value for card_value
                          in CardValue}
    assert len(char_to_card_value) == len(CardValue), char_to_card_value
    return char_to_card_value[char]
