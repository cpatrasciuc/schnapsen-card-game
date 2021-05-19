#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from typing import List, Optional, Tuple

from kivy.base import runTouchApp
from kivy.uix.layout import Layout
from kivy.uix.widget import Widget

from ui.debuggable_widget import DebuggableWidget


class CardSlotsLayout(Layout, DebuggableWidget):
  """
  A layout that displays the children widgets (cards) on a grid and maximizes
  the area used while keeping the aspect ratio of the children constant.
  """

  # pylint: disable=too-many-instance-attributes

  def __init__(self, aspect_ratio: float = 24 / 37, rows: int = 1,
               cols: int = 1, align_top: bool = False, spacing: float = 0.0,
               **kwargs):
    """
    Instantiates a new CardSlotsLayout.
    :param aspect_ratio: The aspect ratio that is enforced on the children (
    aspect_ratio = width / height).
    :param rows: Number of rows.
    :param cols: Number of columns.
    :param align_top: If this is True and the layout cannot use its entire
    height to display the children, it will display them starting from the top
    border and leaving the unused area at the bottom of the layout. If this is
    False, the unused area will be at the top.
    :param spacing: The spacing used between children, in percentages of
    children size. A spacing of 0.5 means the children will leave half their
    width/height between them. A spacing of -0.5 means the children will overlap
    on half of their width/height.
    :param kwargs: Parameters to forward to the base class' constructor.
    """
    # pylint: disable=too-many-arguments
    super().__init__(**kwargs)
    self._rows = rows
    self._cols = cols
    self._ratio = aspect_ratio
    self._align_top = align_top
    self._spacing = spacing
    self._slots: List[List[Optional[Widget]]] = [[None] * cols for _ in
                                                 range(rows)]
    self._card_size = 0, 0

    # Trigger a call to do_layout() whenever position, size or children change.
    self.fbind('children', self._trigger_layout)
    self.fbind('pos', self._trigger_layout)
    self.fbind('pos_hint', self._trigger_layout)
    self.fbind('size_hint', self._trigger_layout)
    self.fbind('size', self._trigger_layout)

  @property
  def rows(self) -> int:
    return self._rows

  @property
  def cols(self) -> int:
    return self._cols

  def add_card(self, widget: Widget, row: int, col: int) -> None:
    """
    Adds a widget to the slot specified by row and col. The slot must be empty
    (i.e., not already occupied by another widget).
    """
    assert row < self._rows and col < self._cols, (row, col)
    assert self._slots[row][col] is None, (self._slots[row][col], row, col)
    self._slots[row][col] = widget
    super().add_widget(widget)

  def remove_card(self, row: int, col: int) -> Optional[Widget]:
    """
    Removes a widget from the slot specified by row and col. If the slot is not
    empty, it returns the widget that got removed.
    """
    assert row < self._rows and col < self._cols, (row, col)
    widget = self._slots[row][col]
    if widget is not None:
      super().remove_widget(widget)
      self._slots[row][col] = None
    return widget

  def _update_card_size(self) -> None:
    slot_height = self.height / ((1 + self._spacing) * (self._rows - 1) + 1)
    width_if_height_is_fixed = slot_height * self._ratio
    if (width_if_height_is_fixed * (1 + self._spacing) * (
        self._cols - 1) + width_if_height_is_fixed) <= self.width:
      width = width_if_height_is_fixed
      height = slot_height
    else:
      width = self.width / ((1 + self._spacing) * (self._cols - 1) + 1)
      height = width / self._ratio
    assert abs(width / height - self._ratio) < 1e-10
    self._card_size = int(width), int(height)

  @property
  def card_size(self) -> Tuple[int, int]:
    return self._card_size

  def _get_local_card_pos(self, row, col):
    assert 0 <= row < self._rows and 0 <= col < self._cols, (row, col)
    width, height = self._card_size
    bottom_margin = 0
    if self._align_top:
      bottom_margin = self.height - height * (1 + self._spacing) * (
          self._rows - 1) - height
    return int(col * width * (1 + self._spacing)), int(
      bottom_margin + (self._rows - row - 1) * height * (
          1 + self._spacing))

  def get_card_pos(self, row, col):
    """
    Returns the position of the grid slot specified by row and col, in parent
    coordinates.
    """
    return self.to_parent(*self._get_local_card_pos(row, col), True)

  def do_layout(self, *_):
    """
    This function is called when a layout is called by a trigger. That means
    whenever the position, the size or the children of this layout change.
    """
    self._update_card_size()
    for row in range(self._rows):
      for col in range(self._cols):
        if self._slots[row][col] is None:
          continue
        self._slots[row][col].pos = self.get_card_pos(row, col)
        self._slots[row][col].size = self._card_size


if __name__ == "__main__":
  ROWS = 2
  COLS = 5
  cards_layout = CardSlotsLayout(rows=ROWS, cols=COLS, spacing=-0.25,
                                 align_top=True)
  for _row in range(ROWS):
    for _col in range(COLS):
      label = DebuggableWidget()
      label.debug_text = f"Slot{_row},{_col}"
      cards_layout.add_card(label, _row, _col)
  runTouchApp(cards_layout)
