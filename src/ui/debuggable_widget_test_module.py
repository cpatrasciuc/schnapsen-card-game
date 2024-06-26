#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

"""
Test module used by DebuggableWidgetTest.
"""

# pylint: disable=wrong-import-position

import os
import sys

from kivy.base import stopTouchApp, runTouchApp
from kivy.clock import Clock

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ui.debuggable_widget import DebuggableWidget


def main():
  config = "DEBUG" if __debug__ else "RELEASE"

  debuggable_widget = DebuggableWidget()

  # We cannot use asserts here since we will run this with -O in tests.
  for attribute in ["debug_text", "color_rgba", "background_rgba"]:
    if hasattr(debuggable_widget, attribute) != __debug__:
      negation = "not " if __debug__ else ""
      raise AssertionError(
        f"{attribute} should {negation}be present in {config} mode.")

  # Test that code that uses DebuggableWidgets does not crash in RELEASE mode.
  debuggable_widget.debug_text = "DebugText"
  debuggable_widget.color_rgba = 1, 0, 0, 1
  debuggable_widget.background_rgba = 0, 0.3, 0, 1

  Clock.schedule_once(lambda _: stopTouchApp(), 1)
  runTouchApp(debuggable_widget)
  print("SUCCESS")


if __name__ == "__main__":
  main()
