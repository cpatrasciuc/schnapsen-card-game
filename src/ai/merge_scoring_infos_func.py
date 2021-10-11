#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import dataclasses
import logging
import pprint
from collections import Counter, defaultdict
from typing import List, Tuple, Callable, Dict, Optional, Union

import numpy as np
from scipy.stats import bootstrap

from model.player_action import PlayerAction


@dataclasses.dataclass
class ScoringInfo:
  # pylint: disable=too-many-instance-attributes

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

  rewards: Optional[List[float]] = None
  """
  Individual rewards from all paths going through this action. This is filled
  only if MctsPlayerOptions.save_rewards is True.
  """


ActionsWithScores = Dict[PlayerAction, ScoringInfo]

AggregatedScores = List[Tuple[PlayerAction, float]]
"""
A list containing each action and its aggregated score. An action should only
appear once in the output.
"""

MergeScoringInfosFunc = Callable[[List[ActionsWithScores]], AggregatedScores]
"""
Function that receives the ActionWithScores dictionaries for all the
processed permutations (i.e., one dictionary per root node) and returns a list
with (action, score) tuples, where the score is some aggregation across all the
root nodes for that particular action.
"""


def best_action_frequency(
    actions_with_scores_list: List[ActionsWithScores]) -> AggregatedScores:
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
  actions_and_scores = counter.most_common(10)
  logging.info("MctsPlayer: Best action counts:\n%s",
               pprint.pformat(actions_and_scores, indent=True))
  return actions_and_scores


def are_all_nodes_fully_simulated(
    actions_with_scores_list: List[ActionsWithScores]) -> bool:
  for actions_with_scores in actions_with_scores_list:
    for score in actions_with_scores.values():
      if not score.fully_simulated:
        return False
  return True


MergeUcbsFunc = Callable[[List[Tuple[float, int]]], float]
"""
Function that receives a list of (Q, N) pairs and returns the aggregated score.
"""


def _simple_average_merge_ucbs_func(ucbs: List[Tuple[float, int]]) -> float:
  num = sum(q for q, n in ucbs)
  denom = sum(n for q, n in ucbs)
  return num / denom


def _weighted_average_merge_ucbs_func(ucbs: List[Tuple[float, int]]) -> float:
  num = sum(q * n for q, n in ucbs)
  denom = sum(n for q, n in ucbs)
  return num / denom


def _lower_ci_bound(ucbs: List[Tuple[float, int]]) -> float:
  scores = [q / n for q, n in ucbs]
  if len(scores) == 1:
    return scores[0]
  bootstrap_result = bootstrap((scores,), np.mean, method='percentile')
  return bootstrap_result.confidence_interval.low


def _average_ucb_for_fully_simulated_trees(
    actions_with_scores_list: List[ActionsWithScores]) -> AggregatedScores:
  stats = defaultdict(list)
  for actions_with_scores in actions_with_scores_list:
    for action, score in actions_with_scores.items():
      stats[action].append(score.score)
  actions_and_scores = [(action, sum(ucb) / len(ucb)) for action, ucb in
                        stats.items()]
  # noinspection PyUnreachableCode
  if __debug__:
    logging.debug("MctsPlayer: Average UCBs:\n%s",
                  pprint.pformat(actions_and_scores, indent=True))
  return actions_and_scores


def _average_ucb_for_partially_simulated_trees(
    actions_with_scores_list: List[ActionsWithScores],
    merge_ucb_func: MergeUcbsFunc) -> AggregatedScores:
  stats = defaultdict(list)
  for actions_with_scores in actions_with_scores_list:
    for action, score in actions_with_scores.items():
      if score.fully_simulated:
        q = score.score * score.n
        n = score.n
      else:
        q = score.q
        n = score.n
      stats[action].append((q, n))
  actions_and_scores = [(action, merge_ucb_func(ucbs)) for action, ucbs in
                        stats.items()]
  return actions_and_scores


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
def _merge_ucbs(
    actions_with_scores_list: List[ActionsWithScores],
    merge_ucb_func: MergeUcbsFunc) -> AggregatedScores:
  is_fully_simulated = are_all_nodes_fully_simulated(actions_with_scores_list)
  if is_fully_simulated:
    actions_and_scores = _average_ucb_for_fully_simulated_trees(
      actions_with_scores_list)
  else:
    actions_and_scores = _average_ucb_for_partially_simulated_trees(
      actions_with_scores_list, merge_ucb_func)
  # noinspection PyUnreachableCode
  if __debug__:
    logging.debug("MctsPlayer: Merged UCBs:\n%s",
                  pprint.pformat(sorted(actions_and_scores, key=lambda x: x[1],
                                        reverse=True)))
  return actions_and_scores


