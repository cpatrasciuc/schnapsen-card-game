#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import abc
import copy
import logging
import math
import pprint
import random
from typing import Dict, List, Optional, Generic, TypeVar, Type, Tuple

from ai.heuristic_player import HeuristicPlayer
from model.game_state import GameState
from model.player_action import get_available_actions, PlayerAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair

_PLAYER_FOR_TERMINAL_NODES = PlayerId.ONE


def ucb_for_player(node: "Node", player_id: PlayerId):
  return node.ucb if node.player == player_id else -node.ucb


_State = TypeVar("_State")
_Action = TypeVar("_Action")


class Node(abc.ABC, Generic[_State, _Action]):
  """Generic class representing a node in an MCTS tree."""

  # pylint: disable=too-many-instance-attributes

  def __init__(self, state: _State, parent: Optional["Node"]):
    """Instantiates a new Node given a State object and a parent node."""
    self.state = state
    self.parent = parent
    self.children: Optional[Dict[_Action, "Node"]] = None
    self.untried_actions: Optional[List[_Action]] = None
    self.q = 0
    self.n = 0
    self.ucb = None
    self.fully_simulated = False
    if not self.terminal:
      actions = self._get_available_actions()
      self.children = {action: None for action in actions}
      self.untried_actions = actions
    else:
      score = self._get_reward_for_terminal_node()
      opponent = _PLAYER_FOR_TERMINAL_NODES.opponent()
      self.ucb = score[_PLAYER_FOR_TERMINAL_NODES] - score[opponent]
      self.fully_simulated = True

  @property
  @abc.abstractmethod
  def terminal(self) -> bool:
    """Returns True if this node represents a terminal game state."""

  @abc.abstractmethod
  def _get_available_actions(self) -> List[_Action]:
    """
    This method must return the actions available to the current player in the
    game state represented by this node. It is only called for non-terminal
    nodes.
    """

  @abc.abstractmethod
  def _get_reward_for_terminal_node(self) -> PlayerPair[float]:
    """
    This method must return the score for each player. It is only called for
    terminal nodes.
    """

  @abc.abstractmethod
  def _player(self) -> PlayerId:
    """
    Returns the ID of the player that has to make a move in the game state
    represented by this node.
    """

  @property
  def player(self) -> PlayerId:
    if self.terminal:
      return _PLAYER_FOR_TERMINAL_NODES
    return self._player()

  @property
  def fully_expanded(self) -> bool:
    """Return True if all the children of this node were created."""
    return self.terminal or len(self.untried_actions) == 0

  def expand(self) -> "Node":
    """
    Expands the current node by adding a new child for one of the actions that
    were not already explored. It cannot be called for fully expanded nodes.
    It returns the newly created node.
    """
    assert not self.fully_expanded
    if len(self.untried_actions) == len(self.children):
      heuristic_player = HeuristicPlayer(self.player)
      action = heuristic_player.request_next_action(self.state)
    else:
      action = random.choice(self.untried_actions)
    new_state = self._get_next_state(action)
    child = self.__class__(new_state, self)
    self.children[action] = child
    self.untried_actions.remove(action)
    return child

  @abc.abstractmethod
  def _get_next_state(self, action: _Action) -> _State:
    """
    This method should return the state obtained by playing the given action in
    the game state represented by this node.
    """

  def update_children_ucb(self, exploration_param: float):
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
      children_scores = [ucb_for_player(child, self.player) for child in
                         self.children.values() if child is not None]
      self.ucb = max(children_scores)
      self.fully_simulated = True

  def best_children(self) -> List[Tuple["Node", _Action]]:
    children_with_ucbs = \
      [(ucb_for_player(child, self.player), child, action)
       for action, child in self.children.items() if child is not None]
    if len(children_with_ucbs) == 0:
      # TODO(mcts): Find out why this happens.
      logging.error("MCTSAlgorithm: All children are None: %s",
                    pprint.pformat(self.children, indent=True))
      return [(child, action) for action, child in self.children.items()]
    best_ucb = max([ucb for ucb, child, action in children_with_ucbs])
    return [(child, action) for ucb, child, action in children_with_ucbs if
            ucb == best_ucb]

  def best_actions(self) -> List[_Action]:
    return [action for child, action in self.best_children()]

  def __repr__(self):
    return f"Q:{self.q}, N:{self.n}, UCB({self.player}):{self.ucb} " + \
           f"FullSim:{self.fully_simulated}"


