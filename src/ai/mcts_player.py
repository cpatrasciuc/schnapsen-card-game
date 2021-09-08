#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import functools
import logging
import math
import multiprocessing
import random
from typing import List, Optional

from ai.mcts_algorithm import Mcts, SchnapsenNode
from ai.mcts_player_options import MctsPlayerOptions
from ai.player import Player
from ai.utils import populate_game_view, get_unseen_cards
from model.card import Card
from model.game_state import GameState
from model.player_action import PlayerAction
from model.player_id import PlayerId


def run_mcts(permutation: List[Card], game_view: GameState,
             player_id: PlayerId, max_iterations: int,
             first_level_only: bool) -> SchnapsenNode:
  game_state = populate_game_view(game_view, permutation)
  mcts_algorithm = Mcts(player_id)
  root_node = mcts_algorithm.build_tree(game_state, max_iterations)
  if first_level_only:
    for child in root_node.children.values():
      if child is not None and not child.terminal:
        del child.children
  return root_node


class MctsPlayer(Player):
  """Player implementation that uses the Mcts algorithm."""

  def __init__(self, player_id: PlayerId, cheater: bool = False,
               options: Optional[MctsPlayerOptions] = None):
    """
    Creates a new LibMctsPlayer.
    :param player_id: The ID of the player in a game of Schnapsen (ONE or TWO).
    :param cheater: If True, this player will always know the cards in their
    opponent's hand and the order of the cards in the talon.
    :param options: The parameters used to configure the MctsPlayer.
    """
    # pylint: disable=too-many-arguments
    super().__init__(player_id, cheater)
    self._options = options or MctsPlayerOptions()
    # pylint: disable=consider-using-with
    self._pool = multiprocessing.Pool(processes=self._options.num_processes)
    # pylint: enable=consider-using-with
    logging.info("MctsPlayer: Multiprocessing pool using %s processes.",
                 self._options.num_processes)

  def cleanup(self):
    self._pool.terminate()
    self._pool.join()

  def request_next_action(self, game_view: GameState) -> PlayerAction:
    # pylint: disable=too-many-locals
    cards_set = get_unseen_cards(game_view)
    assert len(cards_set) == 0 or not self.cheater, cards_set
    num_unknown_cards = len(cards_set)
    num_opponent_unknown_cards = len(
      [card for card in game_view.cards_in_hand[self.id.opponent()] if
       card is None])
    total_permutations = \
      math.comb(num_unknown_cards, num_opponent_unknown_cards) * \
      math.perm(num_unknown_cards - num_opponent_unknown_cards)
    num_permutations_to_process = min(total_permutations,
                                      self._options.max_permutations)
    assert num_permutations_to_process == 1 or not self.cheater
    logging.info("MctsPlayer: Num permutations: %s out of %s",
                 num_permutations_to_process, total_permutations)

    permutations = self._options.perm_generator(
      cards_set, num_opponent_unknown_cards, num_permutations_to_process)

    root_nodes = self._pool.map(
      functools.partial(run_mcts, game_view=game_view, player_id=self.id,
                        max_iterations=self._options.max_iterations,
                        first_level_only=self._options.first_level_only),
      permutations)

    if __debug__:
      for root_node in root_nodes:
        for action, child in root_node.children.items():
          print(action, "-->", child)
        print()

    # TODO(mcts): If multiple actions have the same score, use tiebreakers like
    #  ucb, card value * sign(ucb).
    actions_and_scores = self._options.merge_root_nodes_func(root_nodes)
    best_score = max(score for action, score in actions_and_scores)
    best_actions = \
      [action for action, score in actions_and_scores if score == best_score]
    return random.choice(best_actions)
