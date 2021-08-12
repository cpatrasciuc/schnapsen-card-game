#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import copy
import functools
import logging
import math
import multiprocessing
import pprint
import random
from collections import Counter
from math import factorial
from typing import List, Optional

from ai.mcts_algorithm import MCTS
from ai.player import Player
from ai.utils import populate_game_view
from model.card import Card
from model.game_state import GameState
from model.player_action import PlayerAction
from model.player_id import PlayerId


def _run_mcts(permutation: List[Card], game_view: GameState,
              player_id: PlayerId, time_limit_sec: float) -> PlayerAction:
  game_state = populate_game_view(game_view, permutation)
  mcts_algorithm = MCTS(player_id)
  return mcts_algorithm.search(game_state, time_limit_sec)


class MctsPlayer(Player):
  """Player implementation that uses the MCTS algorithm."""

  def __init__(self, player_id: PlayerId, cheater: bool,
               time_limit_sec: float = 1, max_permutations: int = 100,
               num_processes: Optional[int] = None):
    """
    Creates a new LibMctsPlayer.
    :param player_id: The ID of the player in a game of Schnapsen (ONE or TWO).
    :param time_limit_sec: The maximum amount of time (in seconds) that the
    player can use to pick an action, when requested.
    :param max_permutations: The player converts an imperfect-information game
    to a perfect-information game by using a random permutation of the unseen
    cards set. This parameter controls how many such permutations are used
    in the given amount of time. The player then picks the most common best
    action across all the simulated scenarios. If max_permutations is not a
    multiple of num_processes it will be rounded up to the next multiple.
    :param num_processes The number of processes to be used in the pool to
    process the permutations in parallel. If None, the pool will use cpu_count()
    processes.
    """
    # pylint: disable=too-many-arguments
    super().__init__(player_id, cheater)
    self._time_limit_sec = time_limit_sec
    self._max_permutations = max_permutations
    self._num_processes = num_processes or multiprocessing.cpu_count()
    # pylint: disable=consider-using-with
    self._pool = multiprocessing.Pool(processes=self._num_processes)
    # pylint: enable=consider-using-with

  def cleanup(self):
    self._pool.terminate()
    self._pool.join()

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

    num_permutations = min(factorial(len(cards_set)), self._max_permutations)
    while num_permutations % self._num_processes != 0:
      num_permutations += 1
    logging.info("MCTSPlayer: Num permutations: %s out of %s", num_permutations,
                 factorial(len(cards_set)))

    permutations = []
    for _ in range(num_permutations):
      permutation = copy.deepcopy(cards_set)
      random.shuffle(permutation)
      permutations.append(permutation)

    time_limit_per_permutation = self._time_limit_sec / math.ceil(
      num_permutations / self._num_processes)
    # TODO(optimization): Experiment with imap_unordered as well.
    best_actions = self._pool.map(
      functools.partial(_run_mcts, game_view=game_view, player_id=self.id,
                        time_limit_sec=time_limit_per_permutation),
      permutations)

    counter = Counter(best_actions)
    logging.info("MCTSPlayer: Best action counts:\n%s",
                 pprint.pformat(counter.most_common(10), indent=True))
    return counter.most_common(1)[0][0]
