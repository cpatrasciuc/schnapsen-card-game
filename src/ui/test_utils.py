#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from typing import List, Optional

from kivy.base import EventLoop
from kivy.core.window import Window
from kivy.tests.common import GraphicUnitTest as BaseGraphicUnitTest
from kivy.uix.widget import Widget


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
  def assert_list_almost_equal(self, first: List, second: List,
                               places: int = 7, msg: str = ""):
    self.assertEqual(len(first), len(second), msg=msg + "\nDifferent lengths.")
    for i, item in enumerate(first):
      self.assertAlmostEqual(item, second[i],
                             msg=msg + f"\nFirst diff at index {i}.",
                             places=places)

  def assert_is_drawn_on_top(self, top: Widget, bottom: Widget):
    """
    Checks that the widget `top` is drawn on top of the widget `bottom`, in
    terms of z-order. The two widgets must have the same parent.
    """
    self.assertIs(top.parent, bottom.parent)
    self.assertGreater(get_children_index(top.parent, top),
                       get_children_index(bottom.parent, bottom))


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
