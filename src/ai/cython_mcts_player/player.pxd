#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# distutils: language=c++

from libcpp.vector cimport vector

from ai.cython_mcts_player.card cimport Card
from ai.cython_mcts_player.game_state cimport GameState, PlayerId
from ai.cython_mcts_player.mcts cimport Node

cdef void from_python_permutations(py_permutations,
                                   vector[vector[Card]] *permutations)

cdef void populate_game_view(GameState *game_view, vector[Card] *permutation,
                             PlayerId opponent_id) nogil

cdef build_scoring_info(Node *root_node)
