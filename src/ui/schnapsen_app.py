#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from pathlib import Path
from typing import Optional

from kivy.app import App

from ai.cython_mcts_player.player import CythonMctsPlayer
from ai.mcts_player_options import mcts_player_options_v1
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from ui.computer_player import OutOfProcessComputerPlayer
from ui.game_controller import GameController
from ui.game_options import GameOptions
from ui.game_widget import GameWidget
from ui.player import Player

__version__ = '1.0'


class SchnapsenApp(App):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._game_widget: Optional[GameWidget] = None
    self._game_controller: Optional[GameController] = None
    self._game_options: Optional[GameOptions] = None
    self.title = f"Schnapsen Card Game :: v{__version__}"
    # TODO(ui): Set self.icon.

  def build(self):
    self._game_options = GameOptions(computer_cards_visible=True)
    self._game_widget = GameWidget(game_options=self._game_options)
    self._game_widget.padding_pct = 0.01
    self._game_widget.size_hint = 1, 1
    human_player: Player = self._game_widget
    computer_player: Player = OutOfProcessComputerPlayer(
      CythonMctsPlayer, (PlayerId.TWO, False, mcts_player_options_v1()))
    players: PlayerPair[Player] = PlayerPair(human_player, computer_player)
    auto_save_folder = str(Path(__file__).parent.parent.absolute())
    self._game_controller = GameController(self._game_widget, players,
                                           auto_save_folder=auto_save_folder)
    return self._game_widget

  def on_start(self):
    self._game_controller.start()

  def on_stop(self):
    self._game_controller.stop()


if __name__ == '__main__':
  SchnapsenApp().run()
