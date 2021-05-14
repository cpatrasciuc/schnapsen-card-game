#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from kivy.base import runTouchApp
from kivy.lang import Builder
from kivy.uix.scatter import Scatter

Builder.load_string("""
<CardWidget>:
  card_name: ""
  visible: True
  color: 1, 1, 1, 1
  canvas:
    Color:
      rgba: 1, 1, 1, 1
    RoundedRectangle:
      size: self.size
      radius: 10, 
    Color:
      # TODO: Make this dynamic.
      rgba: root.color
    RoundedRectangle:
      #pos: self.pos
      pos: 1, 1
      size: self.width - 2, self.height - 2
      radius: 10,
    Color:
      rgba: 1, 1, 1, 1
    Line:
      rectangle: self.width * 0.1, self.width * 0.1, self.width * 0.8, self.height - self.width * 0.2
  Label:
    text: self.parent.card_name
    halign: "center"
    #center: root.center
    color: "red"
    font_size: root.height / 10
    family_name: "Serif"
  """)


class CardWidget(Scatter):
  def __init__(self, aspect_ratio=24 / 37, **kwargs):
    super().__init__(**kwargs)
    self.moving = False
    self._ratio = aspect_ratio
    self.width = self.height * self._ratio
    self.size_hint = None, None

  def on_size(self, obj, size):
    assert abs(size[0] / size[1] - self._ratio) <= 1e-10, (
      size[0] / size[1], self._ratio)
    self.children[0].center = self.width / 2, self.height / 2

  # def on_touch_up(self, touch):
  #   super().on_touch_up(touch)
  #   self.moving = False

  def set_visible(self, visible):
    self.visible = visible
    self.color = [1, 1, 1, 1] if self.visible else [0.5, 0, 0, 1]
    self.children[0].text = self.card_name if self.visible else ""


if __name__ == "__main__":
  t = CardWidget()
  t.size = 240, 370
  t.card_name = "CardName"
  t.set_visible(False)
  runTouchApp(t)
