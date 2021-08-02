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

  def __init__(self, player_id: PlayerId, cheater: bool = False):
    """
    Instantiate a new Player.
    :param player_id: The Id of the player in a game of Schnapsen (Player ONE or
    TWO).
    """
    self._player_id = player_id
    self._game_of_interest = False
    self._cheater = cheater

  # pylint: disable=invalid-name
  @property
  def id(self) -> PlayerId:
    return self._player_id

  # TODO(tests): Add tests for this.
  @property
  def cheater(self) -> bool:
    return self._cheater

  @abc.abstractmethod
  def request_next_action(self, game_view: GameState) -> PlayerAction:
    """
    This method receives the current state of the game as seen from the player's
    perspective and must return the action that the player chose to play.
    """

  @property
  def game_of_interest(self) -> bool:
    """
    This property could be used by subclasses to tag specific games of interest
    and restrict evals to these games (or bummerls containing at least one such
    game).
    """
    return self._game_of_interest

  @game_of_interest.setter
  def game_of_interest(self, value) -> None:
    self._game_of_interest = value