def merge_ucbs_using_simple_average(
    actions_with_scores_list: List[ActionsWithScores]) -> AggregatedScores:
  return _merge_ucbs(actions_with_scores_list, _simple_average_merge_ucbs_func)


def merge_ucbs_using_weighted_average(
    actions_with_scores_list: List[ActionsWithScores]) -> AggregatedScores:
  return _merge_ucbs(actions_with_scores_list,
                     _weighted_average_merge_ucbs_func)


def merge_ucbs_using_lower_ci_bound(
    actions_with_scores_list: List[ActionsWithScores]) -> AggregatedScores:
  """
  The aggregated score is the lower CI bound of the mean of the scores coming
  from each permutation.
  """
  return _merge_ucbs(actions_with_scores_list, _lower_ci_bound)


def lower_ci_bound_on_raw_rewards(
    actions_with_scores_list: List[ActionsWithScores],
    debug: bool = False) -> Union[
  AggregatedScores, List[Tuple[PlayerAction, float, float, float]]]:
  """
  The aggregated score is the lower CI bound of the mean of all the individual
  rewards across all permutations (i.e., it doesn't compute averages for each
  permutation first). This requires MctsPlayerOptions.save_rewards to be True.
  If debug is True, the output contains the CI limits as well.
  WARNING: This is very slow.
  """
  # pylint: disable=too-many-branches
  is_fully_simulated = are_all_nodes_fully_simulated(actions_with_scores_list)
  if is_fully_simulated:
    return _average_ucb_for_fully_simulated_trees(actions_with_scores_list)

  stats = defaultdict(list)
  for actions_with_scores in actions_with_scores_list:
    for action, score in actions_with_scores.items():
      if score.fully_simulated:
        stats[action].extend([score.score for _ in range(score.n)])
      else:
        stats[action].extend(score.rewards)

  actions_and_scores = []
  for action, rewards in stats.items():
    if len(rewards) == 1:
      if debug:
        actions_and_scores.append((action, rewards[0], rewards[0], rewards[0]))
      else:
        actions_and_scores.append((action, rewards[0]))
    else:
      bootstrap_result = bootstrap((rewards,), np.mean, method='percentile',
                                   n_resamples=1000)
      confidence_interval = bootstrap_result.confidence_interval
      if debug:
        actions_and_scores.append((action, confidence_interval.low,
                                   confidence_interval.low,
                                   confidence_interval.high))
      else:
        actions_and_scores.append((action, confidence_interval.low))
  # noinspection PyUnreachableCode
  if __debug__:
    logging.debug("MctsPlayer: Lower CI bounds on raw rewards:\n%s",
                  pprint.pformat(
                    sorted(actions_and_scores, key=lambda x: x[1],
                           reverse=True)))
  return actions_and_scores


def average_ucb(
    actions_with_scores_list: List[ActionsWithScores]) -> AggregatedScores:
  """
  The aggregated score for each action is the arithmetic mean of its scores
  from each permutation.
  """
  return _average_ucb_for_fully_simulated_trees(actions_with_scores_list)


def count_visits(
    actions_with_scores_list: List[ActionsWithScores]) -> AggregatedScores:
  """
  If all permutations are fully simulated, this is identical to average_ucb().
  Otherwise, the aggregated score for each action is the total number of visits
  this action got across all permutations.
  """
  is_fully_simulated = are_all_nodes_fully_simulated(actions_with_scores_list)
  if is_fully_simulated:
    return _average_ucb_for_fully_simulated_trees(
      actions_with_scores_list)
  stats = defaultdict(float)
  for action_with_scores in actions_with_scores_list:
    for action, scoring_info in action_with_scores.items():
      stats[action] += scoring_info.n
  return list(stats.items())
