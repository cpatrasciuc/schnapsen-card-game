#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import logging
from typing import Optional, Callable

from kivy.base import runTouchApp, EventLoop
from kivy.clock import Clock

from model.bummerl import Bummerl
from model.player_action import PlayerAction, \
  PlayCardAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from ui.computer_player import ComputerPlayer
from ui.game_widget import GameWidget
from ui.player import Player
from ui.score_view import ScoreView, ScoreHistory

ScoreViewCallback = Callable[[ScoreHistory, Callable[[], None]], ScoreView]


class GameController:
  """
  The GameController coordinates the execution flow throughout a game of
  Schnapsen. It takes input from the human player and computer player, updates
  the game state accordingly and notifies the UI about these changes.
  """

  # pylint: disable=too-few-public-methods

  def __init__(
      self, game_widget: GameWidget, players: PlayerPair[Player],
      score_view_callback: ScoreViewCallback = ScoreView.show_score_view,
      computer_action_delay_seconds: int = 1):
    """
    Initializes a new GameController.
    :param game_widget: The UI that will be updated throughout the game.
    :param players: A pair of players that will be asked to perform actions
    throughout the game.
    :param score_view_callback: The function to be used when the GameController
    must show the score view at the end of a game. It receives the ScoreHistory
    as an argument and a callback that the ScoreView should call on dismiss.
    :param: computer_action_delay_seconds: The time in seconds that the
    GameController should wait after the computer completes a trick, so that the
    user can see the card that the computer played.
    """
    self._bummerl: Optional[Bummerl] = None
    self._game_widget = game_widget
    self._players = players
    self._score_view_callback = score_view_callback
    self._wait_seconds = computer_action_delay_seconds

  def start(self, bummerl: Optional[Bummerl] = None) -> None:
    """
    Starts or continues a game of Schnapsen.
    :param bummerl: If this argument is not None, the GameController will
    resume the bummerl. If there exists a current running game in the bummerl
    the GameController will resume it, otherwise it starts a new game in the
    bummerl. If this argument is None, the GameController creates a new bummerl
    and starts a new game in this new bummerl.
    """
    if self._bummerl is None:
      if bummerl is None:
        bummerl = Bummerl()
      self._bummerl = bummerl
    if self._bummerl.game is None:
      self._bummerl.start_game()
    self._game_widget.reset()
    self._game_widget.init_from_game_state(self._bummerl.game.game_state,
                                           self._request_next_action,
                                           self._bummerl.game_points)

  def stop(self):
    self._players.one.cleanup()
    self._players.two.cleanup()
    self._players = None

  def _request_next_action(self) -> None:
    """Requests a new action from the player that must play the next move."""
    # TODO(tests): Add tests for this.
    if self._players is None:
      return
    game_state = self._bummerl.game.game_state
    next_player = game_state.next_player
    # TODO(tests): Add tests for this.
    if self._players[next_player].is_cheater():
      game_view = game_state
    else:
      game_view = game_state.next_player_view()
    logging.info("GameController: Requesting next action for %s", next_player)
    self._players[next_player].request_next_action(game_view,
                                                   self._handle_action_response)

  def _handle_action_response(self, action: PlayerAction) -> None:
    """
    This method is called by the current player once they have decide what is
    the next action they want to play.
    :param action: The action that will be played next.
    """
    logging.info("GameController: Execute action: %s", action)

    game = self._bummerl.game
    game_state = game.game_state
    trick_points = game_state.trick_points

    old_score = trick_points.one, trick_points.two
    game.play_action(action)
    self._game_widget.on_action(action,
                                lambda: self._process_last_action(action,
                                                                  old_score))

  def _process_last_action(self, action, old_score) -> None:
    """
    Performs the last steps in processing a player action. This means updating
    the score and checking whether the current trick is completed. If the trick
    is completed, the GameController notifies the GameWidget to update itself
    accordingly (e.g., move the trick out of the play area, draw new cards).
    :param action: The most recently played action.
    :param old_score: The score before the action was played.
    """
    game_state = self._bummerl.game.game_state
    trick_points = game_state.trick_points

    new_score = trick_points.one, trick_points.two
    if old_score != new_score:
      logging.info("GameController: Score updated: %s", trick_points)
      self._game_widget.on_score_modified(trick_points)

    if isinstance(action, PlayCardAction):
      if game_state.current_trick == PlayerPair(None, None):
        last_trick_winner = game_state.next_player
        last_trick = game_state.won_tricks[last_trick_winner][-1]

        draw_new_cards = False
        total_tricks_played = len(game_state.won_tricks.one) + len(
          game_state.won_tricks.two)
        if not game_state.is_talon_closed and total_tricks_played <= 5:
          draw_new_cards = True

        logging.info(
          "GameController: Trick completed: %s, Winner %s, Draw new cards %s",
          last_trick, last_trick_winner, draw_new_cards)

        # If the computer played the second card in the trick, wait a bit before
        # calling on_trick_completed(), so the user can see what was the card
        # played by the computer.
        Clock.schedule_once(
          lambda _: self._game_widget.on_trick_completed(
            last_trick, last_trick_winner, game_state.cards_in_hand,
            draw_new_cards, self._advance),
          0 if action.player_id == PlayerId.ONE else self._wait_seconds)
        return
    self._advance()

  def _advance(self) -> None:
    """
    If the game is over, it shows the score view. If the game is not over, it
    request a new action from the current player.
    """
    if self._bummerl.game.game_state.is_game_over:
      logging.info("GameController: Game is over")
      self._bummerl.finalize_game()
      if self._bummerl.is_over:
        logging.info("GameController: Bummerl is over")
        logging.info("GameController: %s games played",
                     len(self._bummerl.completed_games))
      self._show_score_view()
    else:
      self._request_next_action()

  def _show_score_view(self) -> None:
    """
    Shows the score view. After the user closes the score view, a new game is
    started. If the current bummerl is over, a new bummerl is started as well.
    """
    score_history = []
    for game in self._bummerl.completed_games:
      score_history.append(
        (game.game_state.trick_points, game.game_state.game_points))
    if self._bummerl.is_over:
      self._bummerl = None
    self._score_view_callback(score_history, self.start)


if __name__ == "__main__":
  EventLoop.ensure_window()
  EventLoop.window.maximize()
  _game_widget = GameWidget()
  _game_widget.padding_pct = 0.01
  _game_widget.size_hint = 1, 1
  _human_player: Player = _game_widget
  _computer_player: Player = ComputerPlayer()
  _players: PlayerPair[Player] = PlayerPair(_human_player, _computer_player)
  _game_controller = GameController(_game_widget, _players)
  Clock.schedule_once(lambda _: _game_controller.start(), 0)
  runTouchApp(_game_widget)
