#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from kivy.uix.widget import Widget

from ui.test_utils import get_children_index


class TestUtilsTest(unittest.TestCase):
  def test_get_children_index(self):
    parent = Widget()
    child_1 = Widget()
    parent.add_widget(child_1)
    child_2 = Widget()
    parent.add_widget(child_2)
    child_3 = Widget()
    parent.add_widget(child_3)
    self.assertEqual(0, get_children_index(parent, parent))
    self.assertEqual(1, get_children_index(parent, child_1))
    self.assertEqual(2, get_children_index(parent, child_2))
    self.assertEqual(3, get_children_index(parent, child_3))
    self.assertIsNone(get_children_index(parent, Widget()))
    self.assertIsNone(get_children_index(child_2, parent))
    parent.remove_widget(child_1)
    self.assertEqual(0, get_children_index(parent, parent))
    self.assertIsNone(get_children_index(parent, child_1))
    self.assertEqual(1, get_children_index(parent, child_2))
    self.assertEqual(2, get_children_index(parent, child_3))
