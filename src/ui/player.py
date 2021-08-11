#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import abc
from typing import Callable

from model.game_state import GameState
from model.player_action import PlayerAction


class Player(abc.ABC):
  """
  Player interface used by the GameController to interact with the players.
  """

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def request_next_action(self, game_view: GameState,
                          callback: Callable[[PlayerAction], None]) -> None:
    """
    This method is called by the GameController when a new action is needed from
    this player.
    :param game_view: The current game_state, from the player's perspective.
    :param callback: The function to be called by the player when then next
    action is available. The action should be passed as the only argument to
    this callback.
    """

  def is_cheater(self) -> bool:  # pylint: disable=no-self-use
    """
    If it returns True, the GameController will send the whole GameState as a
    parameter to request_next_action(). This means that the opponents' cards and
    the talon are visible.
    """
    return False

  def cleanup(self) -> None:
    """
    This method should be overridden in case any cleanup needs to be done before
    the player instance is deleted.
    """
