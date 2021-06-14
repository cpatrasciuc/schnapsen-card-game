#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import abc
from typing import Callable, Optional

from ai.player import Player as AIPlayer
from ai.random_player import RandomPlayer
from model.game_state import GameState
from model.player_action import PlayerAction
from model.player_id import PlayerId


class Player(abc.ABC):
  """
  Player interface used by the GameController to interact with the players.
  """

  # pylint: disable=too-few-public-methods

  __metaclass__ = abc.ABCMeta

  # TODO(player): Add a GameView class and a GameView argument to this function.
  @abc.abstractmethod
  def request_next_action(self, game_state: GameState,
                          callback: Callable[[PlayerAction], None]) -> None:
    """
    This method is called by the GameController when a new action is needed from
    this player.
    :param game_state: The current game_state.
    :param callback: The function to be called by the player when then next
    action is available. The action should be passed as the only argument to
    this callback.
    """


class ComputerPlayer(Player):
  """
  The Player implementation that runs an AI algorithm to pick the next action to
  be played. It's a wrapper over an ai.player.Player instance.
  """

  # pylint: disable=too-few-public-methods

  def __init__(self, player: Optional[AIPlayer] = None):
    self._player = player or RandomPlayer(PlayerId.TWO)

  def request_next_action(self, game_state: GameState,
                          callback: Callable[[PlayerAction], None]) -> None:
    # TODO(ui): Run the AI in a different thread/process.
    callback(self._player.request_next_action(game_state))