class SchnapsenNode(Node[GameState, PlayerAction]):
  """Implementation of the Node class for the game of Schnapsen."""

  @property
  def terminal(self) -> bool:
    return self.state.is_game_over

  def _get_available_actions(self) -> List[PlayerAction]:
    assert not self.terminal
    return get_available_actions(self.state)

  def _get_reward_for_terminal_node(self) -> PlayerPair[float]:
    assert self.terminal
    score = self.state.game_points
    score.one /= 3
    score.two /= 3
    return score

  def _player(self) -> PlayerId:
    return self.state.next_player

  def _get_next_state(self, action: PlayerAction) -> GameState:
    return action.execute(self.state)


def debug_print(node: Node, indent: int = 1):
  if node is None:
    print("None")
    return
  print(f"{node.player.name}: {node}", end="")
  if node.children is None:
    print(f" [score: {node.state.trick_points} {node.state.game_points}]")
    return
  print()
  for action, child in node.children.items():
    print("\t" * indent, end="")
    print(f"{action}", end="")
    debug_print(child, indent + 1)


class MCTS(Generic[_State, _Action]):
  def __init__(self, player_id: PlayerId,
               node_class: Type[Node[_State, _Action]] = SchnapsenNode,
               exploration_param: float = 0.5):
    self._player_id = player_id
    self._node_class = node_class
    self._max_iterations = None
    self._exploration_param = exploration_param
    # TODO(mcts): Cache the tree(s) from previous calls.

  def build_tree(self, state: _State,
                 max_iterations: Optional[int] = None) -> Node[
    _State, _Action]:
    assert max_iterations is None or max_iterations > 0, \
      "max_iterations must be positive"
    if isinstance(state, GameState):
      state_copy = state.deep_copy()
    else:
      state_copy = copy.deepcopy(state)
    root_node = self._node_class(state_copy, None)
    iterations = 0
    while True:
      iterations += 1
      if self.run_one_iteration(root_node):
        break
      if max_iterations is not None and iterations >= max_iterations:
        break
    logging.info("MctsAlgorithm: Run %s iterations", iterations)
    # if len(state.cards_in_hand.one) <= 2:
    #   debug_print(root_node, 0)
    return root_node

  def run_one_iteration(self, root_node: Node) -> bool:
    """Returns True if the entire game tree is already constructed."""
    selected_node = MCTS._selection(root_node)
    if selected_node is None:
      return True
    end_node = MCTS._fully_expand(selected_node)
    self._backpropagate(end_node, end_node.ucb)
    return False

  @staticmethod
  def _selection(node: Node) -> Optional[Node]:
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
      # TODO(mcts): Check if it's better to select the best_child instead of a
      #  random child.
      for best_child in node.best_children():
        if best_child in not_fully_simulated_children:
          node = best_child
          break
      else:
        node = random.choice(not_fully_simulated_children)
    raise Exception("Should not reach this code")  # pragma: no cover

  @staticmethod
  def _fully_expand(node: Node) -> Node:
    while not node.terminal:
      assert not node.fully_expanded
      node = node.expand()
    return node

  def _backpropagate(self, node: Node, score: float):
    while node is not None:
      if not node.terminal:
        node.n += 1
        # TODO(stats): Store all rewards in debug mode and check histogram.
        node.q += score if node.player == _PLAYER_FOR_TERMINAL_NODES else -score
        node.update_children_ucb(self._exploration_param)
      node = node.parent
