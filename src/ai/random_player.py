#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import random
from typing import Optional

from ai.player import Player
from ai.utils import get_best_marriage
from model.game_state import GameState
from model.player_action import PlayerAction, get_available_actions, \
  CloseTheTalonAction, ExchangeTrumpCardAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair


class RandomPlayer(Player):
  """
  Simple implementation of the Player interface that plays a random action from
  the valid actions in a given game state.
  """

  def __init__(self, player_id: PlayerId,
               force_trump_exchange: bool = False,
               never_close_talon: bool = False,
               force_marriage_announcement: bool = False):
    """
    Create a new RandomPlayer.
    :param player_id: The Id of the player in a game of Schnapsen (Player ONE or
    TWO).
    :param force_trump_exchange: If True, and this player is to lead and it can
    exchange the trump card with the trump jack, it will do it right away.
    :param never_close_talon: The player will never close the talon, even if the
    action is available in a given game state.
    :param force_marriage_announcement: If True, the player will always announce
    a marriage if available. If it has the trump marriage, it will announce it.
    If it only has one or two non-trump marriages, it will announce one of them
    randomly. It will play a random card from the chosen marriage.
    force_trump_exchange has priority over this option, since the player can
    announce the marriage after exchanging the trump card.
    """
    super().__init__(player_id)
    self._force_trump_exchange = force_trump_exchange
    self._never_close_talon = never_close_talon
    self._force_marriage_announcement = force_marriage_announcement

  def request_next_action(self, game_view: GameState, game_points: Optional[
    PlayerPair[int]] = None) -> PlayerAction:
    assert game_view.next_player == self.id, "Not my turn"
    available_actions = get_available_actions(game_view)
    if self._never_close_talon:
      available_actions = [action for action in available_actions if
                           not isinstance(action, CloseTheTalonAction)]

    if self._force_trump_exchange:
      for action in available_actions:
        if isinstance(action, ExchangeTrumpCardAction):
          return action

    if self._force_marriage_announcement:
      marriage = get_best_marriage(available_actions, game_view.trump)
      if marriage is not None:
        return marriage

    return random.choice(available_actions)
