#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import abc

from model.game_state import GameState
from model.player_action import PlayerAction
from model.player_id import PlayerId


class Player(abc.ABC):
  """
  Player interface that has to be implemented by all the AI algorithms.
  """

  def __init__(self, player_id: PlayerId):
    """
    Instantiate a new Player.
    :param player_id: The Id of the player in a game of Schnapsen (Player ONE or
    TWO).
    """
    self._player_id = player_id

  # pylint: disable=invalid-name
  @property
  def id(self) -> PlayerId:
    return self._player_id

  # TODO(player): Add a GameView class and a GameView argument to this function.
  @abc.abstractmethod
  def request_next_action(self, game_state: GameState) -> PlayerAction:
    """
    This method receives the current state of the game and must return the
    action that the player chose to play.
    """
