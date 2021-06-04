#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import time
import unittest
from typing import Optional, Sequence
from unittest.mock import Mock

from kivy.base import EventLoop
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.tests.common import GraphicUnitTest as BaseGraphicUnitTest
from kivy.uix.widget import Widget

from ui.card_widget import CardWidget


def get_children_index(parent: Widget, child: Widget) -> Optional[int]:
  """
  Returns the index of child in the list of parent's children widgets, in the
  order in which the widgets are drawn. Index 0 is the parent itself; the parent
  is the first widget to be drawn (in z-order).
  """
  for index, widget in enumerate(parent.walk(restrict=True, loopback=False)):
    if widget is child:
      return index
  return None


class UiTestCase(unittest.TestCase):
  def assert_list_almost_equal(self, first: Sequence, second: Sequence,
                               **kwargs):
    msg = kwargs.get("msg", "")
    kwargs.pop("msg", None)
    self.assertEqual(len(first), len(second), msg=msg + "\nDifferent lengths.")
    for i, item in enumerate(first):
      self.assertAlmostEqual(item, second[i],
                             msg=msg + f"\nFirst diff at index {i}.",
                             **kwargs)

  def assert_is_drawn_on_top(self, top: Widget, bottom: Widget):
    """
    Checks that the widget `top` is drawn on top of the widget `bottom`, in
    terms of z-order. The two widgets must have the same parent.
    """
    self.assertIs(top.parent, bottom.parent)
    self.assertGreater(get_children_index(top.parent, top),
                       get_children_index(bottom.parent, bottom))

  def assert_do_translation(self, expected: bool, card: CardWidget) -> None:
    self.assertEqual(expected, card.do_translation_x)
    self.assertEqual(expected, card.do_translation_y)


class GraphicUnitTest(BaseGraphicUnitTest, UiTestCase):
  """
  Extends kivy.tests.common.GraphicUnitTest and makes sure that the window size
  is reset for each new test.
  """

  def setUp(self):
    super().setUp()
    EventLoop.ensure_window()
    EventLoop.window.size = 320, 240
    self._window = EventLoop.window

  @property
  def window(self) -> Window:
    return self._window

  def tearDown(self, fake=False):
    for child in self.window.children:
      self.window.remove_widget(child)
    return super().tearDown(fake)

  def assert_pixels_almost_equal(self, first: Sequence, second: Sequence,
                                 **kwargs):
    if "delta" not in kwargs and "places" not in kwargs:
      kwargs["delta"] = dp(1)
    self.assert_list_almost_equal(first, second, **kwargs)

  def wait_for_mock_callback(self, mock_callback: Mock,
                             timeout_seconds: int = 5):
    start_seconds = current_seconds = time.time()
    while not mock_callback.called and \
        current_seconds - start_seconds < timeout_seconds:
      self.advance_frames(1)
      current_seconds = time.time()
    if current_seconds - start_seconds >= timeout_seconds:
      self.fail(
        f"The callback was not called within {timeout_seconds} second(s)")
