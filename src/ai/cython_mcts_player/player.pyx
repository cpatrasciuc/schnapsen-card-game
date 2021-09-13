#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# distutils: language=c++

from typing import List

from libcpp.vector cimport vector

from ai.cython_mcts_player.card cimport Card, is_unknown
from ai.cython_mcts_player.game_state cimport GameState, PlayerId, \
  from_python_player_id, from_python_game_state
from ai.cython_mcts_player.mcts cimport Node, build_tree, MAX_CHILDREN, \
  delete_tree
from ai.cython_mcts_player.player_action cimport ActionType, \
  to_python_player_action
from ai.mcts_player import BaseMctsPlayer

from ai.merge_scoring_infos_func import ActionsWithScores, ScoringInfo
from model.card import Card as PyCard
from model.game_state import GameState as PyGameState

cdef void _populate_game_view(GameState *game_view, vector[Card] *permutation,
                              PlayerId opponent_id):
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

cdef list process_permutations_in_parallel(GameState *game_view,
                                           vector[vector[Card]] *permutations,
                                           PlayerId opponent_id,
                                           int max_iterations):
  cdef int i
  cdef GameState game_state
  cdef Node *root_node
  cdef list py_root_nodes = []
  # TODO(cython): Convert this to a parallel-for-loop.
  for i in range(permutations.size()):
    game_state = game_view[0]
    _populate_game_view(&game_state, &permutations[0][i], opponent_id)
    root_node = build_tree(&game_state, max_iterations, exploration_param=0)
    py_root_nodes.append(_build_scoring_info(root_node))
    delete_tree(root_node)
  return py_root_nodes


class CythonMctsPlayer(BaseMctsPlayer):
  """Cython-based implementation of BaseMctsPlayer."""

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
    return process_permutations_in_parallel(
      &game_view, &permutations, from_python_player_id(self.id.opponent()),
      self._options.max_iterations or -1)
