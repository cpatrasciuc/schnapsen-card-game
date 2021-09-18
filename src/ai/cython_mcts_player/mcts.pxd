#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# distutils: language=c++

from ai.cython_mcts_player.game_state cimport GameState, PlayerId
from ai.cython_mcts_player.player_action cimport PlayerAction

ctypedef Node *PNode

cdef int MAX_CHILDREN

cdef struct Node:
  GameState game_state
  Node *parent
  PlayerAction[7] actions
  PNode[7] children
  # TODO(optimization): Could be converted to a bitmask if needed.
  bint[7] best_children  # Only set for not fully simulated children.
  float q
  int n
  float ucb
  float exploration_score
  bint fully_simulated
  bint terminal
  PlayerId player

cdef Node *init_node(GameState *game_state, Node *parent) nogil
cdef bint run_one_iteration(Node *root_node, float exploration_param,
                            bint select_best_child) nogil
cdef Node *build_tree(GameState *game_state, int max_iterations,
                      float exploration_param, bint select_best_child) nogil
cdef void delete_tree(Node *root_node) nogil

cdef list best_actions_for_tests(Node *node)
cdef debug_str(Node *node)
