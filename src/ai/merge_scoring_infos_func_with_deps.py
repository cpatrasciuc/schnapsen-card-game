#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# This file contains the merge_scoring_info_func that would add additional
# dependencies (e.g., scipy, numpy) and are only used for debugging/testing.

import logging
import pprint
from collections import defaultdict

from typing import List, Tuple, Union

import numpy as np
from scipy.stats import bootstrap

from ai.merge_scoring_infos_func import ActionsWithScores, AggregatedScores, \
  _merge_ucbs, are_all_nodes_fully_simulated, \
  _average_ucb_for_fully_simulated_trees
from model.player_action import PlayerAction


def _lower_ci_bound(ucbs: List[Tuple[float, int]]) -> float:
  scores = [q / n for q, n in ucbs]
  if len(scores) == 1:
    return scores[0]
  bootstrap_result = bootstrap((scores,), np.mean, method='percentile')
  return bootstrap_result.confidence_interval.low


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
