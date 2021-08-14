#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from typing import Optional

from ai.mcts_player import MctsPlayer
from ai.utils import get_unseen_cards, populate_game_view
from model.card import Card
from model.card_value import CardValue
from model.game_state_test_utils import get_game_view_for_duck_puzzle, \
  get_game_view_for_who_laughs_last_puzzle, \
  get_game_state_for_forcing_the_issue_puzzle
from model.player_action import PlayCardAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit


class MctsPlayerTest(unittest.TestCase):
  def setUp(self) -> None:
    self._mcts_player = MctsPlayer(PlayerId.ONE, time_limit_sec=None)

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

  def test_who_laughs_last_puzzle(self):
    game_view = get_game_view_for_who_laughs_last_puzzle()
    action = self._mcts_player.request_next_action(game_view)
    print(f"Selected action: {action}")
    expected_actions = {
      PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.KING)),
      PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.QUEEN))
    }
    self.assertIn(action, expected_actions)

  def _play_against_another_mcts_player_until_the_end(self, game_state):
    player_two: Optional[MctsPlayer] = None
    try:
      player_two = MctsPlayer(PlayerId.TWO, time_limit_sec=None)
      players = PlayerPair(self._mcts_player, player_two)
      while not game_state.is_game_over:
        player = players[game_state.next_player]
        action = player.request_next_action(game_state.next_player_view())
        print(f"{game_state.next_player}: {action}")
        action.execute(game_state)
    finally:
      if player_two is not None:
        player_two.cleanup()

  def test_who_laughs_last_puzzle_part_two(self):
    game_view = get_game_view_for_who_laughs_last_puzzle()
    game_view.talon = [Card(Suit.DIAMONDS, CardValue.ACE)]
    unseen_cards = get_unseen_cards(game_view)
    self.assertEqual(4, len(unseen_cards))
    game_state = populate_game_view(game_view, unseen_cards)
    action = PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.KING))
    action.execute(game_state)
    self.assertEqual(PlayerPair(19, 26), game_state.trick_points)
    self._play_against_another_mcts_player_until_the_end(game_state)
    self.assertEqual(0, game_state.game_points.two)

  # TODO(mcts): See if this improves after merging the parallel trees.
  @unittest.skip(
    "Player ONE doesn't know the whole state (i.e., the card in the talon), " +
    "so it's probably doing the right moves")
  def test_forcing_the_issue_puzzle(self):
    game_state = get_game_state_for_forcing_the_issue_puzzle()
    self._play_against_another_mcts_player_until_the_end(game_state)
    self.assertEqual(0, game_state.game_points.two)
