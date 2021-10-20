#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# distutils: language=c++

# cython: warn.unused=False

from typing import List, Optional

from libcpp.vector cimport vector

from ai.cython_mcts_player.card cimport Card, is_unknown
from ai.cython_mcts_player.game_state cimport GameState, PlayerId, \
  from_python_player_id, from_python_game_state, Points
from ai.cython_mcts_player.mcts cimport Node, build_tree, MAX_CHILDREN, \
  delete_tree, build_is_tree, ActionNode
from ai.cython_mcts_player.player_action cimport ActionType, \
  to_python_player_action
from ai.mcts_player import BaseMctsPlayer
from ai.mcts_player_options import MctsPlayerOptions

from ai.merge_scoring_infos_func import ActionsWithScores, ScoringInfo
from model.card import Card as PyCard
from model.game_state import GameState as PyGameState
from model.player_id import PlayerId as PyPlayerId

cdef void from_python_permutations(py_permutations,
                                   vector[vector[Card]] *permutations):
  cdef vector[Card] permutation
  for py_permutation in py_permutations:
    permutation.clear()
    for card in py_permutation:
      permutation.push_back(Card(suit=card.suit, card_value=card.card_value))
    permutations.push_back(permutation)

cdef void populate_game_view(GameState *game_view, vector[Card] *permutation,
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

cdef build_scoring_info(Node *root_node):
  actions_with_scores = {}
  cdef int i
  cdef Node *node
  for i in range(MAX_CHILDREN):
    if root_node.actions[i].action_type == ActionType.NO_ACTION:
      break
    if root_node.children[i] == NULL:
      continue
    py_action = to_python_player_action(root_node.actions[i])
    node = root_node.children[i]
    scoring_info = ScoringInfo(
      q=(node.q if node.player == root_node.player else -node.q),
      n=node.n,
      score=(node.ucb if node.player == root_node.player else -node.ucb),
      fully_simulated=bool(node.fully_simulated), terminal=bool(node.terminal))
    if node.rewards != NULL:
      scoring_info.rewards = list(node.rewards[0])
      if node.player != root_node.player:
        scoring_info.rewards = [-reward for reward in scoring_info.rewards]
    actions_with_scores[py_action] = scoring_info
  return actions_with_scores

cdef list _run_mcts_single_threaded(GameState *game_view,
                                    vector[vector[Card]] *permutations,
                                    PlayerId opponent_id,
                                    Points * bummerl_score,
                                    int max_iterations,
                                    bint select_best_child,
                                    float exploration_param,
                                    bint save_rewards):
  cdef int i
  cdef GameState game_state
  cdef Node *root_node
  cdef list py_root_nodes = []
  for i in range(permutations.size()):
    game_state = game_view[0]
    populate_game_view(&game_state, &permutations[0][i], opponent_id)
    root_node = build_tree(&game_state, max_iterations, exploration_param,
                           select_best_child, save_rewards, bummerl_score)
    py_root_nodes.append(build_scoring_info(root_node))
    delete_tree(root_node)
  return py_root_nodes


class CythonMctsPlayer(BaseMctsPlayer):
  """Cython-based implementation of BaseMctsPlayer."""

  def __init__(self, player_id: PyPlayerId, cheater: bool = False,
               options: Optional[MctsPlayerOptions] = None):
    super().__init__(player_id, cheater, options)
    if options.num_processes != 1:
      raise ValueError(
        f"CythonMctsPlayer: Options specify {options.num_processes} threads, "
        "but multi-threading is not supported. Running in single-threaded mode")

  def run_mcts_algorithm(self, py_game_view: PyGameState,
                         py_permutations: List[List[PyCard]],
                         game_points = None) -> List[ActionsWithScores]:
    cdef GameState game_view = from_python_game_state(py_game_view)
    cdef vector[vector[Card]] permutations
    cdef int max_iterations = self._options.max_iterations or -1
    cdef int total_budget
    from_python_permutations(py_permutations, &permutations)
    options = self._options
    if options.reallocate_computational_budget and \
        max_iterations > 0 and \
        permutations.size() < options.max_permutations:
      total_budget = options.max_permutations * options.max_iterations
      max_iterations = <int> (total_budget / permutations.size())
    cdef Points[2] bummerl_score
    bummerl_score[0] = 0
    bummerl_score[1] = 0
    if options.use_game_points and game_points is not None:
      bummerl_score[0] = game_points.one
      bummerl_score[1] = game_points.two
    return _run_mcts_single_threaded(
      &game_view, &permutations, from_python_player_id(self.id.opponent()),
      bummerl_score, max_iterations, options.select_best_child,
      options.exploration_param, options.save_rewards)


cdef list _run_is_mcts_single_threaded(GameState *game_view,
                                       vector[vector[Card]] *permutations,
                                       PlayerId opponent_id,
                                       Points *bummerl_score,
                                       int max_iterations,
                                       float exploration_param,
                                       bint save_rewards):
  cdef int i
  cdef vector[GameState] game_states
  for i in range(permutations.size()):
    game_states.push_back(game_view[0])
    populate_game_view(&game_states[i], &permutations[0][i], opponent_id)
  cdef vector[ActionNode] action_nodes = build_is_tree(&game_states,
                                                       max_iterations,
                                                       exploration_param,
                                                       save_rewards,
                                                       bummerl_score)
  cdef int j
  action_with_scores = {}
  for i in range(action_nodes.size()):
    py_action = to_python_player_action(action_nodes[i].action)
    scoring_info = ScoringInfo(
      q=action_nodes[i].ucb,
      n=action_nodes[i].n,
      score=(action_nodes[i].ucb if action_nodes[i].player != opponent_id else -
      action_nodes[i].ucb),
      fully_simulated=bool(action_nodes[i].fully_simulated),
      terminal=None)
    action_with_scores[py_action] = scoring_info
    for j in range(action_nodes[i].children.size()):
      if action_nodes[i].children[j] != NULL:
        delete_tree(action_nodes[i].children[j])
  return [action_with_scores]


class CythonIsMctsPlayer(CythonMctsPlayer):
  """
  Cython-based implementation of BaseMctsPlayer that uses Information Set Mcts.
  """

  def run_mcts_algorithm(self, py_game_view: PyGameState,
                         py_permutations: List[List[PyCard]],
                         game_points = None) -> List[ActionsWithScores]:
    cdef GameState game_view = from_python_game_state(py_game_view)
    cdef vector[vector[Card]] permutations
    cdef int max_iterations = self._options.max_iterations or -1
    cdef int total_budget
    from_python_permutations(py_permutations, &permutations)
    if max_iterations > 0:
      max_iterations *= self._options.max_permutations
    cdef Points[2] bummerl_score
    bummerl_score[0] = 0
    bummerl_score[1] = 0
    if self._options.use_game_points and game_points is not None:
      bummerl_score[0] = game_points.one
      bummerl_score[1] = game_points.two
    return _run_is_mcts_single_threaded(
      &game_view, &permutations, from_python_player_id(self.id.opponent()),
      bummerl_score, max_iterations, self._options.exploration_param,
      self._options.save_rewards)
