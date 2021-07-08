#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import copy
import logging
import random
import time
from collections import Counter
from math import factorial
from typing import List

from ai.mcts_algorithm import MCTS
from ai.player import Player
from model.card import Card
from model.game_state import GameState
from model.player_action import PlayerAction
from model.player_id import PlayerId


class MctsPlayer(Player):
  """Player implementation that uses the MCTS algorithm."""

  def __init__(self, player_id: PlayerId, cheater: bool,
               time_limit_sec: float = 1, max_permutations: int = 100):
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
    super().__init__(player_id, cheater)
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
    played_card = game_view.current_trick[self.id.opponent()]
    opp_cards = game_view.cards_in_hand[self.id.opponent()]
    if played_card is not None and played_card not in opp_cards:
      index = opp_cards.index(None)
      opp_cards[index] = played_card

    best_actions = []
    num_permutations = min(factorial(len(cards_set)), self._max_permutations)
    logging.info("MCTSPlayer: Num permutations: %s out of %s", num_permutations,
                 factorial(len(cards_set)))

    start_sec = time.process_time()

    while True:
      permutation = copy.deepcopy(cards_set)
      random.shuffle(permutation)
      game_state = self._populate_game_view(game_view, list(permutation))
      mcts_algorithm = MCTS(self.id)
      best_action = mcts_algorithm.search(
        game_state, self._time_limit_sec / num_permutations)
      best_actions.append(best_action)
      end_sec = time.process_time()
      if end_sec - start_sec > self._time_limit_sec:
        break

    return Counter(best_actions).most_common(1)[0][0]

  def _populate_game_view(self, game_view: GameState,
                          permutation: List[Card]) -> GameState:
    """
    Fill in the unknown cards in the opponent's hand and in the talon in order
    with the cards from permutation. Returns the resulting perfect information
    GameState.
    """
    game_state = copy.deepcopy(game_view)
    opp_cards = game_state.cards_in_hand[self.id.opponent()]
    for i, opp_card in enumerate(opp_cards):
      if opp_card is None:
        opp_cards[i] = permutation.pop()
    for i, talon_card in enumerate(game_state.talon):
      if talon_card is None:
        game_state.talon[i] = permutation.pop()
    return game_state
