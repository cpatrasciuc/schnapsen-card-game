#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import dataclasses
import logging
import pprint
from collections import Counter
from typing import List, Tuple, Callable, Dict, Optional

from model.player_action import PlayerAction


@dataclasses.dataclass
class ScoringInfo:
  """
  A simplified data structure that only has the fields from an Mcts Node that
  are used in selecting the best action across all the Mcts trees.
  """
  q: float
  """Same as Node.q, but from the player's perspective"""
  n: int
  score: float
  """Same as Node.ucb, but from the player's perspective"""
  fully_simulated: bool
  terminal: bool

  score_low: Optional[float] = None
  """An optional lower bound for score in case CIs are used"""
  score_upp: Optional[float] = None
  """An optional upper bound for score in case CIs are used"""


ActionsWithScores = Dict[PlayerAction, ScoringInfo]

MergeScoringInfosFunc = Callable[
  [List[ActionsWithScores]], List[Tuple[PlayerAction, float]]]
"""
Function that receives the ActionWithScores dictionaries for all the
processed permutations (i.e., one dictionary per root node) and returns a list
with (action, score) tuples, where the score is some aggregation across all the
root nodes for that particular action. Each action should only appear once in
the output.
"""


def best_action_frequency(
    actions_with_scores_list: List[ActionsWithScores]) -> List[
  Tuple[PlayerAction, float]]:
  """
  The aggregated score returned for each action is the number of permutations
  for which the action is the best action. One or more actions are considered
  the best action(s) for a permutation if they have the maximum score among all
  actions for that particular permutation.
  """
  best_actions = []
  for actions_with_scores in actions_with_scores_list:
    max_score = max(score.score for _, score in actions_with_scores.items())
    best_actions.extend(
      [action for action, score in actions_with_scores.items() if
       score.score == max_score])
  counter = Counter(best_actions)
  action_and_scores = counter.most_common(10)
  logging.info("MctsPlayer: Best action counts:\n%s",
               pprint.pformat(action_and_scores, indent=True))
  return action_and_scores


if __debug__:
  def _assert_action_is_terminal_across_root_nodes(
      actions_with_scores_list: List[ActionsWithScores],
      action: PlayerAction) -> None:
    for actions_with_scores in actions_with_scores_list:
      score = actions_with_scores.get(action, None)
      # TODO(tests): Double check this is not a bug. This means this action was
      #  not even visited for this root node.
      if score is None:
        continue
      assert score.terminal


def _all_nodes_are_fully_simulated(
    actions_with_scores_list: List[ActionsWithScores]) -> bool:
  is_fully_simulated = True
  for actions_with_scores in actions_with_scores_list:
    for score in actions_with_scores.values():
      if not score.fully_simulated:
        is_fully_simulated = False
        break
    if not is_fully_simulated:
      break
  return is_fully_simulated


# TODO(mcts): Can we aggregate better across permutations? Here we weight each
#  permutation by how many times a given action was visited for that
#  simulation. In max_average_ucb() we weight all permutations equally.
def _agg_ucb(ucbs: List[Tuple[float, int]]) -> float:
  num = sum(q * n for q, n in ucbs)
  denom = sum(n for q, n in ucbs)
  return num / denom


def _get_action_scores_for_fully_simulated_trees(
    actions_with_scores_list: List[ActionsWithScores]) -> List[
  Tuple[PlayerAction, float]]:
  stats = {}
  for actions_with_scores in actions_with_scores_list:
    for action, score in actions_with_scores.items():
      stats[action] = stats.get(action, []) + [score.score]
  if __debug__:
    pprint.pprint(stats)
  actions_and_scores = [(action, sum(ucb) / len(ucb)) for action, ucb in
                        stats.items()]
  return actions_and_scores


def _get_action_scores_for_partially_simulated_trees(
    actions_with_scores_list: List[ActionsWithScores]) -> List[
  Tuple[PlayerAction, float]]:
  stats = {}
  for actions_with_scores in actions_with_scores_list:
    for action, score in actions_with_scores.items():
      if score.terminal:
        if __debug__:
          _assert_action_is_terminal_across_root_nodes(actions_with_scores,
                                                       action)
        q = score.score
        # TODO(mcts): We could us the real value of score.n here.
        n = 1
      else:
        q = score.q
        n = score.n
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
# to be expanded in Mcts and/or consider the best node to be the mode visited
# one.

def merge_ucbs(actions_with_scores_list: List[ActionsWithScores]) -> List[
  Tuple[PlayerAction, float]]:
  is_fully_simulated = _all_nodes_are_fully_simulated(actions_with_scores_list)
  if is_fully_simulated:
    actions_and_scores = _get_action_scores_for_fully_simulated_trees(
      actions_with_scores_list)
  else:
    actions_and_scores = _get_action_scores_for_partially_simulated_trees(
      actions_with_scores_list)
  if __debug__:
    pprint.pprint(sorted(actions_and_scores, key=lambda x: x[1], reverse=True))
  return actions_and_scores


# TODO(tests): Add tests for this function.
def max_average_ucb(actions_with_scores_list: List[ActionsWithScores]) -> List[
  Tuple[PlayerAction, float]]:
  return _get_action_scores_for_fully_simulated_trees(actions_with_scores_list)


# TODO(tests): Add tests for this function.
def most_visited_node(actions_with_scores_list: List[ActionsWithScores]) -> \
    List[Tuple[PlayerAction, float]]:
  is_fully_simulated = _all_nodes_are_fully_simulated(actions_with_scores_list)
  if is_fully_simulated:
    return _get_action_scores_for_fully_simulated_trees(
      actions_with_scores_list)
  stats: Dict[PlayerAction, float] = {}
  for action_with_scores in actions_with_scores_list:
    for action, scoring_info in action_with_scores.items():
      stats[action] = stats.get(action, 0) + scoring_info.n
  return list(stats.items())
