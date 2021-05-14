#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window

from uidemo.game_widget import GameWidget


class SchnapsenApp(App):
  def build(self):
    game_widget = GameWidget()
    game_widget.size = 1000, 800
    Clock.schedule_once(lambda x: game_widget.init_cards(), 1)

    def trigger_layout():
      game_widget.trigger_layout()

    Window.on_maximize = trigger_layout
    Window.on_restore = trigger_layout
    return game_widget


if __name__ == "__main__":
  SchnapsenApp().run()
