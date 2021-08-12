#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import copy
import pprint
import random
import time
from collections import Counter
from math import factorial
from typing import List

import mcts

from ai.player import Player
from ai.utils import populate_game_view
from model.card import Card
from model.game_state import GameState
from model.player_action import get_available_actions, PlayerAction
from model.player_id import PlayerId


class _State:
  """Internal game state representation for the mcts package."""

  # pylint: disable=invalid-name

  def __init__(self, player_id: PlayerId, game_state: GameState):
    self._player_id = player_id
    self._game_state = game_state

  def getPossibleActions(self) -> List[PlayerAction]:
    """Returns an iterable of all actions which can be taken from this state."""
    actions = get_available_actions(self._game_state)
    return actions

  def takeAction(self, action: PlayerAction) -> "_State":
    """Returns the state which results from taking the given action."""
    new_game_state = copy.deepcopy(self._game_state)
    try:
      action.execute(new_game_state)
    except:
      pprint.pprint(str(self._game_state))
      print(action)
      raise
    return _State(self._player_id, new_game_state)

  def isTerminal(self) -> bool:
    """Returns whether this state is a terminal state."""
    return self._game_state.is_game_over

  def getReward(self) -> float:
    """Returns the reward for this state. Only needed for terminal states."""
    score = self._game_state.game_points
    points_diff = score[self._player_id] - score[self._player_id.opponent()]
    return points_diff / 3.0


class LibMctsPlayer(Player):
  """Player implementation that uses the mcts Python package."""

  def __init__(self, player_id: PlayerId, time_limit_sec: float = 1,
               max_permutations: int = 100):
    """
    Creates a new LibMctsPlayer.
    :param player_id: The ID of the player in a game of Schnapsen (ONE or TWO).
    :param time_limit_sec: The maximum amount of time (in seconds) that the
    player can use to pick an action, when requested.
    :param max_permutations: The player converts an imperfect-information game
    to a perfect-information game by using a random permutation of the unseen
    cards set. This parameter controls how many such permutations are used
    in the given amount of time. The player then picks the most common best
    action across all the simulated scenarios.
    """
    super().__init__(player_id)
    self._time_limit_sec = time_limit_sec
    self._max_permutations = max_permutations

  def request_next_action(self, game_view: GameState) -> PlayerAction:
    cards_set = game_view.cards_in_hand.one + game_view.cards_in_hand.two + \
                game_view.talon + [game_view.trump_card] + \
                [game_view.current_trick[self.id.opponent()]] + \
                [trick.one for trick in game_view.won_tricks.one] + \
                [trick.two for trick in game_view.won_tricks.one] + \
                [trick.one for trick in game_view.won_tricks.two] + \
                [trick.two for trick in game_view.won_tricks.two]
    cards_set = {card for card in Card.get_all_cards() if card not in cards_set}
    cards_set = list(sorted(cards_set))

    best_actions = []
    num_permutations = min(factorial(len(cards_set)), self._max_permutations)

    start_sec = time.process_time()

    while True:
      permutation = copy.deepcopy(cards_set)
      random.shuffle(permutation)
      game_state = populate_game_view(game_view, permutation)
      initial_state = _State(self.id, game_state)
      algorithm = mcts.mcts(
        timeLimit=self._time_limit_sec * 1000 / num_permutations)
      best_action = algorithm.search(initialState=initial_state)
      best_actions.append(best_action)
      end_sec = time.process_time()
      if end_sec - start_sec > self._time_limit_sec:
        break

    return Counter(best_actions).most_common(1)[0][0]
