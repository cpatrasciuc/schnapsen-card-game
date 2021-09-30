#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# distutils: language=c++

import logging

from libc.math cimport log, sqrt
from libc.stdlib cimport free, malloc, rand, srand
from libc.string cimport memset
from libc.time cimport time
from libcpp.vector cimport vector

from ai.cython_mcts_player.game_state cimport is_game_over, game_points, Points
from ai.cython_mcts_player.player_action cimport ActionType, execute, \
  get_available_actions

cdef int MAX_CHILDREN = 7

cdef PlayerId _PLAYER_FOR_TERMINAL_NODES = 0

cdef Node *_selection(Node *root_node, bint select_best_child) nogil:
  cdef Node *node = root_node
  cdef vector[Node *] not_fully_simulated_children
  cdef vector[Node *] best_children
  cdef int index
  cdef int i
  while not node.terminal:
    not_fully_simulated_children.clear()
    best_children.clear()
    for i in range(MAX_CHILDREN):
      if node.actions[i].action_type == ActionType.NO_ACTION:
        break
      if node.children[i] == NULL:
        return node
      if not node.children[i].fully_simulated:
        not_fully_simulated_children.push_back(node.children[i])
      if node.best_children[i]:
        best_children.push_back(node.children[i])
    if not_fully_simulated_children.empty():
      return NULL
    if select_best_child and best_children.size() > 0:
      index = rand() % best_children.size()
      best_child = best_children[index]
      node = best_child
      continue
    index = rand() % not_fully_simulated_children.size()
    node = not_fully_simulated_children[index]

cdef Node *init_node(GameState *game_state, Node *parent,
                     Points *bummerl_score) nogil:
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
    if bummerl_score != NULL and bummerl_score[0] + score_p1 >= 7:
      score_p1 = 7 - bummerl_score[0]
    if bummerl_score != NULL and bummerl_score[1] + score_p2 >= 7:
      score_p2 = 7 - bummerl_score[1]
    score_p1 /= 3.0
    score_p2 /= 3.0
    node.ucb = score_p1 - score_p2
    node.fully_simulated = True
    node.player = _PLAYER_FOR_TERMINAL_NODES
  else:
    get_available_actions(&node.game_state, node.actions)
  return node

cdef Node *_expand(Node * node, Points *bummerl_score) nogil:
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
  node.children[index] = init_node(&game_state, node, bummerl_score)
  return node.children[index]

cdef Node *_fully_expand(Node *start_node, Points *bummerl_score) nogil:
  cdef Node *node = start_node
  while not node.terminal:
    node = _expand(node, bummerl_score)
  return node

cdef inline float _ucb_for_player(Node *node, PlayerId player_id) nogil:
  return node.ucb if node.player == player_id else -node.ucb

cdef void _update_ucb(Node *node, float exploration_param) nogil:
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
    node.ucb = node.q / node.n
    node.exploration_score = exploration_param * sqrt(
      2 * log(node.parent.n) / node.n)

cdef void _update_children_ucb(Node *node, float exploration_param,
                               bint select_best_child) nogil:
  cdef int i
  cdef float max_selection_score = -1000000
  cdef float selection_score
  for i in range(MAX_CHILDREN):
    if node.actions[i].action_type == ActionType.NO_ACTION:
      break
    if node.children[i] != NULL:
      _update_ucb(node.children[i], exploration_param)
      if not node.children[i].fully_simulated:
        selection_score = _ucb_for_player(node.children[i], node.player)
        selection_score += node.children[i].exploration_score
        max_selection_score = max(max_selection_score, selection_score)
  if select_best_child:
    for i in range(MAX_CHILDREN):
      if node.actions[i].action_type == ActionType.NO_ACTION:
        break
      if node.children[i] != NULL:
        if node.children[i].fully_simulated:
          node.best_children[i] = False
          continue
        selection_score = _ucb_for_player(node.children[i], node.player)
        selection_score += node.children[i].exploration_score
        node.best_children[i] = (selection_score == max_selection_score)

cdef void _backpropagate(Node *end_node, float score,
                         float exploration_param, bint select_best_child,
                         bint save_rewards) nogil:
  cdef Node *node = end_node
  cdef float score_for_player
  while node != NULL:
    score_for_player = \
      score if node.player == _PLAYER_FOR_TERMINAL_NODES else -score
    if not node.terminal:
      node.n += 1
      node.q += score_for_player
      _update_children_ucb(node, exploration_param, select_best_child)

    if save_rewards:
      # Are we on the first layer in the tree?
      if node.parent != NULL and node.parent.parent == NULL:
        if node.rewards == NULL:
          node.rewards = new vector[float]()
        node.rewards.push_back(score_for_player)

    node = node.parent

cdef bint run_one_iteration(Node *root_node, float exploration_param,
                            bint select_best_child, bint save_rewards,
                            Points *bummerl_score) nogil:
  cdef Node *selected_node = _selection(root_node, select_best_child)
  if selected_node is NULL:
    return True
  cdef Node *end_node = _fully_expand(selected_node, bummerl_score)
  _backpropagate(end_node, end_node.ucb, exploration_param, select_best_child,
                 save_rewards)
  return False

cdef Node *build_tree(GameState *game_state, int max_iterations,
                      float exploration_param, bint select_best_child,
                      bint save_rewards=False,
                      Points *bummerl_score=NULL) nogil:
  cdef Node *root_node = init_node(game_state, NULL, bummerl_score)
  cdef int iterations = 0
  while True:
    iterations += 1
    if run_one_iteration(root_node, exploration_param, select_best_child,
                         save_rewards, bummerl_score):
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

cdef void delete_tree(Node *root_node) nogil:
  if root_node == NULL:
    return
  cdef int i
  for i in range(MAX_CHILDREN):
    if root_node.children[i] != NULL:
      delete_tree(root_node.children[i])
  if root_node.rewards != NULL:
    del root_node.rewards
  free(root_node)

# Initialize the RNG.
srand(time(NULL))
