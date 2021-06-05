#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from unittest.mock import Mock

from model.bummerl import Bummerl
from model.game_state import GameState
from model.game_state_test_utils import get_actions_for_one_complete_game
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from ui.game_controller import GameController
from ui.game_widget import GameWidget
from ui.player import RandomPlayer
from ui.test_utils import GraphicUnitTest


# pylint: disable=too-many-locals,too-many-statements,


class GameControllerTest(GraphicUnitTest):
  def test_new_bummerl_new_game(self):
    self.render(None)

    game_widget = Mock()
    players = PlayerPair(Mock(), Mock())
    score_view = Mock()
    # noinspection PyTypeChecker
    game_controller = GameController(game_widget, players, score_view)

    bummerl = Bummerl(next_dealer=PlayerId.ONE)
    bummerl.start_game(seed=2)
    actions = get_actions_for_one_complete_game(PlayerId.TWO)

    expected_game_state = GameState.new(dealer=PlayerId.ONE, random_seed=2)

    game_controller.start(bummerl)

    # Initializes the game widget.
    game_widget.reset.assert_called_once()
    game_widget.init_from_game_state.assert_called_once()
    actual_game_state, done_callback, game_points = \
      game_widget.init_from_game_state.call_args.args
    self.assertEqual(expected_game_state, actual_game_state)
    self.assertEqual(PlayerPair(0, 0), game_points)
    game_widget.reset_mock()
    done_callback()

    indices_of_actions_that_complete_a_trick = [1, 4, 6, 8, 10, 12]

    for i, action in enumerate(actions):
      print(f"Testing action #{i}: {action}")

      # Player action is requested.
      players[action.player_id].request_next_action.assert_called_once()
      actual_game_state, action_callback = \
        players[action.player_id].request_next_action.call_args.args
      self.assertEqual(expected_game_state, actual_game_state)
      action.execute(expected_game_state)
      players[action.player_id].reset_mock()

      # Player responds with an action.
      action_callback(action)

      # GameWidget.on_action() is called to update the UI.
      game_widget.on_action.assert_called_once()
      actual_action, done_callback = game_widget.on_action.call_args.args
      self.assertEqual(action, actual_action)
      game_widget.reset_mock()
      done_callback()

      # If a trick is completed, GameWidget.on_score_modified() is called and
      # GameWidget.on_trick_completed() is called.
      if i in indices_of_actions_that_complete_a_trick:
        game_widget.on_score_modified.assert_called_once()
        actual_score = game_widget.on_score_modified.call_args.args[0]
        self.assertEqual(expected_game_state.trick_points, actual_score)

        self.wait_for_mock_callback(game_widget.on_trick_completed)
        last_trick, winner, cards_in_hard, draw_new_cards, done_callback = \
          game_widget.on_trick_completed.call_args.args
        self.assertEqual(expected_game_state.next_player, winner)
        self.assertEqual(expected_game_state.won_tricks[winner][-1], last_trick)
        self.assertEqual(expected_game_state.cards_in_hand, cards_in_hard)
        self.assertEqual(i == 1, draw_new_cards)
        game_widget.reset_mock()
        done_callback()

    # The game is over. The score_view_callback is called.
    score_view.assert_called_once()
    score_history, dismiss_callback = score_view.call_args.args
    self.assertEqual([(PlayerPair(13, 67), PlayerPair(0, 3))], score_history)
    score_view.reset_mock()
    dismiss_callback()

    # A new game is started.
    game_widget.reset.assert_called_once()
    game_widget.init_from_game_state.assert_called_once()
    actual_game_state, done_callback, game_points = \
      game_widget.init_from_game_state.call_args.args
    self.assertEqual(PlayerId.ONE, actual_game_state.next_player)
    self.assertEqual(PlayerPair(0, 0), actual_game_state.trick_points)
    self.assertEqual(PlayerPair(0, 3), game_points)

  # TODO(tests): Add a test that checks the end of a Bummerl.

  def test_two_bummerl_with_random_players(self):
    class TestScoreViewWithBummerlCount:
      # pylint: disable=too-few-public-methods

      def __init__(self, done_callback):
        self._num_bummerls = 0
        self._done_callback = done_callback

      def score_view_delegate(self, score_history, dismiss_callback):
        total_game_points = PlayerPair(0, 0)
        for _, game_points in score_history:
          total_game_points.one += game_points.one
          total_game_points.two += game_points.two
        if total_game_points.one > 6 or total_game_points.two > 6:
          self._num_bummerls += 1
        if self._num_bummerls < 2:
          dismiss_callback()
        else:
          self._done_callback()

    game_widget = GameWidget()
    players = PlayerPair(RandomPlayer(), RandomPlayer())
    two_bummerls_played = Mock()
    score_view = TestScoreViewWithBummerlCount(two_bummerls_played)

    self.render(game_widget)

    # noinspection PyTypeChecker
    game_controller = GameController(game_widget, players,
                                     score_view.score_view_delegate, 0)
    game_controller.start()
    self.wait_for_mock_callback(two_bummerls_played, timeout_seconds=60)
