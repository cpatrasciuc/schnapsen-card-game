#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.
from kivy.uix.floatlayout import FloatLayout

from ui.card_slots_layout import CardSlotsLayout
from ui.talon_widget import TalonWidget


class GameWidget(FloatLayout):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)

    tricks_top = CardSlotsLayout(rows=2, cols=8, debug=True, spacing=-0.2,
                                 align_top=True)
    tricks_top.size_hint = 1, 1
    tricks_bot = CardSlotsLayout(rows=2, cols=8, debug=True, spacing=-0.2,
                                 align_top=True)
    tricks_bot.size_hint = 1, 1
    self.ids.computer_tricks.add_widget(tricks_top)
    self.ids.player_tricks.add_widget(tricks_bot)

    cards_bot = CardSlotsLayout(rows=1, cols=5, debug=True, spacing=0.1,
                                align_top=True)
    tricks_bot.size_hint = 1, 1
    self.ids.player_cards_box.add_widget(cards_bot)

    talon = TalonWidget(debug=True)
    talon.debug_text = "TALON"
    self.ids.talon.add_widget(talon)

    cards_top = CardSlotsLayout(aspect_ratio=24 / 37 / 0.1 * 0.35, rows=1,
                                cols=5, debug=True, spacing=0.1, align_top=True)
    cards_top.size_hint = 1, 1
    self.ids.computer_cards_box.add_widget(cards_top)

  def do_layout(self, *args, **kwargs):
    self.ids.computer_tricks.height = 0.25 * self.height
    self.ids.player_tricks.height = self.ids.computer_tricks.height
    self.ids.player_tricks.y = 0.10 * self.height
    self.ids.fill_area.height = 0.10 * self.height
    self.ids.talon.height = 0.3 * self.height
    self.ids.buttons.height = self.height - self.ids.computer_tricks.height \
                              - self.ids.player_tricks.height \
                              - self.ids.talon.height \
                              - self.ids.fill_area.height

    # Max width for talon
    width, _ = self.ids.computer_tricks.children[0].get_card_size()
    rel_x, _ = self.ids.computer_tricks.children[0].get_relative_pos(0, 7)
    self.ids.talon.width = rel_x + width
    super().do_layout(*args, **kwargs)

  def trigger_layout(self):
    self._trigger_layout()
