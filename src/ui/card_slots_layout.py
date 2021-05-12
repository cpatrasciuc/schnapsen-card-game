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
               spacing=0.0, debug=False, **kwargs):
    super().__init__(**kwargs)
    self._ratio = aspect_ratio
    self._rows = rows
    self._cols = cols
    self._align_top = align_top
    self._slots: List[Optional[Widget]] = [None] * (rows * cols)
    self._debug = debug
    self._spacing = spacing
    if self._debug:
      for line in range(self._rows):
        for col in range(self._cols):
          label = DebuggableWidget()
          label.debug_text = f"Slot{line},{col}"
          self._slots[line * self._cols + col] = label
          self.add_widget(label)

  def get_card_size(self):
    slot_height = self.height / ((1 + self._spacing) * (self._rows - 1) + 1)
    width_if_height_is_fixed = slot_height * self._ratio
    if (width_if_height_is_fixed * (1 + self._spacing) * (
        self._cols - 1) + width_if_height_is_fixed) <= self.width:
      width = width_if_height_is_fixed
      height = slot_height
    else:
      width = self.width / ((1 + self._spacing) * (self._cols - 1) + 1)
      height = width / self._ratio
    return width, height

  def get_relative_pos(self, row, col):
    assert 0 <= row < self._rows and 0 <= col < self._cols, (row, col)
    width, height = self.get_card_size()
    missing_top = self.height - height * (1 + self._spacing) * (
        self._rows - 1) - height if self._align_top else 0
    return (col * width * (1 + self._spacing),
            missing_top + (self._rows - row - 1) * height * (1 + self._spacing))

  def do_layout(self, *args, **kwargs):
    card_size = self.get_card_size()
    for line in range(self._rows):
      for col in range(self._cols):
        if self._slots[line * self._cols + col] is None:
          continue
        rel_x, rel_y = self.get_relative_pos(line, col)
        self._slots[
          line * self._cols + col].pos = self.x + rel_x, self.y + rel_y
        self._slots[line * self._cols + col].size = card_size


if __name__ == "__main__":
  t = CardSlotsLayout(rows=2, cols=5, spacing=-0.25, debug=True, align_top=True)
  t.debug_text = "blabla"
  runTouchApp(t)
