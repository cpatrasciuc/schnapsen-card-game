#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import dataclasses
from typing import TypeVar, Generic

from model.player_id import PlayerId

T = TypeVar('T')


@dataclasses.dataclass
class PlayerPair(Generic[T]):
  """
  Generic class that stores a pair of variables, one for each of the two players
  in a game of Schnapsen. It can be keyed by PlayerId.

  Examples:
    * score: one integer for each player
    * the cards in hand: a list of cards for each player
    * a trick: one card for each player
  """
  one: T = None
  two: T = None

  def __getitem__(self, key):
    self._check_key_type(key)
    return self.one if key == PlayerId.ONE else self.two

  def __setitem__(self, key, value):
    self._check_key_type(key)
    if key == PlayerId.ONE:
      self.one = value
    else:
      self.two = value

  @staticmethod
  def _check_key_type(key):
    if type(key) != PlayerId:
      raise TypeError("Keys must be of type PlayerId, not %s." % type(key))
