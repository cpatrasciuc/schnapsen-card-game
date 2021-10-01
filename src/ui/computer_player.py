#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import logging
import multiprocessing
from multiprocessing.connection import Connection
from typing import Type, Tuple, Any, Optional, Callable

from kivy.clock import Clock

from ai.player import Player as AIPlayer
from ai.random_player import RandomPlayer
from model.game_state import GameState
from model.player_action import PlayerAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from ui.player import Player


class ComputerPlayer(Player):
  """
  A Player implementation that runs an AI algorithm to pick the next action to
  be played. It's a wrapper over an ai.player.Player instance. This class runs
  the AIPlayer in-process, which means it will block the UI until the AIPlayer
  returns a PlayerAction.
  """

  def __init__(self, player: Optional[AIPlayer] = None):
    self._player = player or RandomPlayer(PlayerId.TWO)

  def request_next_action(self, game_view: GameState,
                          callback: Callable[[PlayerAction], None],
                          game_points: Optional[
                            PlayerPair[int]] = None) -> None:
    callback(self._player.request_next_action(game_view, game_points))

  def is_cheater(self) -> bool:
    return self._player.cheater


def _player_process(conn: Connection, player_class: Type[AIPlayer],
                    player_args: Tuple[Any]) -> None:  # pragma: no cover
  """
  Used to run an AIPlayer in a separate process.
  See OutOfProcessComputerPlayer.__init__() for more details.
  """
  logging.info("AIProcess: Started")
  player = player_class(*player_args)
  logging.info("AIProcess: Player created successfully: %s", player)
  conn.send(player.cheater)
  while True:
    logging.info("AIProcess: Waiting for a GameView from the UI process...")
    try:
      game_view, game_points = conn.recv()
    except EOFError:
      logging.info("AIProcess: The pipe was closed. Exiting.")
      break
    logging.info("AIProcess: GameView received. Processing...")
    action = player.request_next_action(game_view, game_points)
    logging.info("AIProcess: Sending action (%s) to the UI process", action)
    try:
      conn.send(action)
    except BrokenPipeError:
      logging.info("AIProcess: The pipe was closed. Exiting.")
      break


class OutOfProcessComputerPlayer(Player):
  """
  A Player implementation that runs an AI algorithm to pick the next action to
  be played. It's a wrapper over an ai.player.Player instance. This class runs
  the AI algorithm in a separate process and doesn't block the current process
  (e.g., the UI).
  """

  def __init__(self, player_class: Type[AIPlayer], player_args: Tuple):
    """
    Instantiates a new OutOfProcessComputerPlayer and starts the corresponding
    AIProcess. This process receives the class and constructor arguments for an
    AIPlayer, instantiates the AIPlayer and replies with the value of
    AIPlayer.cheater. Then, in a loop, it waits for GameView objects, calls the
    AIPlayer.request_next_action() on them and replies with the result.
    :param player_class: The class used to instantiate the AIPlayer.
    :param player_args: The arguments to be passed to the AIPlayer constructor.
    """
    super().__init__()
    ui_conn, ai_conn = multiprocessing.Pipe()
    self._conn = ui_conn
    self._ai_process = multiprocessing.Process(target=_player_process,
                                               args=(ai_conn, player_class,
                                                     player_args))
    self._ai_process.name = "AIProcess"
    self._ai_process.start()
    self._cheater = ui_conn.recv()

  def cleanup(self) -> None:
    """Closes the pipe and waits for the AIProcess to terminate."""
    logging.info("OutOfProcess: Closing the pipe to the AIProcess.")
    self._conn.close()
    logging.info("OutOfProcess: Waiting for the AIProcess to finish.")
    self._ai_process.join()

  def request_next_action(self, game_view: GameState,
                          callback: Callable[[PlayerAction], None],
                          game_points: Optional[
                            PlayerPair[int]] = None) -> None:
    """
    Sends the GameView to the AIProcess and schedules an event that checks for a
    reply before the next frame is drawn. One should not send a GameView to the
    AIProcess before a reply for the previous GameView is received.
    """
    self._conn.send((game_view, game_points))
    Clock.schedule_once(lambda *_: self._poll_for_ai_reply(callback))

  def _poll_for_ai_reply(self,
                         callback: Callable[[PlayerAction], None]) -> None:
    """
    Checks if the AIProcess replied with a PlayerAction. If yes, it runs the
    callback received in request_next_action(). If not, schedules a new call
    to this method before the next frame is drawn.
    """
    if self._conn.closed:
      return
    if self._conn.poll():
      callback(self._conn.recv())
    else:
      Clock.schedule_once(lambda *_: self._poll_for_ai_reply(callback))

  def is_cheater(self) -> bool:
    return self._cheater
