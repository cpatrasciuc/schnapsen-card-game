#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# distutils: language=c++

from typing import List, Tuple

import numpy as np
import pandas
from pandas import DataFrame
from scipy.stats import bootstrap

from libcpp.vector cimport vector

from ai.cython_mcts_player.card cimport Card
from ai.cython_mcts_player.game_state cimport from_python_game_state, \
  GameState, from_python_player_id, PlayerId
from ai.cython_mcts_player.mcts cimport MAX_CHILDREN
from ai.cython_mcts_player.mcts cimport Node
from ai.cython_mcts_player.mcts cimport run_one_iteration, init_node
from ai.cython_mcts_player.mcts cimport delete_tree
from ai.cython_mcts_player.player cimport build_scoring_info
from ai.cython_mcts_player.player cimport from_python_permutations
from ai.cython_mcts_player.player cimport populate_game_view
from ai.cython_mcts_player.player_action cimport ActionType
from ai.cython_mcts_player.player_action cimport to_python_player_action
from ai.mcts_player import generate_permutations
from ai.mcts_player_options import MctsPlayerOptions
from ai.merge_scoring_infos_func import ActionsWithScores, max_average_ucb
from model.game_state import GameState as PyGameState
from model.player_action import PlayerAction

def _add_rank_column(dataframe: DataFrame) -> None:
  dataframe["rank"] = dataframe["score"].sort_values().rank(method="min",
                                                            ascending=False)

cdef _score_ci(Node *node):
  ci_low = node.ucb
  ci_upp = node.ucb
  if (not node.fully_simulated) and (node.rewards != NULL):
    if node.rewards.size() >= 2:
      ci = bootstrap((list(node.rewards[0]),), np.mean, confidence_level=0.95,
                     method='percentile')
      ci_low = ci.confidence_interval.low
      ci_upp = ci.confidence_interval.high
  if node.player != node.parent.player:
    ci_low, ci_upp = -ci_upp, -ci_low
  return ci_low, ci_upp

cdef _build_scoring_info_with_debug(Node *root_node):
  scoring_info = build_scoring_info(root_node)
  for i in range(MAX_CHILDREN):
    if root_node.actions[i].action_type == ActionType.NO_ACTION:
      break
    if root_node.children[i] == NULL:
      continue
    py_action = to_python_player_action(root_node.actions[i])
    ci_low, ci_upp = _score_ci(root_node.children[i])
    scoring_info[py_action].score_low = ci_low
    scoring_info[py_action].score_upp = ci_upp
  return scoring_info

def _max_average_ucb_with_ci(
    actions_with_scores_list: List[ActionsWithScores]) -> List[
  Tuple[PlayerAction, float, float, float]]:
  """
  Same as max_average_ucb(), but tries to compute come CIs for the final score
  of each action.
  WARNING: This is likely not correct from a statistics point of view.
  """
  scores = {}
  scores_low = {}
  scores_upp = {}
  for actions_with_scores in actions_with_scores_list:
    for action, score in actions_with_scores.items():
      scores[action] = scores.get(action, []) + [score.score]
      if score.score_low is not None:
        scores_low[action] = scores_low.get(action, []) + [score.score_low]
      if score.score_upp is not None:
        scores_upp[action] = scores_upp.get(action, []) + [score.score_upp]
  actions_and_scores = []
  for action, ucbs in scores.items():
    score_low = scores_low[action]
    score_upp = scores_upp[action]
    upp = None
    low = None
    if len(score_low) > 2 and len(score_upp) > 2:
      ci = bootstrap((score_low,), np.mean, method="percentile")
      low = ci.confidence_interval.low
      ci = bootstrap((score_upp,), np.mean, method="percentile")
      upp = ci.confidence_interval.high
    elif len(score_low) == 1 and len(score_upp) == 1:
      low = score_low[0]
      upp = score_upp[0]
    actions_and_scores.append((action, sum(ucbs) / len(ucbs), low, upp))
  return actions_and_scores

