#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import threading
import time
import unittest
from multiprocessing import Event
from unittest.mock import Mock

from ai.player import Player as AIPlayer
from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState
from model.game_state_test_utils import get_game_state_for_tests
from model.player_action import PlayCardAction, PlayerAction
from model.player_id import PlayerId
from model.suit import Suit
from ui.computer_player import ComputerPlayer, OutOfProcessComputerPlayer
from ui.test_utils import GraphicUnitTest


class ComputerPlayerTest(unittest.TestCase):
  def test(self):
    action = PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE))

    class TestPlayer(AIPlayer):
      def request_next_action(self, game_view: GameState) -> PlayerAction:
        return action

    ai_player = TestPlayer(PlayerId.ONE, True)
    player = ComputerPlayer(ai_player)
    self.assertTrue(player.is_cheater())
    game_state = get_game_state_for_tests()
    callback = Mock()
    player.request_next_action(game_state, callback)
    callback.assert_called()
    self.assertEqual(action, callback.call_args.args[0])


class _OutOfProcessTestPlayer(AIPlayer):
  def __init__(self, player_id: PlayerId, cheater: bool, event: Event):
    super().__init__(player_id, cheater)
    self._event = event

  def request_next_action(self, game_view: GameState) -> PlayerAction:
    self._event.wait()
    return PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE))


class OutOfProcessComputerPlayerTest(GraphicUnitTest):
  def test(self):
    self.render(None)
    event = Event()
    player = OutOfProcessComputerPlayer(_OutOfProcessTestPlayer,
                                        (PlayerId.ONE, True, event))
    self.assertTrue(player.is_cheater())
    game_state = get_game_state_for_tests()
    callback = Mock()
    player.request_next_action(game_state, callback)
    callback.assert_not_called()
    self.advance_frames(5)
    callback.assert_not_called()
    event.set()
    self.wait_for_mock_callback(callback, 5)
    self.assertEqual(
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)),
      callback.call_args.args[0])
    player.cleanup()

  def test_cleanup_player_before_the_reply_is_received(self):
    self.render(None)
    event = Event()
    player = OutOfProcessComputerPlayer(_OutOfProcessTestPlayer,
                                        (PlayerId.ONE, True, event))
    game_state = get_game_state_for_tests()
    callback = Mock()
    player.request_next_action(game_state, callback)
    self.advance_frames(5)

    def set_event_after_one_second():
      time.sleep(1)
      event.set()

    thread = threading.Thread(target=set_event_after_one_second)
    thread.start()
    self.advance_frames(5)
    player.cleanup()
    self.advance_frames(5)
    callback.assert_not_called()
