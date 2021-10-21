#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# distutils: language=c++

from collections import defaultdict
from typing import List, Tuple, Optional

import numpy as np
import pandas
from pandas import DataFrame
from scipy.stats import bootstrap

from libcpp.vector cimport vector

from ai.cython_mcts_player.card cimport Card
from ai.cython_mcts_player.game_state cimport from_python_game_state, \
  GameState, from_python_player_id, PlayerId, Points
from ai.cython_mcts_player.mcts cimport MAX_CHILDREN
from ai.cython_mcts_player.mcts cimport ActionNode
from ai.cython_mcts_player.mcts cimport Node
from ai.cython_mcts_player.mcts cimport build_tree
from ai.cython_mcts_player.mcts cimport run_one_iteration, init_node
from ai.cython_mcts_player.mcts cimport run_one_is_iteration
from ai.cython_mcts_player.mcts cimport delete_tree
from ai.cython_mcts_player.player cimport build_scoring_info
from ai.cython_mcts_player.player cimport from_python_permutations
from ai.cython_mcts_player.player cimport populate_game_view
from ai.cython_mcts_player.player_action cimport ActionType
from ai.cython_mcts_player.player_action cimport PlayerAction
from ai.cython_mcts_player.player_action cimport get_available_actions
from ai.cython_mcts_player.player_action cimport to_python_player_action
from ai.heuristic_player import HeuristicPlayer
from ai.mcts_player import generate_permutations
from ai.mcts_player_options import MctsPlayerOptions
from ai.merge_scoring_infos_func import ActionsWithScores, average_ucb, \
  are_all_nodes_fully_simulated
from ai.merge_scoring_infos_func_with_deps import lower_ci_bound_on_raw_rewards
from model.game_state import GameState as PyGameState
from model.player_action import PlayerAction as PyPlayerAction
from model.player_pair import PlayerPair

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

def _average_ucb_with_ci(
    actions_with_scores_list: List[ActionsWithScores]) -> List[
  Tuple[PyPlayerAction, float, float, float]]:
  """
  Same as average_ucb(), but tries to compute come CIs for the final score
  of each action.
  WARNING: This is likely not correct from a statistics point of view.
  """
  scores = defaultdict(list)
  scores_low = defaultdict(list)
  scores_upp = defaultdict(list)
  for actions_with_scores in actions_with_scores_list:
    for action, score in actions_with_scores.items():
      scores[action].append(score.score)
      if score.score_low is not None:
        scores_low[action].append(score.score_low)
      if score.score_upp is not None:
        scores_upp[action].append(score.score_upp)
  actions_and_scores = []
  for action, ucbs in scores.items():
    score_low = scores_low[action]
    score_upp = scores_upp[action]
    upp = None
    low = None
    # TODO(mcts_debug): Find a proper way to compute these CIs. Towards the end
    #  of the game, when we process *all* possible permutations, there should be
    #  no additional uncertainty on top of the uncertainty coming with each
    #  score from each permutation.
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

def _lower_ci_bound_on_raw_rewards_with_ci(
    actions_with_scores_list: List[ActionsWithScores]) -> List[
  Tuple[PyPlayerAction, float, float, float]]:
  is_fully_simulated = are_all_nodes_fully_simulated(actions_with_scores_list)
  if is_fully_simulated:
    return _average_ucb_with_ci(actions_with_scores_list)
  return lower_ci_bound_on_raw_rewards(actions_with_scores_list, debug=True)

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
      node.fully_simulated,
      ci_low,
      ci_upp,
    ))

  dataframe = DataFrame(data, columns=["action", "q", "n", "score", "exp_comp",
                                       "fully_simulated", "score_low",
                                       "score_upp"])
  _add_rank_column(dataframe)
  return dataframe

def run_mcts_and_collect_data(py_game_state: PyGameState,
                              options: MctsPlayerOptions,
                              iterations_step: int = 1,
                              game_points: Optional[PlayerPair[int]] = None):
  cdef Points[2] bummerl_score
  bummerl_score[0] = 0
  bummerl_score[1] = 0
  if game_points is not None and options.use_game_points:
    bummerl_score[0] = game_points.one
    bummerl_score[1] = game_points.two
  cdef GameState game_state = from_python_game_state(py_game_state)
  cdef Node *root_node = init_node(&game_state, NULL, bummerl_score)
  cdef int iteration = 1
  cdef bint is_fully_simulated = False
  cdef int max_iterations = options.max_iterations
  dataframes = []
  while True:
    for _ in range(iterations_step):
      is_fully_simulated = run_one_iteration(root_node,
                                             options.exploration_param,
                                             options.select_best_child,
                                             options.save_rewards,
                                             bummerl_score)
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
                                 iterations_step: int,
                                 game_points: Optional[PlayerPair[int]] = None):
  cdef Points[2] bummerl_score
  bummerl_score[0] = 0
  bummerl_score[1] = 0
  if game_points is not None and options.use_game_points:
    bummerl_score[0] = game_points.one
    bummerl_score[1] = game_points.two
  cdef int total_budget = options.max_iterations * options.max_permutations
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
    root_nodes.push_back(init_node(&game_state, NULL, bummerl_score))

  cdef int iteration = 1
  cdef bint is_fully_simulated, permutation_is_fully_simulated
  dataframes = []
  max_iterations = options.max_iterations
  if options.reallocate_computational_budget:
    max_iterations = int(total_budget / permutations.size())
  while True:
    is_fully_simulated = True
    for _ in range(iterations_step):
      is_fully_simulated = True
      for i in range(root_nodes.size()):
        permutation_is_fully_simulated = run_one_iteration(
          root_nodes[i], options.exploration_param, options.select_best_child,
          options.save_rewards, bummerl_score)
        is_fully_simulated = \
          is_fully_simulated and permutation_is_fully_simulated
      iteration += 1
      if is_fully_simulated:
        break

    actions_with_scoring_infos = []
    for j in range(root_nodes.size()):
      actions_with_scoring_infos.append(
        _build_scoring_info_with_debug(root_nodes[j]))
    if options.merge_scoring_info_func == average_ucb:
      actions_and_scores = _average_ucb_with_ci(actions_with_scoring_infos)
      dataframe = DataFrame(
        data=[(str(action), score, score_low, score_upp) for
              action, score, score_low, score_upp in actions_and_scores],
        columns=["action", "score", "score_low", "score_upp"])
    elif options.merge_scoring_info_func == lower_ci_bound_on_raw_rewards:
      actions_and_scores = _lower_ci_bound_on_raw_rewards_with_ci(
        actions_with_scoring_infos)
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

