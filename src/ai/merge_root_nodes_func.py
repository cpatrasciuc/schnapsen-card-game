#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import logging
import pprint
from collections import Counter
from typing import List, Tuple, Callable

from ai.mcts_algorithm import SchnapsenNode
from model.player_action import PlayerAction

MergeRootNodesFunc = Callable[
  [List[SchnapsenNode]], List[Tuple[PlayerAction, float]]]
"""
Function that receives the root nodes for all the permutations processed by an
MCTSPlayer and returns a list with (action, score) tuples, where the score is
some aggregation across all the root nodes for that particular action. Each
action should only appear once in the output.
"""


def most_frequent_best_action(root_nodes: List[SchnapsenNode]) -> List[
  Tuple[PlayerAction, float]]:
  """Returns the most popular action across all root nodes' best actions."""
  best_actions = []
  for root_node in root_nodes:
    best_actions.extend(root_node.best_actions())
  counter = Counter(best_actions)
  action_and_scores = counter.most_common(10)
  logging.info("MCTSPlayer: Best action counts:\n%s",
               pprint.pformat(action_and_scores, indent=True))
  return action_and_scores


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

def merge_ucbs(root_nodes: List[SchnapsenNode]) -> List[
  Tuple[PlayerAction, float]]:
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
  return actions_and_scores


# TODO(tests): Add tests for this function.
def max_average_ucb_across_root_nodes(
    root_nodes: List[SchnapsenNode]) -> List[Tuple[PlayerAction, float]]:
  assert len(set(root_node.player for root_node in root_nodes)) == 1
  return _get_action_scores_for_fully_simulated_trees(root_nodes)
