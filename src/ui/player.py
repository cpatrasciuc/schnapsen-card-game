#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import abc
import random
from typing import Callable

from model.game_state import GameState
from model.player_action import PlayerAction, get_available_actions, \
  ExchangeTrumpCardAction, AnnounceMarriageAction


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


# TODO(refactor): Replace or move this to the AI package when available.
class RandomPlayer(Player):
  """
  Simple implementation of the Player interface that mostly plays a random
  action from the valid actions in a given game state.
  """

  # pylint: disable=too-few-public-methods

  def request_next_action(self, game_state: GameState,
                          callback: Callable[[PlayerAction], None]) -> None:
    available_actions = get_available_actions(game_state)

    # Exchange trump if available.
    for action in available_actions:
      if isinstance(action, ExchangeTrumpCardAction):
        callback(action)
        return

    # Announce a marriage if available.
    marriages = []
    for action in available_actions:
      if isinstance(action, AnnounceMarriageAction):
        marriages.append(action)

    action = random.choice(
      marriages if len(marriages) > 0 else available_actions)
    callback(action)
