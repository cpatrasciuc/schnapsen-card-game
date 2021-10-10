#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import functools
import os
import unittest
from typing import Optional, List

from ai.cython_mcts_player.player import CythonMctsPlayer
from ai.mcts_player import MctsPlayer
from ai.mcts_player_options import MctsPlayerOptions
from ai.merge_scoring_infos_func import best_action_frequency, \
  average_ucb, ActionsWithScores, merge_ucbs_using_simple_average, \
  merge_ucbs_using_weighted_average, count_visits
from ai.utils import get_unseen_cards, populate_game_view
from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState
from model.game_state_test_utils import get_game_view_for_duck_puzzle, \
  get_game_state_for_who_laughs_last_puzzle, \
  get_game_state_for_forcing_the_issue_puzzle, \
  get_game_view_for_the_last_trump_puzzle, \
  get_game_state_for_know_your_opponent_puzzle, \
  get_game_view_for_grab_the_brass_ring_puzzle
from model.player_action import PlayCardAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit


# TODO(tests): Investigate why this fails on GitHub.
@unittest.skipIf("GITHUB_ACTIONS" in os.environ,
                 "Disable these tests on GitHub")
class MctsPlayerTest(unittest.TestCase):
  def setUp(self) -> None:
    options = MctsPlayerOptions(max_iterations=None)
    self._mcts_player = MctsPlayer(PlayerId.ONE, options=options)

  def tearDown(self) -> None:
    self._mcts_player.cleanup()

  def test_duck_puzzle(self):
    game_view = get_game_view_for_duck_puzzle()
    action = self._mcts_player.request_next_action(game_view)
    print(f"Selected action: {action}")
    expected_actions = {
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)),
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN))
    }
    self.assertIn(action, expected_actions)

  def _play_against_another_mcts_player_until_the_end(self,
                                                      game_state) -> GameState:
    player_two: Optional[MctsPlayer] = None
    try:
      options = MctsPlayerOptions(max_iterations=None)
      player_class = self._mcts_player.__class__
      if player_class == CythonMctsPlayer:
        options.num_processes = 1
      player_two = player_class(PlayerId.TWO, options=options)
      players = PlayerPair(self._mcts_player, player_two)
      while not game_state.is_game_over:
        player = players[game_state.next_player]
        action = player.request_next_action(game_state.next_player_view())
        print(f"{game_state.next_player}: {action}")
        game_state = action.execute(game_state)
    finally:
      if player_two is not None:
        player_two.cleanup()
    return game_state

  def test_who_laughs_last_puzzle(self):
    # Part one
    game_state = get_game_state_for_who_laughs_last_puzzle()
    action = self._mcts_player.request_next_action(
      game_state.next_player_view())
    expected_actions = {
      PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.KING)),
      PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.QUEEN))
    }
    self.assertIn(action, expected_actions)
    game_state = action.execute(game_state)
    if action.card.card_value == CardValue.KING:
      self.assertEqual(PlayerPair(19, 26), game_state.trick_points)
    else:
      self.assertEqual(PlayerPair(18, 26), game_state.trick_points)
    # Part two
    game_state = self._play_against_another_mcts_player_until_the_end(
      game_state)
    self.assertEqual(0, game_state.game_points.two)

  # TODO(mcts): See if this improves after merging the parallel trees.
  @unittest.skip(
    "Player ONE doesn't know the whole state (i.e., the card in the talon), " +
    "so it's probably doing the right moves")
  def test_forcing_the_issue_puzzle(self):
    game_state = get_game_state_for_forcing_the_issue_puzzle()
    game_state = self._play_against_another_mcts_player_until_the_end(
      game_state)
    self.assertEqual(0, game_state.game_points.two)

  def test_the_last_trump_puzzle(self):
    game_view = get_game_view_for_the_last_trump_puzzle()
    action = self._mcts_player.request_next_action(game_view)
    print(f"Selected action: {action}")
    self.assertEqual(
      PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.TEN)), action)

    game_state = populate_game_view(game_view, get_unseen_cards(game_view))
    game_state = action.execute(game_state)
    game_state = self._play_against_another_mcts_player_until_the_end(
      game_state)
    self.assertEqual(0, game_state.game_points.two)

  def test_know_your_opponent_puzzle(self):
    game_state = get_game_state_for_know_your_opponent_puzzle()
    game_state = self._play_against_another_mcts_player_until_the_end(
      game_state)
    self.assertEqual(0, game_state.game_points.two)

    # If we just run the MctsPlayer for Player.TWO, it doesn't play the Ace
    # of Spades as the second card to challenge Player.ONE as described in the
    # puzzle, so we run this scenario manually here.
    game_state = get_game_state_for_know_your_opponent_puzzle()
    action = PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.KING))
    game_state = action.execute(game_state)
    action = PlayCardAction(PlayerId.TWO, Card(Suit.SPADES, CardValue.ACE))
    game_state = action.execute(game_state)
    action = self._mcts_player.request_next_action(
      game_state.next_player_view())
    self.assertEqual(
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)), action)
    game_state = action.execute(game_state)
    game_state = self._play_against_another_mcts_player_until_the_end(
      game_state)
    self.assertEqual(0, game_state.game_points.two)

  def test_grab_the_brass_ring_puzzle(self):
    game_view = get_game_view_for_grab_the_brass_ring_puzzle()
    action = self._mcts_player.request_next_action(game_view)
    self.assertEqual(
      PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.ACE)), action)


class MctsPlayerMostFrequentBestActionTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(
      max_iterations=None, merge_scoring_info_func=best_action_frequency)
    self._mcts_player = MctsPlayer(PlayerId.ONE, options=options)


class InProcessMctsPlayerTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(max_iterations=None, num_processes=1)
    self._mcts_player = MctsPlayer(PlayerId.ONE, options=options)


class MctsPlayerSelectBestChildTest(MctsPlayerTest):
  def setUp(self) -> None:
    # Run in-process so that code coverage sees this code-path.
    options = MctsPlayerOptions(max_iterations=None, select_best_child=True,
                                num_processes=1)
    self._mcts_player = MctsPlayer(PlayerId.ONE, options=options)


class MctsPlayerWithSaveRewards(unittest.TestCase):
  def test_cannot_instantiate_with_save_rewards(self) -> None:
    options = MctsPlayerOptions(max_iterations=None, save_rewards=True)
    with self.assertRaisesRegex(ValueError, "save_rewards is not supported"):
      MctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerMaxAverageUcbTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(max_iterations=None,
                                merge_scoring_info_func=average_ucb,
                                num_processes=1)
    self._mcts_player = CythonMctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerMostFrequentBestActionTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(
      max_iterations=None, merge_scoring_info_func=best_action_frequency,
      num_processes=1)
    self._mcts_player = CythonMctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerCountVisitsTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(
      max_iterations=None,
      merge_scoring_info_func=count_visits,
      num_processes=1)
    self._mcts_player = CythonMctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerMergeUcbsUsingSimpleAverageTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(
      max_iterations=None,
      merge_scoring_info_func=merge_ucbs_using_simple_average,
      num_processes=1)
    self._mcts_player = CythonMctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerMergeUcbsUsingWeightedAverageTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(
      max_iterations=None,
      merge_scoring_info_func=merge_ucbs_using_weighted_average,
      num_processes=1)
    self._mcts_player = CythonMctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerWithParallelismTest(unittest.TestCase):
  def test_cannot_instantiate_with_multi_threading(self) -> None:
    options = MctsPlayerOptions(max_iterations=None, num_processes=10)
    with self.assertRaisesRegex(ValueError, "10 threads"):
      CythonMctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerSelectBestChildTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(max_iterations=None,
                                select_best_child=True,
                                num_processes=1)
    self._mcts_player = CythonMctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerSaveRewardsTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(max_iterations=None,
                                select_best_child=True,
                                save_rewards=True,
                                num_processes=1)
    self._mcts_player = CythonMctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerUseHeuristicTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(max_iterations=None,
                                select_best_child=True,
                                use_heuristic=True,
                                num_processes=1)
    self._mcts_player = CythonMctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerTest(unittest.TestCase):
  @staticmethod
  def test_max_iterations_less_than_available_actions():
    # Here not all of the root node's children will be expanded.
    options = MctsPlayerOptions(max_iterations=1, max_permutations=10,
                                num_processes=1)
    game_state = GameState.new(random_seed=0)
    mcts_player = CythonMctsPlayer(game_state.next_player, False, options)
    mcts_player.request_next_action(game_state.next_player_view())


