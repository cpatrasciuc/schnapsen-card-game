#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# distutils: language=c++

import logging

from libc.math cimport log, sqrt
from libc.stdlib cimport free, malloc, rand
from libc.string cimport memset
from libcpp.vector cimport vector

from ai.cython_mcts_player.game_state cimport is_game_over, game_points
from ai.cython_mcts_player.player_action cimport ActionType, execute, \
  get_available_actions

cdef int MAX_CHILDREN = 7

cdef PlayerId _PLAYER_FOR_TERMINAL_NODES = 0

cdef Node *_selection(Node *root_node):
  cdef Node *node = root_node
  cdef vector[Node *] not_fully_simulated_children
  cdef int index
  cdef int i
  while not node.terminal:
    not_fully_simulated_children.clear()
    for i in range(MAX_CHILDREN):
      if node.actions[i].action_type == ActionType.NO_ACTION:
        break
      if node.children[i] == NULL:
        return node
      if not node.children[i].fully_simulated:
        not_fully_simulated_children.push_back(node.children[i])
    if not_fully_simulated_children.empty():
      return NULL
    # TODO(mcts): Maybe call srand() to initialize the RNG?
    index = rand() % not_fully_simulated_children.size()
    node = not_fully_simulated_children[index]

cdef Node *_init_node(GameState *game_state, Node *parent):
  cdef Node *node = <Node *> malloc(sizeof(Node))
  cdef float score_p1, score_p2
  memset(node, 0, sizeof(Node))
  node.game_state = game_state[0]
  node.parent = parent
  node.terminal = is_game_over(&node.game_state)
  node.fully_simulated = False
  node.q = 0
  node.n = 0
  node.ucb = 0
  node.player = node.game_state.next_player
  if node.terminal:
    score_p1, score_p2 = game_points(&node.game_state)
    score_p1 /= 3.0
    score_p2 /= 3.0
    node.ucb = score_p1 - score_p2
    node.fully_simulated = True
    node.player = _PLAYER_FOR_TERMINAL_NODES
  else:
    get_available_actions(&node.game_state, node.actions)
  return node

cdef Node *_expand(Node * node):
  cdef vector[int] untried_indices
  cdef int i
  for i in range(MAX_CHILDREN):
    if node.actions[i].action_type == ActionType.NO_ACTION:
      break
    if node.children[i] == NULL:
      untried_indices.push_back(i)
  cdef int index = rand() % untried_indices.size()
  index = untried_indices[index]
  cdef GameState game_state = execute(&node.game_state, node.actions[index])
  node.children[index] = _init_node(&game_state, node)
  return node.children[index]

cdef Node *_fully_expand(Node *start_node):
  cdef Node *node = start_node
  while not node.terminal:
    node = _expand(node)
  return node

cdef inline float _ucb_for_player(Node *node, PlayerId player_id):
  return node.ucb if node.player == player_id else -node.ucb

cdef void _update_ucb(Node *node, float exploration_param):
  cdef bint fully_simulated = True
  cdef float max_children_score = -100.0
  cdef float child_score = -100.0
  if node.terminal or node.fully_simulated:
    return
  for i in range(MAX_CHILDREN):
    if node.actions[i].action_type == ActionType.NO_ACTION:
      break
    if node.children[i] == NULL or not node.children[i].fully_simulated:
      fully_simulated = False
      break
    child_score = _ucb_for_player(node.children[i], node.player)
    if child_score > max_children_score:
      max_children_score = child_score
  if fully_simulated:
    node.ucb = max_children_score
    node.fully_simulated = True
  else:
    node.ucb = node.q / node.n + exploration_param * sqrt(
      2 * log(node.parent.n) / node.n)

cdef void _update_children_ucb(Node *node, float exploration_param):
  cdef int i
  for i in range(MAX_CHILDREN):
    if node.actions[i].action_type == ActionType.NO_ACTION:
      break
    if node.children[i] != NULL:
      _update_ucb(node.children[i], exploration_param)

cdef void _backpropagate(Node *end_node, float score, float exploration_param):
  cdef Node *node = end_node
  while node != NULL:
    if not node.terminal:
      node.n += 1
      node.q += score if node.player == _PLAYER_FOR_TERMINAL_NODES else -score
      _update_children_ucb(node, exploration_param)
    node = node.parent

cdef bint run_one_iteration(Node *root_node, float exploration_param):
  cdef Node *selected_node = _selection(root_node)
  if selected_node is NULL:
    return True
  cdef Node *end_node = _fully_expand(selected_node)
  _backpropagate(end_node, end_node.ucb, exploration_param)
  return False

cdef Node *build_tree(GameState *game_state, int max_iterations,
                      float exploration_param):
  cdef Node *root_node = _init_node(game_state, NULL)
  cdef int iterations = 0
  while True:
    iterations += 1
    if run_one_iteration(root_node, exploration_param):
      break
    if 0 < max_iterations <= iterations:
      break
  return root_node

cdef list best_actions_for_tests(Node *node):
  cdef float best_ucb = -100000
  cdef float ucb
  cdef bint has_expanded_children = False
  cdef int i
  for i in range(MAX_CHILDREN):
    if node.actions[i].action_type == ActionType.NO_ACTION:
      break
    if node.children[i] == NULL:
      continue
    has_expanded_children = True
    ucb = _ucb_for_player(node.children[i], node.player)
    if ucb > best_ucb:
      best_ucb = ucb
  cdef list actions = []
  if has_expanded_children:
    for i in range(MAX_CHILDREN):
      if node.actions[i].action_type == ActionType.NO_ACTION:
        break
      if node.children[i] == NULL:
        continue
      ucb = _ucb_for_player(node.children[i], node.player)
      if ucb == best_ucb:
        actions.append(node.actions[i])
  else:
    logging.error("MctsAlgorithm: All children are None")
    for i in range(MAX_CHILDREN):
      if node.actions[i].action_type == ActionType.NO_ACTION:
        break
      actions.append(node.actions[i])
  return actions

cdef debug_str(Node *node):
  return f"Q:{node.q}, N:{node.n}, UCB({node.player}):{node.ucb} " + \
         f"FullSim:{node.fully_simulated}"

cdef void delete_tree(Node *root_node):
  if root_node == NULL:
    return
  cdef int i
  for i in range(MAX_CHILDREN):
    if root_node.children[i] != NULL:
      delete_tree(root_node.children[i])
  free(root_node)
