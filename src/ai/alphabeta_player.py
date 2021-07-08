#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.
import copy
import enum
import logging
import pprint
from typing import Dict

from ai.player import Player
from model.game_state import GameState
from model.player_action import get_available_actions, PlayerAction


class EvalType(enum.Enum):
  ALPHA = enum.auto()
  BETA = enum.auto()
  EXACT = enum.auto()


class Node:
  def __init__(self):
    self.eval_type = None
    self.score = None
    self.children = None
    self.best_action = None

  def evaluate(self, alpha, beta):
    if self.eval_type == EvalType.EXACT:
      return self.score
    if self.eval_type == EvalType.ALPHA and self.score <= alpha:
      return alpha
    if self.eval_type == EvalType.BETA and self.score >= beta:
      return beta
    return None

  def __repr__(self):
    return f"{self.score}, {self.eval_type}"


class AlphaBeta:
  def __init__(self, max_search_time, shuffle, player_id):
    self._max_search_time = max_search_time
    self._shuffle = shuffle
    self._cache: Dict[GameState, Node] = {}
    self._player_id = player_id

  def get_best_action(self, game_state: GameState):
    self.search(game_state, -10, 10)
    node = self._cache[game_state]
    if True:
      debug_info = {action: self._cache.get(new_game_state, None) for
                    action, new_game_state in node.children.items()}
      logging.info("AlphaBeta: %s", pprint.pformat(str(debug_info)))
    return self._cache[game_state].best_action

  def search(self, game_state: GameState, alpha: float, beta: float):
    node = self._cache.get(game_state, None)
    if node is not None:
      score = node.evaluate(alpha, beta)
      if score is not None:
        return score
    if game_state.is_game_over:
      score = self._get_score(game_state)
      self._update(game_state, score, EvalType.EXACT, None, None)
      return score
    if node is not None and node.children is not None:
      children = node.children
    else:
      children = _get_children(game_state)
    if self._shuffle:
      pass  # shuffle a copy here
    max_player = self._player_id == game_state.next_player
    best_action = None
    if max_player:
      eval_type = EvalType.ALPHA
      for action, new_game_state in children.items():
        score = self.search(new_game_state, alpha, beta)
        if alpha < score:
          alpha = score
          best_action = action
          eval_type = EvalType.EXACT
        if beta <= alpha:
          eval_type = EvalType.BETA
          self._update(game_state, beta, EvalType.BETA, children, best_action)
          break
      if eval_type == EvalType.BETA:
        self._update(game_state, beta, EvalType.BETA, children, best_action)
      return alpha

    eval_type = EvalType.BETA
    for action, new_game_state in children.items():
      score = self.search(new_game_state, alpha, beta)
      if score < beta:
        beta = score
        best_action = action
        eval_type = EvalType.EXACT
      if beta <= alpha:
        eval_type = EvalType.ALPHA
        self._update(game_state, alpha, EvalType.ALPHA, children, best_action)
        break
    if eval_type == EvalType.ALPHA:
      self._update(game_state, beta, eval_type, children, best_action)
    return beta

  def _get_score(self, game_state):
    game_points = game_state.game_points
    score = game_points[self._player_id] - game_points[
      self._player_id.opponent()]
    return score

  def _update(self, game_state: GameState, score, eval_type, children,
              best_action):
    if game_state not in self._cache:
      node = Node()
      self._cache[game_state] = node
    else:
      node = self._cache[game_state]
    node.eval_type = eval_type
    node.score = score
    node.children = children
    node.best_action = best_action


def _get_children(game_state: GameState):
  result = {}
  for action in get_available_actions(game_state):
    new_game_state = copy.deepcopy(game_state)
    action.execute(new_game_state)
    result[action] = new_game_state
  return result


class AlphaBetaPlayer(Player):
  def request_next_action(self, game_view: GameState) -> PlayerAction:
    alpha_beta = AlphaBeta(224, False, self.id)
    return alpha_beta.get_best_action(game_view)
