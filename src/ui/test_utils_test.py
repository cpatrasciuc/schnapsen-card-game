#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from kivy.uix.widget import Widget

from ui.test_utils import get_children_index, UiTestCase, GraphicUnitTest


class TestUtilsTest(UiTestCase):
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

  def test_assert_list_almost_equal(self):
    self.assert_list_almost_equal([10, 20, 30], [11, 19, 30], places=-1)
    self.assert_list_almost_equal([10, 20, 30], [10.1, 19.9, 30.0], places=0)
    with self.assertRaisesRegex(AssertionError, "First diff at index 0"):
      self.assert_list_almost_equal([10, 20, 30], [10.1, 19.9, 30.0], places=1)
    with self.assertRaisesRegex(AssertionError, "First diff at index 1"):
      self.assert_list_almost_equal([10, 20, 30], [10.01, 19.9, 30.0], places=1)

    self.assert_list_almost_equal([10, 20, 30], [11, 19, 30], delta=1)
    self.assert_list_almost_equal([10, 20, 30], [10.1, 19.9, 30.0], delta=0.5)
    with self.assertRaisesRegex(AssertionError, "First diff at index 0"):
      self.assert_list_almost_equal([10, 20, 30], [10.1, 19.9, 30.0],
                                    delta=0.09)
    with self.assertRaisesRegex(AssertionError, "First diff at index 1"):
      self.assert_list_almost_equal([10, 20, 30], [10.01, 19.9, 30.0],
                                    delta=0.09)

    with self.assertRaisesRegex(AssertionError, "Different lengths"):
      self.assert_list_almost_equal([10, 20, 30], [10, 20])


class GraphicUnitTestTest(GraphicUnitTest):
  def test_assert_almost_equal_pixels(self):
    self.assert_pixels_almost_equal([30, 50], [31, 49])
    self.assert_pixels_almost_equal([30, 50], [31, 49], places=-1)
    with self.assertRaisesRegex(AssertionError, "First diff at index 0"):
      self.assert_pixels_almost_equal([30, 50], [31, 49], delta=0.9)
    with self.assertRaisesRegex(AssertionError, "First diff at index 0"):
      self.assert_pixels_almost_equal([30, 50], [31, 49], places=0)
