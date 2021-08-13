#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from ai.mcts_player import MctsPlayer
from model.card import Card
from model.card_value import CardValue
from model.game_state_test_utils import get_game_view_for_duck_puzzle
from model.player_action import PlayCardAction
from model.player_id import PlayerId
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
