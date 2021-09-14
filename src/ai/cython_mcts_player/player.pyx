#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# distutils: language=c++

# cython: warn.unused=False

import logging
import math

cimport openmp

from typing import List, Optional

from cython.parallel import prange
from libc.stdlib cimport free, malloc
from libcpp.vector cimport vector

from ai.cython_mcts_player.card cimport Card, is_unknown
from ai.cython_mcts_player.game_state cimport GameState, PlayerId, \
  from_python_player_id, from_python_game_state
from ai.cython_mcts_player.mcts cimport Node, build_tree, MAX_CHILDREN, \
  delete_tree
from ai.cython_mcts_player.player_action cimport ActionType, \
  to_python_player_action
from ai.mcts_player import BaseMctsPlayer
from ai.mcts_player_options import MctsPlayerOptions

from ai.merge_scoring_infos_func import ActionsWithScores, ScoringInfo
from model.card import Card as PyCard
from model.game_state import GameState as PyGameState
from model.player_id import PlayerId as PyPlayerId

cdef void _populate_game_view(GameState *game_view, vector[Card] *permutation,
                              PlayerId opponent_id) nogil:
  cdef int i
  cdef int perm_index = 0
  for i in range(5):
    if is_unknown(game_view.cards_in_hand[opponent_id][i]):
      game_view.cards_in_hand[opponent_id][i] = permutation[0][perm_index]
      perm_index += 1
  for i in range(9):
    if is_unknown(game_view.talon[i]):
      game_view.talon[i] = permutation[0][perm_index]
      perm_index += 1

cdef _build_scoring_info(Node *root_node):
  actions_with_scores = {}
  cdef int i
  cdef Node *node
  for i in range(MAX_CHILDREN):
    if root_node.actions[i].action_type == ActionType.NO_ACTION:
      break
    py_action = to_python_player_action(root_node.actions[i])
    node = root_node.children[i]
    scoring_info = ScoringInfo(
      q=(node.q if node.player == root_node.player else -node.q),
      n=node.n,
      score=(node.ucb if node.player == root_node.player else -node.ucb),
      fully_simulated=bool(node.fully_simulated), terminal=bool(node.terminal))
    actions_with_scores[py_action] = scoring_info
  return actions_with_scores

cdef list _run_mcts_multi_threaded(GameState *game_view,
                                   vector[vector[Card]] *permutations,
                                   PlayerId opponent_id,
                                   int max_iterations,
                                   int num_threads):
  cdef Py_ssize_t i
  cdef Py_ssize_t n = permutations.size()
  cdef GameState game_state
  cdef Node ** root_nodes = <Node **> malloc(n * sizeof(Node *))
  cdef int chunksize = math.floor(n / num_threads)
  if num_threads > 1:
    openmp.omp_set_num_threads(num_threads)
  for i in prange(n, nogil=True, schedule="static", chunksize=chunksize):
    game_state = game_view[0]
    _populate_game_view(&game_state, &permutations[0][i], opponent_id)
    root_nodes[i] = build_tree(&game_state, max_iterations,
                               exploration_param=0)
  cdef list py_root_nodes = []
  for i in range(n):
    py_root_nodes.append(_build_scoring_info(root_nodes[i]))
  for i in prange(n, nogil=True, schedule="static", chunksize=chunksize):
    delete_tree(root_nodes[i])
  free(root_nodes)
  return py_root_nodes

cdef list _run_mcts_single_threaded(GameState *game_view,
                                    vector[vector[Card]] *permutations,
                                    PlayerId opponent_id,
                                    int max_iterations):
  cdef int i
  cdef GameState game_state
  cdef Node *root_node
  cdef list py_root_nodes = []
  for i in range(permutations.size()):
    game_state = game_view[0]
    _populate_game_view(&game_state, &permutations[0][i], opponent_id)
    root_node = build_tree(&game_state, max_iterations, exploration_param=0)
    py_root_nodes.append(_build_scoring_info(root_node))
    delete_tree(root_node)
  return py_root_nodes


class CythonMctsPlayer(BaseMctsPlayer):
  """Cython-based implementation of BaseMctsPlayer."""

  def __init__(self, player_id: PyPlayerId, cheater: bool = False,
               options: Optional[MctsPlayerOptions] = None):
    super().__init__(player_id, cheater, options)
    if options.num_processes != 1:
      logging.warning(
        f"CythonMctsPlayer: Using {options.num_processes} threads")
    else:
      logging.info("CythonMctsPlayer: Running in single-threaded mode")

  def run_mcts_algorithm(self, py_game_view: PyGameState,
                         py_permutations: List[List[PyCard]]) -> List[
    ActionsWithScores]:
    cdef vector[vector[Card]] permutations
    cdef vector[Card] permutation
    for py_permutation in py_permutations:
      permutation.clear()
      for card in py_permutation:
        permutation.push_back(Card(suit=card.suit, card_value=card.card_value))
      permutations.push_back(permutation)
    cdef GameState game_view = from_python_game_state(py_game_view)
    if self._options.num_processes == 1:
      return _run_mcts_single_threaded(
        &game_view, &permutations, from_python_player_id(self.id.opponent()),
        self._options.max_iterations or -1)
    return _run_mcts_multi_threaded(&game_view, &permutations,
                                    from_python_player_id(self.id.opponent()),
                                    self._options.max_iterations or -1,
                                    self._options.num_processes)
