#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.
from typing import List, Optional

from kivy.base import runTouchApp
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget

from ui.debuggable_widget import DebuggableWidget

Builder.load_string("""
<TricksWidget>:
  size_hint: 1, 1
""")


class CardSlotsLayout(FloatLayout, DebuggableWidget):
  def __init__(self, aspect_ratio=24.0 / 37, rows=1, cols=1, align_top=False,
               debug=False, **kwargs):
    super().__init__(**kwargs)
    self._ratio = aspect_ratio
    self._rows = rows
    self._cols = cols
    self._align_top = align_top
    self._slots: List[Optional[Widget]] = [None] * (rows * cols)
    self._debug = debug
    if self._debug:
      for line in range(self._rows):
        for col in range(self._cols):
          label = DebuggableWidget()
          label.debug_text = f"Slot{line},{col}"
          self._slots[line * self._cols + col] = label
          self.add_widget(label)

  def get_card_size(self):
    width_if_height_is_fixed = self.height / float(self._rows) * self._ratio
    if width_if_height_is_fixed * self._cols <= self.width:
      width = width_if_height_is_fixed
      height = self.height / self._rows
    else:
      width = self.width / self._cols
      height = width / self._ratio
    return width, height

  def get_relative_pos(self, row, col):
    assert 0 <= row < self._rows and 0 <= col < self._cols, (row, col)
    width, height = self.get_card_size()
    missing_top = self.height - height * self._rows if self._align_top else 0
    return col * width, missing_top + (self._rows - row - 1) * height

  def do_layout(self, *args, **kwargs):
    for i, slot in enumerate(self._slots):
      if slot is None:
        continue
      rel_x, rel_y = self.get_relative_pos(i // self._cols, i % self._cols)
      slot.pos = self.x + rel_x, self.y + rel_y
      slot.size = self.get_card_size()


if __name__ == "__main__":
  t = CardSlotsLayout(rows=1, cols=5, debug=True)
  t.debug_text = "blabla"
  runTouchApp(t)
