#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from typing import Optional

from ai.cython_mcts_player.player import CythonMctsPlayer
from ai.mcts_player import MctsPlayer
from ai.mcts_player_options import MctsPlayerOptions
from ai.merge_scoring_infos_func import most_frequent_best_action, merge_ucbs, \
  max_average_ucb
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
      max_iterations=None, merge_scoring_info_func=most_frequent_best_action)
    self._mcts_player = MctsPlayer(PlayerId.ONE, options=options)


class MctsPlayerMergeUcbsTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(max_iterations=None,
                                merge_scoring_info_func=merge_ucbs)
    self._mcts_player = MctsPlayer(PlayerId.ONE, options=options)


class InProcessMctsPlayerTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(max_iterations=None, num_processes=1)
    self._mcts_player = MctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerMaxAverageUcbTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(max_iterations=None,
                                merge_scoring_info_func=max_average_ucb,
                                num_processes=1)
    self._mcts_player = CythonMctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerMostFrequentBestActionTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(
      max_iterations=None, merge_scoring_info_func=most_frequent_best_action,
      num_processes=1)
    self._mcts_player = CythonMctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerMergeUcbsTest(MctsPlayerTest):
  def setUp(self) -> None:
    options = MctsPlayerOptions(max_iterations=None,
                                merge_scoring_info_func=merge_ucbs,
                                num_processes=1)
    self._mcts_player = CythonMctsPlayer(PlayerId.ONE, options=options)


class CythonMctsPlayerWithParallelismTest(unittest.TestCase):
  def test_cannot_instantiate_with_multi_threading(self) -> None:
    options = MctsPlayerOptions(max_iterations=None,
                                num_processes=10)
    with self.assertRaisesRegex(ValueError, "10 threads"):
      CythonMctsPlayer(PlayerId.ONE, options=options)