cdef _get_children_data(Node *root_node):
  cdef int i
  cdef Node *node
  data = []

  for i in range(MAX_CHILDREN):
    if root_node.actions[i].action_type == ActionType.NO_ACTION:
      break
    if root_node.children[i] == NULL:
      continue
    py_action = to_python_player_action(root_node.actions[i])
    node = root_node.children[i]
    ci_low, ci_upp = _score_ci(node)
    data.append((
      str(py_action),
      (node.q if node.player == root_node.player else -node.q),
      node.n,
      (node.ucb if node.player == root_node.player else -node.ucb),
      node.exploration_score,
      ci_low,
      ci_upp,
    ))

  dataframe = DataFrame(data, columns=["action", "q", "n", "score", "exp_comp",
                                       "score_low", "score_upp"])
  _add_rank_column(dataframe)
  return dataframe

def run_mcts_and_collect_data(py_game_state: PyGameState,
                              options: MctsPlayerOptions,
                              iterations_step: int = 1):
  cdef GameState game_state = from_python_game_state(py_game_state)
  cdef Node *root_node = init_node(&game_state, NULL)
  cdef int iteration = 1
  cdef bint is_fully_simulated = False
  cdef int max_iterations = options.max_iterations
  dataframes = []
  while True:
    for _ in range(iterations_step):
      is_fully_simulated = run_one_iteration(root_node,
                                             options.exploration_param,
                                             options.select_best_child,
                                             options.save_rewards)
      iteration += 1
      if is_fully_simulated:
        break
    dataframe = _get_children_data(root_node)
    dataframe["iteration"] = iteration
    dataframes.append(dataframe)
    if is_fully_simulated:
      break
    if max_iterations is not None and iteration >= max_iterations:
      break
  delete_tree(root_node)
  return pandas.concat(dataframes, ignore_index=True)

def run_mcts_player_step_by_step(py_game_view: PyGameState,
                                 options: MctsPlayerOptions,
                                 iterations_step: int):
  cdef GameState game_view = from_python_game_state(py_game_view)
  cdef GameState game_state
  cdef vector[Node *] root_nodes
  cdef PlayerId opponent_id = from_python_player_id(
    py_game_view.next_player.opponent())

  cdef vector[vector[Card]] permutations
  from_python_permutations(generate_permutations(py_game_view, options),
                           &permutations)

  cdef int i, j
  for i in range(permutations.size()):
    game_state = game_view
    populate_game_view(&game_state, &permutations[i], opponent_id)
    root_nodes.push_back(init_node(&game_state, NULL))

  cdef int iteration = 1
  cdef bint is_fully_simulated, permutation_is_fully_simulated
  dataframes = []
  max_iterations = options.max_iterations
  while True:
    is_fully_simulated = True
    for _ in range(iterations_step):
      is_fully_simulated = True
      for i in range(root_nodes.size()):
        permutation_is_fully_simulated = run_one_iteration(
          root_nodes[i], options.exploration_param, options.select_best_child,
          options.save_rewards)
        is_fully_simulated = \
          is_fully_simulated and permutation_is_fully_simulated
      iteration += 1
      if is_fully_simulated:
        break

    actions_with_scoring_infos = []
    for j in range(root_nodes.size()):
      actions_with_scoring_infos.append(
        _build_scoring_info_with_debug(root_nodes[j]))
    if options.merge_scoring_info_func == max_average_ucb:
      actions_and_scores = _max_average_ucb_with_ci(actions_with_scoring_infos)
      dataframe = DataFrame(
        data=[(str(action), score, score_low, score_upp) for
              action, score, score_low, score_upp in actions_and_scores],
        columns=["action", "score", "score_low", "score_upp"])
    else:
      actions_and_scores = options.merge_scoring_info_func(
        actions_with_scoring_infos)
      dataframe = DataFrame(
        data=[(str(action), score) for action, score in actions_and_scores],
        columns=["action", "score"])

    dataframe["iteration"] = iteration
    _add_rank_column(dataframe)
    dataframes.append(dataframe)

    if is_fully_simulated:
      break
    if max_iterations is not None and iteration >= max_iterations:
      break

  for i in range(root_nodes.size()):
    delete_tree(root_nodes[i])
  return pandas.concat(dataframes, ignore_index=True)
