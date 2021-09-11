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
  float q
  int n
  float ucb
  bint fully_simulated
  bint terminal
  PlayerId player

cdef Node *build_tree(GameState *game_state, int max_iterations,
                      float exploration_param)
cdef debug_str(Node *node)
