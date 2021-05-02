#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import enum


@enum.unique
class PlayerId(enum.Enum):
  """Identifiers for the two players in a game of Schnapsen."""
  ONE = enum.auto()
  TWO = enum.auto()

  def opponent(self) -> "PlayerId":
    """Utility method that can be used to get the opponent of a given player."""
    return PlayerId.TWO if self == PlayerId.ONE else PlayerId.ONE

  def __str__(self):
    return self.name
