#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from kivy.base import EventLoop
from kivy.tests.common import GraphicUnitTest
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget

from ui.card_slots_layout import CardSlotsLayout


class CardSlotsLayoutTest(unittest.TestCase):
  def compute_layout(self, cards_layout: CardSlotsLayout, expected_size=None,
                     expected_pos=None):
    cards_layout.do_layout()
    self.assertEqual(expected_size, cards_layout.card_size)
    pos = [[cards_layout.get_card_pos(row, col) for col in
            range(cards_layout.cols)] for row in range(cards_layout.rows)]
    self.assertEqual(expected_pos, pos)

  def test_one_row(self):
    cards_layout = CardSlotsLayout(aspect_ratio=1 / 3, rows=1, cols=3)
    cards_layout.size = 100, 100
    self.compute_layout(cards_layout, (33, 100), [[(0, 0), (33, 0), (66, 0)]])

    cards_layout = CardSlotsLayout(aspect_ratio=3, rows=1, cols=3)
    cards_layout.size = 100, 100
    self.compute_layout(cards_layout, (33, 11), [[(0, 0), (33, 0), (66, 0)]])

    cards_layout = CardSlotsLayout(aspect_ratio=3, rows=1, cols=3,
                                   align_top=True)
    cards_layout.size = 100, 100
    self.compute_layout(cards_layout, (33, 11), [[(0, 89), (33, 89), (66, 89)]])

  def test_one_column(self):
    cards_layout = CardSlotsLayout(aspect_ratio=1 / 4, rows=3, cols=1)
    cards_layout.size = 100, 100
    self.compute_layout(cards_layout, (8, 33), [[(0, 66)], [(0, 33)], [(0, 0)]])

    cards_layout = CardSlotsLayout(aspect_ratio=4, rows=3, cols=1)
    cards_layout.size = 100, 100
    self.compute_layout(cards_layout, (100, 25),
                        [[(0, 50)], [(0, 25)], [(0, 0)]])

    cards_layout = CardSlotsLayout(aspect_ratio=4, rows=3, cols=1,
                                   align_top=True)
    cards_layout.size = 100, 100
    self.compute_layout(cards_layout, (100, 25),
                        [[(0, 75)], [(0, 50)], [(0, 25)]])

  def test_2x3(self):
    cards_layout = CardSlotsLayout(aspect_ratio=1 / 3, rows=2, cols=3)
    cards_layout.size = 100, 100
    self.compute_layout(cards_layout, (16, 50),
                        [[(0, 50), (16, 50), (32, 50)],
                         [(0, 0), (16, 0), (32, 0)]])

    cards_layout = CardSlotsLayout(aspect_ratio=3, rows=2, cols=3)
    cards_layout.size = 100, 100
    self.compute_layout(cards_layout, (33, 11),
                        [[(0, 11), (33, 11), (66, 11)],
                         [(0, 0), (33, 0), (66, 0)]])

    cards_layout = CardSlotsLayout(aspect_ratio=3, rows=2, cols=3,
                                   align_top=True)
    cards_layout.size = 100, 100
    self.compute_layout(cards_layout, (33, 11),
                        [[(0, 89), (33, 89), (66, 89)],
                         [(0, 78), (33, 78), (66, 78)]])

  def test_spacing(self):
    cards_layout = CardSlotsLayout(aspect_ratio=1 / 2, rows=2, cols=2,
                                   spacing=0.0)
    cards_layout.size = 100, 100
    self.compute_layout(cards_layout, (25, 50),
                        [[(0, 50), (25, 50)], [(0, 0), (25, 0)]])

    cards_layout = CardSlotsLayout(aspect_ratio=1 / 2, rows=2, cols=2,
                                   spacing=0.1)
    cards_layout.size = 100, 100
    self.compute_layout(cards_layout, (23, 47),
                        [[(0, 51), (25, 51)], [(0, 0), (25, 0)]])

    cards_layout = CardSlotsLayout(aspect_ratio=1 / 2, rows=2, cols=2,
                                   spacing=0.5)
    cards_layout.size = 100, 100
    self.compute_layout(cards_layout, (20, 40),
                        [[(0, 60), (30, 60)], [(0, 0), (30, 0)]])

    cards_layout = CardSlotsLayout(aspect_ratio=1 / 2, rows=2, cols=2,
                                   spacing=-0.5)
    cards_layout.size = 100, 100
    self.compute_layout(cards_layout, (33, 66),
                        [[(0, 33), (16, 33)], [(0, 0), (16, 0)]])

  def test_remove_missing_card(self):
    cards_layout = CardSlotsLayout(rows=1, cols=3)
    widget = Widget()
    cards_layout.add_card(widget, 0, 0)
    self.assertIs(widget, cards_layout.remove_card_at(0, 0))
    self.assertIsNone(cards_layout.remove_card_at(0, 0))

  def test_cannot_add_outside_of_the_grid(self):
    cards_layout = CardSlotsLayout(rows=2, cols=3)
    with self.assertRaises(AssertionError):
      cards_layout.add_card(Widget(), 10, 2)
    with self.assertRaises(AssertionError):
      cards_layout.add_card(Widget(), 0, 20)

  def test_cannot_add_on_already_occupied_slot(self):
    cards_layout = CardSlotsLayout(rows=2, cols=3)
    cards_layout.add_card(Widget(), 0, 0)
    with self.assertRaises(AssertionError):
      cards_layout.add_card(Widget(), 0, 0)

  def test_coordinates_are_relative_to_parent(self):
    """
    Checks that the coordinates returned by get_card_pos() do not change even if
    the parent of the CardSlotsLayout moves to a different position.
    """
    cards_layout = CardSlotsLayout(aspect_ratio=1 / 3, rows=1, cols=3)
    cards_layout.size = 100, 100

    parent = FloatLayout()
    parent.add_widget(cards_layout)
    parent.pos = 0, 0
    parent.do_layout()
    self.compute_layout(cards_layout, (33, 100), [[(0, 0), (33, 0), (66, 0)]])

    parent.pos = 50, 50
    parent.do_layout()
    self.compute_layout(cards_layout, (33, 100), [[(0, 0), (33, 0), (66, 0)]])

  def test_first_free_slot(self):
    cards_layout = CardSlotsLayout(rows=2, cols=3)
    self.assertEqual((0, 0), cards_layout.first_free_slot)
    cards_layout.add_card(Widget(), 0, 1)
    self.assertEqual((0, 0), cards_layout.first_free_slot)
    cards_layout.add_card(Widget(), 0, 0)
    self.assertEqual((0, 2), cards_layout.first_free_slot)
    cards_layout.add_card(Widget(), 0, 2)
    self.assertEqual((1, 0), cards_layout.first_free_slot)
    cards_layout.remove_card_at(0, 1)
    self.assertEqual((0, 1), cards_layout.first_free_slot)
    cards_layout.add_card(Widget(), 0, 1)
    cards_layout.add_card(Widget(), 1, 0)
    cards_layout.add_card(Widget(), 1, 1)
    cards_layout.add_card(Widget(), 1, 2)
    self.assertEqual((None, None), cards_layout.first_free_slot)

  def test_add_card_at_row_col(self):
    cards_layout = CardSlotsLayout(rows=2, cols=3)
    with self.assertRaises(AssertionError):
      cards_layout.add_card(Widget(), None, 0)
    with self.assertRaises(AssertionError):
      cards_layout.add_card(Widget(), 0, None)
    widget = Widget()
    cards_layout.add_card(widget, 1, 1)
    for _ in range(5):
      cards_layout.add_card(Widget())
    with self.assertRaisesRegex(AssertionError, "Slot not empty"):
      cards_layout.add_card(Widget(), 1, 0)
    with self.assertRaisesRegex(AssertionError, "No empty slot"):
      cards_layout.add_card(Widget())
    self.assertIs(widget, cards_layout.remove_card_at(1, 1))
    cards_layout.add_card(Widget())
    with self.assertRaisesRegex(AssertionError, "Out of bounds"):
      cards_layout.add_card(Widget(), 10, 10)


