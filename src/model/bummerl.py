#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import random
from typing import List, Optional

from model.game import Game
from model.player_id import PlayerId
from model.player_pair import PlayerPair


class Bummerl:
  """
  A Bummerl consists of several individual games and the dealer alternates with
  each game. The player who is the first to seven game points wins.
  """

  def __init__(self, next_dealer: Optional[PlayerId] = None):
    """
    Creates a new Bummerl.
    :param next_dealer: the ID of the player that will be the dealer in the
    first game. If it is None, the dealer will be selected at random for the
    first game and then it will alternate with each game.
    """
    self._next_dealer: PlayerId = next_dealer
    if self._next_dealer is None:
      self._next_dealer = random.choice([PlayerId.ONE, PlayerId.TWO])
    self._game = None
    self._completed_games: List[Game] = []
    self._game_points: PlayerPair[int] = PlayerPair(0, 0)

  @property
  def game(self) -> Optional[Game]:
    """The current game, if any."""
    return self._game

  @property
  def completed_games(self) -> List[Game]:
    return self._completed_games

  @property
  def game_points(self) -> PlayerPair[int]:
    """
    The game points scored so far from completed games. It does not include the
    current game, even if it is in a game-over state, until finalize_game() is
    called.
    """
    return self._game_points

  def start_game(self, seed: Optional[int] = None) -> Game:
    """
    Starts a new game as part of this Bummerl. It cannot be called if a game is
    already in progress or if one player already reached 7 points.
    :param seed: an integer used as a seed for the random number generator that
    shuffles the cards.
    """
    assert self._game is None, "Game in progress"
    assert not self.is_over, f"Bummerl is over: {self.game_points}"
    self._game = Game(dealer=self._next_dealer, seed=seed)
    self._next_dealer = self._next_dealer.opponent()
    return self._game

  def finalize_game(self):
    """
    If the current game is over, it adds it to the list of completed games and
    updates the Bummerl score. It cannot be called if the current game is not
    over. It does not create a new game automatically.
    """
    assert self._game.game_state.is_game_over, "Current game is not over"
    self._completed_games.append(self._game)
    game_points = self._game.game_state.score()
    self._game_points.one += game_points.one
    self._game_points.two += game_points.two
    self._game = None

  @property
  def is_over(self):
    """Returns True if one player reached 7 points."""
    return self._game_points.one > 6 or self._game_points.two > 6
