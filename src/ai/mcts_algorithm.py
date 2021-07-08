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
from model.player_pair import PlayerPair


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
    self._final_score = False
    self.reward: Optional[PlayerPair[float]] = None
    if not self._game_state.is_game_over:
      actions = get_available_actions(self._game_state)
      self.children = {action: None for action in actions}
      self.untried_actions = actions
    else:
      score = self._game_state.game_points
      score.one /= 3
      score.two /= 3
      self.reward = score

  @property
  def fully_expanded(self) -> bool:
    return self.terminal or len(self.untried_actions) == 0

  @property
  def terminal(self) -> bool:
    return self._game_state.is_game_over

  @property
  def player(self) -> PlayerId:
    return self._game_state.next_player

  def add_children(self, action: PlayerAction) -> "Node":
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
    if self.terminal or self._final_score:
      return
    num_not_fully_expanded_children = len(
      [child for child in self.children.values() if
       child is None or not child.fully_expanded])
    if num_not_fully_expanded_children > 0:
      self.ucb = self.q / self.n + exploration_param * math.sqrt(
        2 * math.log(self.parent.n) / self.n)
    else:
      children_scores = [_ucb_for_player(child, self.player) for child in
                         self.children.values() if child is not None]
      self.ucb = max(children_scores)
      self._final_score = True

  def best_child(self) -> "Node":
    children_with_ucb = [(_ucb_for_player(node, self.player), node) for node in
                         self.children.values() if node is not None]
    children_with_ucb.sort(key=lambda x: x[0], reverse=True)
    best_ucb = children_with_ucb[0][0]
    best_children = [x for x in children_with_ucb if x[0] == best_ucb]
    return random.choice(best_children)[1]

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

  def search(self, game_state: GameState, time_limit_sec: float):
    root_node = Node(copy.deepcopy(game_state), None)
    self._time_limit_sec = time_limit_sec
    self._start_time = time.process_time()
    while not self._is_computation_budget_depleted():
      selected_node = self._selection(root_node)
      end_node = self._fully_expand(selected_node)
      self._evaluate(end_node)
      self._backpropagate(end_node, end_node.reward)
    logging.info("MCTS: %s", pprint.pformat(root_node.children))
    if len(game_state.cards_in_hand.one) < 5:
      debug_print(root_node)
    best_child = root_node.best_child()
    for action, child in root_node.children.items():
      if child is best_child:
        return action
    raise Exception("Should not reach this code")

  def _is_computation_budget_depleted(self):
    current_time = time.process_time()
    return current_time - self._start_time > self._time_limit_sec

  def _selection(self, node: Node) -> Node:
    while not node.terminal:
      if not node.fully_expanded:
        return self._expand(node)
      else:
        # TODO(mcts): No need to do these simulations. Can do something smarter.
        node = random.choice(list(node.children.values()))  # node.best_child()
    return node

  def _expand(self, node: Node):
    # TODO(mcts): Start with the action that the HeuristicPlayer would play.
    action = random.choice(node.untried_actions)
    return node.add_children(action)

  def _fully_expand(self, node: Node) -> Node:
    while not node.terminal:
      if not node.fully_expanded:
        node = self._expand(node)
      else:
        logging.error("MCTS: Should not reach this")
        node = random.choice(list(node.children.values()))
    return node

  def _backpropagate(self, node: Node, reward: PlayerPair[float]):
    while node is not None:
      node.n += 1

      node.q += reward[node.player] - reward[node.player.opponent()]
      node.update_children_ucb(self._exploration_param)
      node = node.parent

  def _evaluate(self, node):
    score = node._game_state.game_points
    opponent = self._player_id.opponent()
    node.ucb = (score[self._player_id] - score[opponent]) / 3.0
    node._final_score = True