class CardSlotsLayoutGraphicTest(GraphicUnitTest):
  def test_children_are_resized_and_repositioned(self):
    cards_layout = CardSlotsLayout(aspect_ratio=1 / 3, rows=1, cols=3)
    cards_layout.size = 100, 100
    cards_layout.size_hint = None, None

    EventLoop.ensure_window()
    self.render(cards_layout)

    # Create a widget at random coordinates with a random size.
    widget = Widget()
    widget.size = 123, 456
    widget.pos = 78, 90
    self.assertEqual([123, 456], widget.size)
    self.assertEqual([78, 90], widget.pos)

    # Add the widget to the CardSlotsLayout and check that it got resized and
    # correctly positioned.
    cards_layout.add_card(widget, 0, 1)
    self.advance_frames(1)
    self.assertEqual([33, 0], widget.pos)
    self.assertEqual([33, 100], widget.size)

    # Resize the CardSlotsLayout and check that the widget got resized and
    # repositioned accordingly.
    cards_layout.size = 900, 900
    self.advance_frames(1)
    self.assertEqual([300, 0], widget.pos)
    self.assertEqual([300, 900], widget.size)

    # Move the CardSlotsLayout and check that the widget got resized and
    # repositioned accordingly.
    cards_layout.pos = 10, 20
    self.advance_frames(1)
    self.assertEqual([10, 20], cards_layout.pos)
    self.assertEqual([310, 20], widget.pos)
    self.assertEqual([300, 900], widget.size)

    # Remove the widget from the CardSlotsLayout, move the CardSlotsLayout and
    # check that the size and position of the widget are not affected.
    self.assertIs(widget, cards_layout.remove_card_at(0, 1))
    cards_layout.pos = 30, 40
    self.advance_frames(1)
    self.assertEqual([310, 20], widget.pos)
    self.assertEqual([300, 900], widget.size)
