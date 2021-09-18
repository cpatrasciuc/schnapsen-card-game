#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# distutils: language=c++

import pandas
from pandas import DataFrame

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
from model.game_state import GameState as PyGameState

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
    data.append((
      str(py_action),
      (node.q if node.player == root_node.player else -node.q),
      node.n,
      (node.ucb if node.player == root_node.player else -node.ucb),
      node.exploration_score))

  dataframe = DataFrame(data, columns=["action", "q", "n", "score", "exp_comp"])
  dataframe["rank"] = dataframe["score"].sort_values().rank(method="min",
                                                            ascending=False)
  return dataframe

def run_mcts_and_collect_data(py_game_state: PyGameState,
                              options: MctsPlayerOptions):
  cdef GameState game_state = from_python_game_state(py_game_state)
  cdef Node *root_node = init_node(&game_state, NULL)
  iteration = 1
  dataframes = []
  max_iterations = options.max_iterations
  while True:
    is_fully_simulated = run_one_iteration(root_node,
                                           options.exploration_param,
                                           options.select_best_child)
    dataframe = _get_children_data(root_node)
    dataframe["iteration"] = iteration
    dataframes.append(dataframe)
    if is_fully_simulated:
      break
    if max_iterations is not None and iteration >= max_iterations:
      break
    iteration += 1
  delete_tree(root_node)
  return pandas.concat(dataframes, ignore_index=True)

def run_mcts_permutations_step_by_step(py_game_view: PyGameState,
                                       options: MctsPlayerOptions):
  cdef GameState game_view = from_python_game_state(py_game_view)
  cdef GameState game_state
  cdef vector[Node *] root_nodes
  cdef PlayerId opponent_id = from_python_player_id(
    py_game_view.next_player.opponent())

  cdef vector[vector[Card]] permutations
  from_python_permutations(generate_permutations(py_game_view, options),
                           &permutations)

  cdef int i
  for i in range(permutations.size()):
    game_state = game_view
    populate_game_view(&game_state, &permutations[i], opponent_id)
    root_nodes.push_back(init_node(&game_state, NULL))

  iteration = 1
  dataframes = []
  max_iterations = options.max_iterations
  while True:
    is_fully_simulated = True

    actions_with_scoring_infos = []
    for i in range(root_nodes.size()):
      is_fully_simulated = is_fully_simulated and run_one_iteration(
        root_nodes[i], options.exploration_param, options.select_best_child)
      actions_with_scoring_infos.append(build_scoring_info(root_nodes[i]))
    actions_and_scores = options.merge_scoring_info_func(
      actions_with_scoring_infos)

    dataframe = DataFrame(
      data=[(str(action), score) for action, score in actions_and_scores],
      columns=["action", "score"])
    dataframe["iteration"] = iteration
    dataframes.append(dataframe)

    if is_fully_simulated:
      break
    if max_iterations is not None and iteration >= max_iterations:
      break

    iteration += 1

  for i in range(root_nodes.size()):
    delete_tree(root_nodes[i])
  return pandas.concat(dataframes, ignore_index=True)
