#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import functools
import logging
import math
import multiprocessing
import pprint
import random
from collections import Counter
from typing import List, Optional, Callable, Tuple

from ai.mcts_algorithm import MCTS, SchnapsenNode
from ai.permutations import PermutationsGenerator, sims_table_perm_generator
from ai.player import Player
from ai.utils import populate_game_view, get_unseen_cards
from model.card import Card
from model.game_state import GameState
from model.player_action import PlayerAction
from model.player_id import PlayerId


def _run_mcts(permutation: List[Card], game_view: GameState,
              player_id: PlayerId, time_limit_sec: float) -> SchnapsenNode:
  game_state = populate_game_view(game_view, permutation)
  mcts_algorithm = MCTS(player_id)
  return mcts_algorithm.build_tree(game_state, time_limit_sec)


MergeRootNodesFunc = Callable[[List[SchnapsenNode]], PlayerAction]
"""
Function that receives the root nodes for all the permutations processed by an
MCTSPlayer and returns the action that the player chose to play, after taking
into account the data from all these trees.
"""


def most_frequent_best_action(root_nodes: List[SchnapsenNode]) -> PlayerAction:
  """Returns the most popular action across all root nodes' best actions."""
  best_actions = []
  for root_node in root_nodes:
    best_actions.extend(root_node.best_actions())
  counter = Counter(best_actions)
  logging.info("MCTSPlayer: Best action counts:\n%s",
               pprint.pformat(counter.most_common(10), indent=True))
  return counter.most_common(1)[0][0]


if __debug__:
  def _assert_action_is_terminal_across_root_nodes(
      root_nodes: List[SchnapsenNode], action: PlayerAction) -> None:
    for root_node in root_nodes:
      child = root_node.children[action]
      # TODO(tests): Double check this is not a bug. This means this action was
      #  not even visited for this root node.
      if child is None:
        continue
      assert child.terminal


def _all_nodes_are_fully_simulated(root_nodes: List[SchnapsenNode]) -> bool:
  is_fully_expanded = True
  for root_node in root_nodes:
    for child in root_node.children.values():
      if child is None or not child.fully_simulated:
        is_fully_expanded = False
        break
    if not is_fully_expanded:
      break
  return is_fully_expanded


# TODO(mcts): Can we aggregate better across permutations? Here we weight each
#  permutation by how many times a given action was visited for that
#  simulation. In max_average_ucb_across_root_nodes() we weight all permutations
#  equally.
def _agg_ucb(ucbs: List[Tuple[float, int]]) -> float:
  num = sum(q * n for q, n in ucbs)
  denom = sum(n for q, n in ucbs)
  return num / denom


def _get_action_scores_for_fully_simulated_trees(
    root_nodes: List[SchnapsenNode]) -> List[Tuple[PlayerAction, float]]:
  player_id = root_nodes[0].player
  stats = {}
  for root_node in root_nodes:
    for action, child in root_node.children.items():
      if child is None:
        continue
      stats[action] = stats.get(action, []) + [
        child.ucb if child.player == player_id else -child.ucb]
  if __debug__:
    pprint.pprint(stats)
  actions_and_scores = [(action, sum(ucb) / len(ucb)) for action, ucb in
                        stats.items()]
  return actions_and_scores


def _get_action_scores_for_partially_simulated_trees(
    root_nodes: List[SchnapsenNode]) -> List[Tuple[PlayerAction, float]]:
  player_id = root_nodes[0].player
  stats = {}
  for root_node in root_nodes:
    for action, child in root_node.children.items():
      if child is None:
        continue
      if child.terminal:
        if __debug__:
          _assert_action_is_terminal_across_root_nodes(root_nodes, action)
        q = child.ucb if child.player == player_id else -child.ucb
        n = 1
      else:
        q = child.q if child.player == player_id else -child.q
        n = child.n
      stats[action] = stats.get(action, []) + [(q, n)]
  if __debug__:
    pprint.pprint(stats)
  actions_and_scores = [(action, _agg_ucb(ucbs)) for action, ucbs in
                        stats.items()]
  return actions_and_scores


