#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.
from kivy.base import runTouchApp
from kivy.uix.floatlayout import FloatLayout

from uidemo.debuggable_widget import DebuggableWidget


class TalonWidget(FloatLayout, DebuggableWidget):
  def __init__(self, aspect_ratio=24 / 37, debug=False, **kwargs):
    super().__init__(**kwargs)
    self._ratio = aspect_ratio
    self._debug = debug
    if self._debug:
      self._trump_card = DebuggableWidget()
      self._trump_card.debug_text = "Trump card     "
      self.add_widget(self._trump_card)
      self._talon = DebuggableWidget()
      self._talon.debug_text = "Talon"
      self.add_widget(self._talon)

  def get_talon_size(self):
    width_if_using_height = self.height * self._ratio + self.height / 2.0
    if self.width > width_if_using_height:
      height = self.height
    else:
      height = 2 * self.width / (2.0 * self._ratio + 1.0)
    return height * self._ratio, height

  def get_talon_pos(self):
    _, height = self.get_talon_size()
    return self.x + self.width / 2.0, self.y + (self.height - height) / 2.0

  def get_trump_card_size(self):
    width, height = self.get_talon_size()
    return height, width

  def get_trump_card_pos(self):
    width, height = self.get_trump_card_size()
    return self.x + self.width / 2.0 - width / 2.0, self.y + (
        self.height - height) / 2.0

  def do_layout(self, *largs, **kwargs):
    if self._debug:
      self._talon.size = self.get_talon_size()
      self._talon.pos = self.get_talon_pos()
      self._trump_card.size = self.get_trump_card_size()
      self._trump_card.pos = self.get_trump_card_pos()


if __name__ == "__main__":
  t = TalonWidget(debug=False)
  runTouchApp(t)
