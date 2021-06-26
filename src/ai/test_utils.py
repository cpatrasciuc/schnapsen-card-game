#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from typing import List

from model.card import Card


def card_list_from_string(string_list: List[str]) -> List[Card]:
  return [Card.from_string(token) if token is not None else None
          for token in string_list]
