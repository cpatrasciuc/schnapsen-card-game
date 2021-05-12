#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.
from kivy.base import runTouchApp
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.widget import Widget

Builder.load_string("""
<DebuggableWidget>:
  canvas:
    Color:
      # TODO: Make this dynamic.
      rgba: 1, 1, 1, 1
    Line:
      rectangle: self.x + 1, self.y + 1, self.width - 1, self.height - 1
      dash_offset: 5
      dash_length: 5
  Label:
    text: self.parent.debug_text
    center: self.parent.center
    text_size: self.parent.size
    font_size: root.height / 10
  """)


class DebuggableWidget(Widget):
  debug_text = StringProperty()
  pass


if __name__ == "__main__":
  t = DebuggableWidget()
  t.debug_text = "blabla"
  runTouchApp(t)
