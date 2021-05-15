#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from textwrap import dedent

from kivy.base import runTouchApp
from kivy.lang import Builder
from kivy.uix.widget import Widget

# Based on this article:
# http://robertour.com/2013/10/02/easy-way-debugging-kivy-interfaces/
Builder.load_string(dedent("""
  <DebuggableWidget>:
    debug_text: ""
    color_rgba: 1, 1, 1, 1
    background_rgba: 0, 0, 0, 0
    canvas.before:
      Color:
        rgba: root.background_rgba
      Rectangle:
        pos: self.pos
        size: self.size
    canvas.after:
      Color:
        rgba: root.color_rgba
      Line:
        rectangle: self.x + 1, self.y + 1, self.width - 2, self.height - 2
        dash_offset: 5
        dash_length: 5
    Label:
      text: root.debug_text
      halign: "center"
      valign: "center"
      color: root.color_rgba
      center: root.center
      text_size: root.size
      font_size: root.height / 10
  """))


# TODO(debug): Make this class a no-op in case debug is not enabled.
# TODO(tests): Maybe write some tests for this.
class DebuggableWidget(Widget):
  """
  Allows a widget to be debugged by setting a background color, drawing a dashed
  line around the widget and displaying a debug message in the middle of the
  widget.
  """


if __name__ == "__main__":
  # pylint: disable=attribute-defined-outside-init
  debuggable_widget = DebuggableWidget()
  debuggable_widget.debug_text = "DebugText"
  debuggable_widget.color_rgba = 1, 0, 0, 1
  debuggable_widget.background_rgba = 0, 0.3, 0, 1
  runTouchApp(debuggable_widget)
