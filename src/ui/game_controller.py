#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import logging
from typing import Optional

from kivy.base import runTouchApp, EventLoop
from kivy.clock import Clock

from model.bummerl import Bummerl
from model.player_action import PlayerAction, \
  PlayCardAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from ui.game_widget import GameWidget
from ui.player import Player, RandomPlayer
from ui.score_view import ScoreView

DELAY = 1


class GameController:
  def __init__(self, game_widget: GameWidget, players: PlayerPair[Player]):
    self._bummerl: Optional[Bummerl] = None
    self._game_widget = game_widget
    self._players = players

  def start(self, bummerl=None):
    if self._bummerl is None:
      if bummerl is None:
        bummerl = Bummerl(next_dealer=PlayerId.TWO)
      self._bummerl = bummerl
    if self._bummerl.game is None:
      self._bummerl.start_game()
    self._game_widget.init_from_game_state(self._bummerl.game.game_state,
                                           self._bummerl.game_points)
    self.request_next_action()

  def request_next_action(self):
    game_state = self._bummerl.game.game_state
    next_player = game_state.next_player
    logging.info("GameController: Requesting next action for %s", next_player)
    self._players[next_player].request_next_action(game_state,
                                                   self.handle_action_response)

  def handle_action_response(self, action: PlayerAction):
    logging.info("GameController: Execute action: %s", action)

    game = self._bummerl.game
    game_state = game.game_state
    trick_points = game_state.trick_points

    old_score = trick_points.one, trick_points.two
    game.play_action(action)
    self._game_widget.on_action(action)
    Clock.schedule_once(lambda _: self.process_last_action(action, old_score),
                        DELAY)

  def process_last_action(self, action, old_score):
    game = self._bummerl.game
    game_state = game.game_state
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
        if not game.game_state.is_talon_closed and total_tricks_played <= 5:
          draw_new_cards = True

        logging.info(
          "GameController: Trick completed: %s, Winner %s, Draw new cards %s",
          last_trick, last_trick_winner, draw_new_cards)
        self._game_widget.on_trick_completed(last_trick, last_trick_winner,
                                             game_state.cards_in_hand,
                                             draw_new_cards)

    if game.game_state.is_game_over:
      logging.info("GameController: Game is over")
      self._bummerl.finalize_game()
      if self._bummerl.is_over:
        logging.info("GameController: Bummerl is over")
        logging.info("GameController: %s games played",
                     len(self._bummerl.completed_games))
        self.show_score_view()
      else:
        self.show_score_view()
    else:
      self.request_next_action()

  def reset_and_start(self):
    self._game_widget.reset()
    self.start()

  def show_score_view(self):
    score_history = []
    for game in self._bummerl.completed_games:
      score_history.append(
        (game.game_state.trick_points, game.game_state.game_points))
    score_view = ScoreView(score_history)
    if self._bummerl.is_over:
      self._bummerl = None
    score_view.bind(on_dismiss=lambda _: self.reset_and_start())
    score_view.open()


if __name__ == "__main__":
  EventLoop.ensure_window()
  EventLoop.window.maximize()
  _game_widget = GameWidget()
  _game_widget.padding_pct = 0.01
  _game_widget.size_hint = 1, 1
  _game_widget.do_layout()
  _players: PlayerPair[Player] = PlayerPair(_game_widget, RandomPlayer())
  _game_controller = GameController(_game_widget, _players)
  _game_controller.start()
  runTouchApp(_game_widget)