# TODO(tests): Add tests for this function.
# This function doesn't work if the children of a root node are terminal nodes.
# If the nodes to be expanded are chosen randomly, using Q and N directly might
# only increase the confidence of scenarios that where visited more frequently.
# On the other hand, terminal children should have the highest confidence, but
# are only visited once. I think if the next action leads to a terminal node, it
# does so in all permutations. If that is the case, we should just average the
# ucb (i.e., we never have to merge terminal and non-terminal children for the
# same action across two different permutations).
# Leaving this function here in case we can use it when we pick the best child
# to be expanded in MCTS and/or consider the best node to be the mode visited
# one.
def merge_ucbs(root_nodes: List[SchnapsenNode]) -> PlayerAction:
  assert len(set(root_node.player for root_node in root_nodes)) == 1
  is_fully_simulated = _all_nodes_are_fully_simulated(root_nodes)
  if is_fully_simulated:
    actions_and_scores = _get_action_scores_for_fully_simulated_trees(
      root_nodes)
  else:
    actions_and_scores = _get_action_scores_for_partially_simulated_trees(
      root_nodes)
  if __debug__:
    pprint.pprint(sorted(actions_and_scores, key=lambda x: x[1], reverse=True))
  best_score = max(score for action, score in actions_and_scores)
  best_actions = \
    [action for action, score in actions_and_scores if score == best_score]
  return random.choice(best_actions)


# TODO(tests): Add tests for this function.
def max_average_ucb_across_root_nodes(
    root_nodes: List[SchnapsenNode]) -> PlayerAction:
  assert len(set(root_node.player for root_node in root_nodes)) == 1
  actions_and_scores = _get_action_scores_for_fully_simulated_trees(root_nodes)
  best_score = max(score for action, score in actions_and_scores)
  best_actions = \
    [action for action, score in actions_and_scores if score == best_score]
  return random.choice(best_actions)


class MctsPlayer(Player):
  """Player implementation that uses the MCTS algorithm."""

  def __init__(self, player_id: PlayerId, cheater: bool = False,
               time_limit_sec: Optional[float] = 1, max_permutations: int = 100,
               num_processes: Optional[int] = None,
               perm_generator: Optional[PermutationsGenerator] = None,
               merge_root_nodes_func: Optional[MergeRootNodesFunc] = None):
    """
    Creates a new LibMctsPlayer.
    :param player_id: The ID of the player in a game of Schnapsen (ONE or TWO).
    :param cheater: If True, this player will always know the cards in their
    opponent's hand and the order of the cards in the talon.
    :param time_limit_sec: The maximum amount of time (in seconds) that the
    player can use to pick an action, when requested. If None, there is no time
    limit.
    :param max_permutations: The player converts an imperfect-information game
    to a perfect-information game by using a random permutation of the unseen
    cards set. This parameter controls how many such permutations are used
    in the given amount of time. The player then picks the most common best
    action across all the simulated scenarios. If max_permutations is not a
    multiple of num_processes it will be rounded up to the next multiple.
    :param num_processes The number of processes to be used in the pool to
    process the permutations in parallel. If None, the pool will use cpu_count()
    processes.
    :param perm_generator The function that generates the permutations of the
    unseen cards set that will be processed when request_next_action() is
    called.
    :param merge_root_nodes_func The function that receives all the trees
    corresponding to all the processed permutations, merges the information and
    picks the best action to be played.
    """
    # pylint: disable=too-many-arguments
    super().__init__(player_id, cheater)
    self._time_limit_sec = time_limit_sec
    self._max_permutations = max_permutations
    self._num_processes = num_processes or multiprocessing.cpu_count()
    # pylint: disable=consider-using-with
    self._pool = multiprocessing.Pool(processes=self._num_processes)
    # pylint: enable=consider-using-with
    self._perm_generator = perm_generator or sims_table_perm_generator
    self._merge_root_nodes_func = merge_root_nodes_func or \
                                  max_average_ucb_across_root_nodes

  def cleanup(self):
    self._pool.terminate()
    self._pool.join()

  def request_next_action(self, game_view: GameState) -> PlayerAction:
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
                                      self._max_permutations)
    assert num_permutations_to_process == 1 or not self.cheater
    logging.info("MCTSPlayer: Num permutations: %s out of %s",
                 num_permutations_to_process, total_permutations)

    permutations = self._perm_generator(cards_set, num_opponent_unknown_cards,
                                        num_permutations_to_process)

    if self._time_limit_sec is None:
      time_limit_per_permutation = None
    else:
      time_limit_per_permutation = self._time_limit_sec / math.ceil(
        num_permutations_to_process / self._num_processes)

    # TODO(optimization): Experiment with imap_unordered as well.
    root_nodes = self._pool.map(
      functools.partial(_run_mcts, game_view=game_view, player_id=self.id,
                        time_limit_sec=time_limit_per_permutation),
      permutations)

    if __debug__:
      for root_node in root_nodes:
        for action, child in root_node.children.items():
          print(action, "-->", child)
        print()

    # TODO(mcts): If multiple actions have the same score, use tiebreakers like
    #  ucb, card value * sign(ucb).
    return self._merge_root_nodes_func(root_nodes)
