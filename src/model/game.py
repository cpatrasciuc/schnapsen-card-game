#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from typing import List

from model.game_state import GameState
from model.player_action import PlayerAction
from model.player_id import PlayerId


class Game:
  """
  A class that stores a game of Schnapsen: it stores the initial state (i.e.,
  the dealer ID and the random seed used to shuffle the deck) and a list of
  player actions that were performed so far. The game could not be over yet.
  It supports pickling/unpickling.
  """

  def __init__(self, dealer: PlayerId, seed: int):
    self._dealer = dealer
    self._seed = seed
    self._game_state: GameState = GameState.new(dealer=dealer, random_seed=seed)
    self._actions: List[PlayerAction] = []

  @property
  def game_state(self) -> GameState:
    return self._game_state

  def play_action(self, action: PlayerAction) -> None:
    """
    Executes the given player action. The action must be a legal action in the
    current state of the game.
    """
    assert not self._game_state.is_game_over()
    self._actions.append(action)
    action.execute(self._game_state)

  def __getstate__(self):
    """
    Returns the object that should be saved during pickling.
    Doesn't export the current game state. It can be recreated by starting from
    the same initial state and performing all the actions when unpickling.
    """
    state = self.__dict__.copy()
    del state['_game_state']
    return state

  def __setstate__(self, state):
    """
    Restore the instance variable and recreate the game state by executing all
    the player actions.
    """
    self.__dict__.update(state)
    self._game_state: GameState = GameState.new(dealer=self._dealer,
                                                random_seed=self._seed)
    for action in self._actions:
      action.execute(self._game_state)
