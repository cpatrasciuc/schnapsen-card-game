#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import abc

from model.game_state import GameState
from model.player_id import PlayerId


class PlayerAction(abc.ABC):
  """
  Abstract base class for all possible player actions.

  The subclasses corresponding to each action are the following:

  * PlayCardAction - play a card from hand; it's used for both cards in a trick.
  * AnnounceMarriageAction - announce a marriage and play one of the two cards.
  * ExchangeTrumpCardAction - exchange the trump jack in hand for the trump
    card on the table.
  * CloseTheTalonAction - close the talon.
  """

  def __init__(self, player_id: PlayerId):
    """
    Instantiates a new player action.
    :param player_id: The player that will perform this action.
    """
    assert player_id is not None
    self._player_id = player_id

  @property
  def player_id(self):
    return self._player_id

  @abc.abstractmethod
  def can_execute_on(self, game_state: GameState) -> bool:
    """
    Abstract method that must return True if this action is a legal action, in
    the situation represented by the game state provided as an argument.
    """

  @abc.abstractmethod
  def execute(self, game_state: GameState):
    """
    Abstract method that must perform the necessary changes corresponding to
    performing this player action on the game state provided as an argument.
    The action must be a legal action given the currest state of the game.
    This can be checked with can_execute_on().
    """


class CloseTheTalonAction(PlayerAction):
  """The player who is to lead closes the talon."""

  def can_execute_on(self, game_state: GameState) -> bool:
    if not game_state.on_lead(self.player_id):
      return False
    if game_state.is_talon_closed:
      return False
    if len(game_state.talon) == 0:
      return False
    return True

  def execute(self, game_state: GameState):
    assert self.can_execute_on(game_state)
    game_state.close_talon()
