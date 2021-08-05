#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import copy
import logging
import math
import pprint
import random
import time
from typing import Dict, List, Optional

from model.game_state import GameState
from model.player_action import get_available_actions, PlayerAction
from model.player_id import PlayerId

_PLAYER_FOR_TERMINAL_NODES = PlayerId.ONE


def _ucb_for_player(node: "Node", player_id: PlayerId):
  return node.ucb if node.player == player_id else -node.ucb


class Node:
  def __init__(self, game_state: GameState, parent: Optional["Node"]):
    self._game_state = game_state
    self.parent = parent
    self.children: Optional[Dict[PlayerAction, "Node"]] = None
    self.untried_actions: Optional[List[PlayerAction]] = None
    self.q = 0
    self.n = 0
    self.ucb = None
    self.fully_simulated = False
    if not self._game_state.is_game_over:
      actions = get_available_actions(self._game_state)
      self.children = {action: None for action in actions}
      self.untried_actions = actions
    else:
      score = self._game_state.game_points
      opponent = _PLAYER_FOR_TERMINAL_NODES.opponent()
      self.ucb = (score[_PLAYER_FOR_TERMINAL_NODES] - score[opponent]) / 3
      self.fully_simulated = True

  @property
  def fully_expanded(self) -> bool:
    return self.terminal or len(self.untried_actions) == 0

  @property
  def terminal(self) -> bool:
    return self._game_state.is_game_over

  @property
  def player(self) -> PlayerId:
    if self.terminal:
      return _PLAYER_FOR_TERMINAL_NODES
    return self._game_state.next_player

  def add_children(self, action: PlayerAction) -> "Node":
    assert action in self.children, ("Invalid action", action)
    assert action in self.untried_actions, ("Already expanded action", action)
    game_state = copy.deepcopy(self._game_state)
    action.execute(game_state)
    child = Node(game_state, self)
    self.children[action] = child
    self.untried_actions.remove(action)
    return child

  def update_children_ucb(self, exploration_param):
    if self.children is None:
      return
    for node in self.children.values():
      if node is not None:
        node.update_ucb(exploration_param)

  def update_ucb(self, exploration_param: float):
    if self.terminal or self.fully_simulated:
      return
    num_not_fully_simulated_children = len(
      [child for child in self.children.values() if
       child is None or not child.fully_simulated])
    if num_not_fully_simulated_children > 0:
      self.ucb = self.q / self.n + exploration_param * math.sqrt(
        2 * math.log(self.parent.n) / self.n)
    else:
      children_scores = [_ucb_for_player(child, self.player) for child in
                         self.children.values() if child is not None]
      self.ucb = max(children_scores)
      self.fully_simulated = True

  def best_child(self) -> "Node":
    children_with_ucb = [(_ucb_for_player(node, self.player), node) for node in
                         self.children.values() if node is not None]
    children_with_ucb.sort(key=lambda x: x[0], reverse=True)
    best_ucb = children_with_ucb[0][0]
    best_children = [x for x in children_with_ucb if x[0] == best_ucb]
    return random.choice(best_children)[1]

  def best_action(self) -> PlayerAction:
    best_child = self.best_child()
    for action, child in self.children.items():
      if child is best_child:
        return action
    raise Exception("Should not reach this code")

  def __repr__(self):
    return f"Q:{self.q}, N:{self.n}, UCB:{self.ucb}"


def debug_print(node: Node, indent: int = 1):
  if node is None:
    print("None")
    return
  print(f"{node.player.name}: {node}")
  if node.children is None:
    return
  for action, child in node.children.items():
    print("\t" * indent, end="")
    print(f"{action}", end="")
    debug_print(child, indent + 1)


class MCTS:
  def __init__(self, player_id: PlayerId, exploration_param=math.sqrt(2)):
    self._player_id = player_id
    self._start_time = None
    self._time_limit_sec = None
    self._exploration_param = exploration_param
    # TODO(mcts): Cache the tree(s) from previous calls.

  def search(self, game_state: GameState,
             time_limit_sec: Optional[float] = None) -> PlayerAction:
    root_node = self.build_tree(game_state, time_limit_sec)
    logging.info("MCTS: %s", pprint.pformat(root_node.children))
    if len(game_state.cards_in_hand.one) < 5:
      debug_print(root_node)
    return root_node.best_action()

  def build_tree(self, game_state: GameState,
                 time_limit_sec: Optional[float] = None) -> Node:
    root_node = Node(copy.deepcopy(game_state), None)
    self._time_limit_sec = time_limit_sec
    self._start_time = time.process_time()
    while not self._is_computation_budget_depleted():
      if self._run_one_iteration(root_node):
        break
    return root_node

  def _run_one_iteration(self, root_node: Node) -> bool:
    """Returns True if the entire game tree is already constructed."""
    selected_node = self._selection(root_node)
    if selected_node is None:
      return True
    end_node = self._fully_expand(selected_node)
    self._backpropagate(end_node, end_node.ucb)
    return False

  def _is_computation_budget_depleted(self):
    if self._time_limit_sec is None:
      return False
    current_time = time.process_time()
    return current_time - self._start_time > self._time_limit_sec

  def _selection(self, node: Node) -> Optional[Node]:
    while not node.terminal:
      if not node.fully_expanded:
        return node
      # TODO(mcts): Check if the UCB formula is still valid if we don't pick the
      #  node randomly.
      not_fully_simulated_children = [child for child in
                                      node.children.values() if
                                      not child.fully_simulated]
      if len(not_fully_simulated_children) == 0:
        # This can only happen once we expanded the whole game tree.
        return None
      best_child = node.best_child()
      if best_child in not_fully_simulated_children:
        node = best_child
      else:
        node = random.choice(not_fully_simulated_children)
    return node

  def _expand(self, node: Node):
    # TODO(mcts): Start with the action that the HeuristicPlayer would play.
    action = random.choice(node.untried_actions)
    return node.add_children(action)

  def _fully_expand(self, node: Node) -> Node:
    while not node.terminal:
      assert not node.fully_expanded
      node = self._expand(node)
    return node

  def _backpropagate(self, node: Node, score: float):
    while node is not None:
      if not node.terminal:
        node.n += 1
        # TODO(stats): Store all rewards in debug mode and check histogram.
        node.q += score if node.player == _PLAYER_FOR_TERMINAL_NODES else -score
        node.update_children_ucb(self._exploration_param)
      node = node.parent