class ReallocateComputationalBudgetTest(unittest.TestCase):
  def _assert_num_iterations(self,
                             expected_iterations: int,
                             actions_with_scores_list: List[ActionsWithScores]):
    dummy_output = {}
    iterations = 0
    for actions_with_scores in actions_with_scores_list:
      for action, scoring_info in actions_with_scores.items():
        iterations += scoring_info.n
        dummy_output[action] = scoring_info.score
    self.assertEqual(expected_iterations, iterations)
    return list(dummy_output.items())

  def _run_test(self, player_class):
    options = MctsPlayerOptions(
      num_processes=1,
      max_permutations=10,
      max_iterations=10,
      merge_scoring_info_func=functools.partial(self._assert_num_iterations,
                                                10 * 10),
      reallocate_computational_budget=False)
    game_view = GameState.new(random_seed=0).next_player_view()
    player = player_class(game_view.next_player, False, options)
    player.get_actions_and_scores(game_view)

    # There is one card left in the talon, the opponent played already a card
    # from their hand, so there are only 4 unknown cards in the opponent's hand.
    # This means there are only 4 permutations possible.
    game_view = get_game_view_for_duck_puzzle()

    # Without reallocating the computational budget, the player runs 4
    # permutations of 100 iterations each.
    options = MctsPlayerOptions(
      num_processes=1,
      max_permutations=100,
      max_iterations=100,
      merge_scoring_info_func=functools.partial(self._assert_num_iterations,
                                                4 * 100),
      reallocate_computational_budget=False)
    player = player_class(game_view.next_player, False, options)
    player.get_actions_and_scores(game_view)

    # When reallocating the computational budget, the player runs 4
    # permutations of 2500 iterations each, but 5784 are enough to simulate the
    # entire game tree.
    options = MctsPlayerOptions(
      num_processes=1,
      max_permutations=100,
      max_iterations=100,
      merge_scoring_info_func=functools.partial(self._assert_num_iterations,
                                                5784),
      reallocate_computational_budget=True)
    player = player_class(game_view.next_player, False, options)
    player.get_actions_and_scores(game_view)

    # If max_iterations is None, the computational budget is unlimited, so
    # reallocate_computational_budget has no effect.
    options = MctsPlayerOptions(
      num_processes=1,
      max_permutations=100,
      max_iterations=None,
      merge_scoring_info_func=functools.partial(self._assert_num_iterations,
                                                5784),
      reallocate_computational_budget=False)
    player = player_class(game_view.next_player, False, options)
    player.get_actions_and_scores(game_view)
    options = MctsPlayerOptions(
      num_processes=1,
      max_permutations=100,
      max_iterations=None,
      merge_scoring_info_func=functools.partial(self._assert_num_iterations,
                                                5784),
      reallocate_computational_budget=True)
    player = player_class(game_view.next_player, False, options)
    player.get_actions_and_scores(game_view)

  def test_mcts_player(self):
    self._run_test(MctsPlayer)

  def test_cython_mcts_player(self):
    self._run_test(CythonMctsPlayer)
