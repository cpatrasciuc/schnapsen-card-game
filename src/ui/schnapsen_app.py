#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from typing import Optional

from kivy.app import App

from model.player_pair import PlayerPair
from ui.game_controller import GameController
from ui.game_options import GameOptions
from ui.game_widget import GameWidget
from ui.player import Player, ComputerPlayer

__version__ = '0.1'


class SchnapsenApp(App):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._game_widget: Optional[GameWidget] = None
    self._game_controller: Optional[GameController] = None
    self._game_options: Optional[GameOptions] = None
    self.title = f"Schnapsen Card Game :: v{__version__}"
    # TODO(ui): Set self.icon.

  def build(self):
    self._game_options = GameOptions()
    self._game_widget = GameWidget(game_options=self._game_options)
    self._game_widget.padding_pct = 0.01
    self._game_widget.size_hint = 1, 1
    human_player: Player = self._game_widget
    computer_player: Player = ComputerPlayer()
    players: PlayerPair[Player] = PlayerPair(human_player, computer_player)
    self._game_controller = GameController(self._game_widget, players)
    return self._game_widget

  def on_start(self):
    self._game_controller.start()


if __name__ == '__main__':
  SchnapsenApp().run()
