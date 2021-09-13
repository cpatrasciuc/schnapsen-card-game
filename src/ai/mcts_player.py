#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import abc
import functools
import logging
import math
import multiprocessing
import random
from typing import List, Optional, Tuple

from ai.mcts_algorithm import Mcts, SchnapsenNode, ucb_for_player
from ai.mcts_player_options import MctsPlayerOptions
from ai.merge_root_nodes_func import ScoringInfo, ActionsWithScores
from ai.player import Player
from ai.utils import populate_game_view, get_unseen_cards
from model.card import Card
from model.game_state import GameState
from model.player_action import PlayerAction
from model.player_id import PlayerId


def _find_action_with_max_score(
    actions_and_scores: List[Tuple[PlayerAction, float]]) -> PlayerAction:
  """
  Given a list of PlayerActions and merged scores across all perfect information
  Mcts trees, it returns the action with the highest score. If there are
  multiple actions having the highest score, it picks one of them randomly.
  """
  # TODO(mcts): If multiple actions have the same score, use tiebreakers like
  #  ucb, card value * sign(ucb).
  max_score = max(score for action, score in actions_and_scores)
  actions_with_max_score = \
    [action for action, score in actions_and_scores if score == max_score]
  return random.choice(actions_with_max_score)


def run_mcts(permutation: List[Card], game_view: GameState,
             player_id: PlayerId, max_iterations: int) -> ActionsWithScores:
  game_state = populate_game_view(game_view, permutation)
  mcts_algorithm = Mcts(player_id)
  root_node = mcts_algorithm.build_tree(game_state, max_iterations)
  actions_with_scores = {}
  for action, child in root_node.children.items():
    if child is None:
      continue
    actions_with_scores[action] = ScoringInfo(
      q=(child.q if child.player == root_node.player else -child.q),
      n=child.n, score=ucb_for_player(child, root_node.player),
      fully_simulated=child.fully_simulated,
      terminal=child.terminal)
  return actions_with_scores


class BaseMctsPlayer(Player, abc.ABC):
  """Base class for a Player that uses the Mcts algorithm."""

  def __init__(self, player_id: PlayerId, cheater: bool = False,
               options: Optional[MctsPlayerOptions] = None):
    """
    Creates a new MctsPlayer.
    :param player_id: The ID of the player in a game of Schnapsen (ONE or TWO).
    :param cheater: If True, this player will always know the cards in their
    opponent's hand and the order of the cards in the talon.
    :param options: The parameters used to configure the MctsPlayer.
    """
    super().__init__(player_id, cheater)
    self._options = options or MctsPlayerOptions()

  def _generate_permutations(self, game_view: GameState) -> List[List[Card]]:
    """
    Given a game view that represents an imperfect information game, this method
    returns the card permutations that should be used by the Mcts algorithm to
    generate a list of perfect information games and process them.
    """
    cards_set = get_unseen_cards(game_view)
    assert len(cards_set) == 0 or not self.cheater, cards_set
    num_unknown_cards = len(cards_set)
    num_opponent_unknown_cards = len(
      [card for card in game_view.cards_in_hand[self.id.opponent()] if
       card is None])
    total_permutations = \
      math.comb(num_unknown_cards, num_opponent_unknown_cards) * \
      math.perm(num_unknown_cards - num_opponent_unknown_cards)
    num_permutations_to_process = min(total_permutations,
                                      self._options.max_permutations)
    assert num_permutations_to_process == 1 or not self.cheater
    logging.info("MctsPlayer: Num permutations: %s out of %s",
                 num_permutations_to_process, total_permutations)
    return self._options.perm_generator(
      cards_set, num_opponent_unknown_cards, num_permutations_to_process)

  def request_next_action(self, game_view: GameState) -> PlayerAction:
    permutations = self._generate_permutations(game_view)
    actions_with_scores_list = self.run_mcts_algorithm(game_view, permutations)
    if __debug__:
      for actions_with_scores in actions_with_scores_list:
        for action, score in actions_with_scores.items():
          print(action, "-->", score)
        print()
    actions_and_scores = self._options.merge_root_nodes_func(
      actions_with_scores_list)
    return _find_action_with_max_score(actions_and_scores)

  @abc.abstractmethod
  def run_mcts_algorithm(self, game_view: GameState,
                         permutations: List[List[Card]]) -> List[SchnapsenNode]:
    """
    This method is overridden by subclasses to run a particular implementation
    of the Mcts algorithm, given a game view and a list of permutations that
    convert the imperfect information game in a list of perfect information
    games. It returns a list of Mcts root nodes, one for each permutation.
    """

  def cleanup(self) -> None:
    """
    This method should be overridden by subclasses in case there is some cleanup
    work to be done before the player is deleted.
    """


class MctsPlayer(BaseMctsPlayer):
  """
  Implementation of BaseMctsPlayer that uses a multiprocessing.Pool to run
  multiple instances of an Mcts algorithm in parallel.
  """

  def __init__(self, player_id: PlayerId, cheater: bool = False,
               options: Optional[MctsPlayerOptions] = None):
    super().__init__(player_id, cheater, options)
    # pylint: disable=consider-using-with
    self._pool = multiprocessing.Pool(processes=self._options.num_processes)
    # pylint: enable=consider-using-with
    logging.info("MctsPlayer: Multiprocessing pool using %s processes.",
                 self._options.num_processes)

  def cleanup(self) -> None:
    self._pool.terminate()
    self._pool.join()

  def run_mcts_algorithm(self, game_view: GameState,
                         permutations: List[List[Card]]) -> List[
    ActionsWithScores]:
    root_nodes = self._pool.map(
      functools.partial(run_mcts, game_view=game_view, player_id=self.id,
                        max_iterations=self._options.max_iterations),
      permutations)
    return root_nodes