def run_is_mcts_player_step_by_step(
    py_game_view: PyGameState,
    options: MctsPlayerOptions,
    iterations_step: int,
    game_points: Optional[PlayerPair[int]] = None):
  cdef Points[2] bummerl_score
  bummerl_score[0] = 0
  bummerl_score[1] = 0
  if game_points is not None and options.use_game_points:
    bummerl_score[0] = game_points.one
    bummerl_score[1] = game_points.two
  cdef int total_budget = options.max_iterations * options.max_permutations
  cdef GameState game_view = from_python_game_state(py_game_view)

  cdef PlayerId opponent_id = from_python_player_id(
    py_game_view.next_player.opponent())
  cdef vector[vector[Card]] permutations
  from_python_permutations(generate_permutations(py_game_view, options),
                           &permutations)

  cdef int i, j

  cdef vector[GameState] game_states
  for i in range(permutations.size()):
    game_states.push_back(game_view)
    populate_game_view(&game_states[i], &permutations[i], opponent_id)

  cdef vector[ActionNode] action_nodes
  cdef PlayerAction[7] actions
  get_available_actions(&game_states[0], actions)
  cdef ActionNode action_node
  action_node.children.resize(game_states.size(), NULL)
  action_node.n = 0
  action_node.ucb = 0
  action_node.exploration_score = 0
  action_node.fully_simulated = False
  for i in range(MAX_CHILDREN):
    if actions[i].action_type == ActionType.NO_ACTION:
      break
    action_node.action = actions[i]
    action_nodes.push_back(action_node)

  cdef int game_state_index = 0
  cdef int iteration = 0
  cdef bint is_fully_simulated = False
  dataframes = []
  while True:
    for _ in range(iterations_step):
      game_state_index = (game_state_index + 1) % game_states.size()
      iteration += 1
      if run_one_is_iteration(&action_nodes, &game_states, game_state_index,
                              iteration, options.exploration_param,
                              options.save_rewards, bummerl_score):
        is_fully_simulated = True
        break

    tmp_data = []
    for i in range(action_nodes.size()):
      py_action = to_python_player_action(action_nodes[i].action)
      tmp_data.append((str(py_action), action_nodes[i].n,
                       action_nodes[i].ucb if action_nodes[
                                                i].player != opponent_id else -
                       action_nodes[i].ucb,
                       bool(action_nodes[i].fully_simulated)))

    dataframe = DataFrame(data=tmp_data,
                          columns=["action", "n", "score", "fully_simulated"])
    dataframe["iteration"] = iteration
    _add_rank_column(dataframe)
    dataframes.append(dataframe)

    if is_fully_simulated:
      break
    if options.max_iterations is not None and iteration >= total_budget:
      break

  for i in range(action_nodes.size()):
    for j in range(action_nodes[i].children.size()):
      if action_nodes[i].children[j] != NULL:
        delete_tree(action_nodes[i].children[j])
  return pandas.concat(dataframes, ignore_index=True)

cdef _accumulate_overlap(Node *root_node, py_game_state, level, data):
  if root_node.terminal:
    return
  heuristic_player = HeuristicPlayer(py_game_state.next_player)
  best_heuristic_action = heuristic_player.request_next_action(py_game_state)
  cdef int i = 0
  cdef int max_visits = -1
  cdef int heuristic_visits = -1
  cdef Node *node
  children_visits = []
  for i in range(MAX_CHILDREN):
    if root_node.actions[i].action_type == ActionType.NO_ACTION:
      break
    if root_node.children[i] == NULL:
      continue
    py_action = to_python_player_action(root_node.actions[i])
    node = root_node.children[i]
    max_visits = max(max_visits, node.n)
    if py_action == best_heuristic_action:
      heuristic_visits = node.n
    children_visits.append(node.n)
    new_py_game_state = py_action.execute(py_game_state)
    _accumulate_overlap(node, new_py_game_state, level + 1, data)
  heuristic_rank = len([x for x in children_visits if x < heuristic_visits])
  data.append((max_visits, heuristic_visits, heuristic_rank, level))

def overlap_between_mcts_and_heuristic(py_game_state: PyGameState,
                                       options: MctsPlayerOptions):
  cdef GameState game_state = from_python_game_state(py_game_state)
  cdef Node *root_node = build_tree(&game_state, options.max_iterations,
                                    options.exploration_param,
                                    options.select_best_child,
                                    options.save_rewards)
  data = []
  _accumulate_overlap(root_node, py_game_state, 0, data)
  delete_tree(root_node)
  columns = ["max_visits", "heuristic_visits", "heuristic_rank", "level"]
  return DataFrame(data, columns=columns, dtype=int)
