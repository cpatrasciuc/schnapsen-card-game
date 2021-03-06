#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import abc
import copy
import functools
import logging
import math
import multiprocessing
import random
from typing import List, Optional

from ai.mcts_algorithm import Mcts, ucb_for_player
from ai.mcts_player_options import MctsPlayerOptions
from ai.merge_scoring_infos_func import ScoringInfo, ActionsWithScores, \
  AggregatedScores
from ai.player import Player
from ai.utils import populate_game_view, get_unseen_cards
from model.card import Card
from model.game_state import GameState
from model.player_action import PlayerAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair


def _find_action_with_max_score(
    actions_and_scores: AggregatedScores) -> PlayerAction:
  """
  Given a list of PlayerActions and merged scores across all perfect information
  Mcts trees, it returns the action with the highest score. If there are
  multiple actions having the highest score, it picks one of them randomly.
  """
  max_score = max(score for action, score in actions_and_scores)
  actions_with_max_score = \
    [action for action, score in actions_and_scores if score == max_score]
  return random.choice(actions_with_max_score)


def generate_permutations(game_view: GameState,
                          options: MctsPlayerOptions) -> List[List[Card]]:
  """
  Given a game view that represents an imperfect information game, this function
  returns the card permutations that should be used by the Mcts algorithm to
  generate a list of perfect information games and process them.
  """
  cards_set = get_unseen_cards(game_view)
  num_unknown_cards = len(cards_set)
  num_opponent_unknown_cards = len(
    [card for card in
     game_view.cards_in_hand[game_view.next_player.opponent()] if
     card is None])
  total_permutations = \
    math.comb(num_unknown_cards, num_opponent_unknown_cards) * \
    math.perm(num_unknown_cards - num_opponent_unknown_cards)
  num_permutations_to_process = min(total_permutations,
                                    options.max_permutations)
  logging.info("MctsPlayer: Num permutations: %s out of %s",
               num_permutations_to_process, total_permutations)
  permutations = options.perm_generator(
    cards_set, num_opponent_unknown_cards, num_permutations_to_process)
  return permutations


def run_mcts(permutation: List[Card], game_view: GameState,
             player_id: PlayerId,
             options: MctsPlayerOptions) -> ActionsWithScores:
  game_state = populate_game_view(game_view, permutation)
  mcts_algorithm = Mcts(player_id, exploration_param=options.exploration_param)
  root_node = mcts_algorithm.build_tree(game_state, options.max_iterations,
                                        options.select_best_child)
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
    permutations = generate_permutations(game_view, self._options)
    assert len(permutations) == 1 or not self.cheater
    return permutations

  def get_actions_and_scores(self, game_view: GameState, game_points: Optional[
    PlayerPair[int]] = None) -> AggregatedScores:
    permutations = self._generate_permutations(game_view)
    actions_with_scores_list = self.run_mcts_algorithm(game_view, permutations,
                                                       game_points)
    if __debug__:
      for actions_with_scores in actions_with_scores_list:
        for action, score in actions_with_scores.items():
          print(action, "-->", score)
        print()
    actions_and_scores = self._options.merge_scoring_info_func(
      actions_with_scores_list)
    return actions_and_scores

  def request_next_action(self, game_view: GameState, game_points: Optional[
    PlayerPair[int]] = None) -> PlayerAction:
    actions_and_scores = self.get_actions_and_scores(game_view, game_points)
    return _find_action_with_max_score(actions_and_scores)

  @abc.abstractmethod
  def run_mcts_algorithm(self, game_view: GameState,
                         permutations: List[List[Card]],
                         game_points: Optional[PlayerPair[int]] = None) -> List[
    ActionsWithScores]:
    """
    This method is overridden by subclasses to run a particular implementation
    of the Mcts algorithm, given a game view and a list of permutations that
    convert the imperfect information game in a list of perfect information
    games. It returns a list of ActionsWithScores dicts, one for each
    permutation. If provided, the game_points argument represents the score at
    bummerl level.
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
    self._pool = None
    if options.num_processes != 1:
      # pylint: disable=consider-using-with
      self._pool = multiprocessing.Pool(processes=self._options.num_processes)
      # pylint: enable=consider-using-with
      logging.info("MctsPlayer: Multiprocessing pool using %s processes.",
                   self._options.num_processes)
    else:
      logging.info("MctsPlayer: Mcts will run in-process.")
    if options.save_rewards:
      raise ValueError("save_rewards is not supported by MctsPlayer")
    if options.use_game_points:
      logging.warning("MctsPlayer: MctsPlayerOptions.use_game_points is True, "
                      "but MctsPlayer ignores game_points.")

  def cleanup(self) -> None:
    if self._pool is not None:
      self._pool.terminate()
      self._pool.join()

  def run_mcts_algorithm(self, game_view: GameState,
                         permutations: List[List[Card]],
                         game_points: Optional[PlayerPair[int]] = None) -> List[
    ActionsWithScores]:
    options = self._options
    if options.reallocate_computational_budget and \
        options.max_iterations is not None and \
        len(permutations) < options.max_permutations:
      options = copy.copy(options)
      total_budget = options.max_permutations * options.max_iterations
      options.max_iterations = total_budget / len(permutations)
    if self._pool is not None:
      actions_with_scores_list = self._pool.map(
        functools.partial(run_mcts, game_view=game_view, player_id=self.id,
                          options=options),
        permutations)
    else:
      actions_with_scores_list = [
        run_mcts(permutation, game_view, self.id, options)
        for permutation in permutations]
    return actions_with_scores_list
