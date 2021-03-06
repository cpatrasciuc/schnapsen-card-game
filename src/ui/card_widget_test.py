#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from unittest.mock import Mock

from kivy.tests.common import UnitTestTouch
from kivy.uix.floatlayout import FloatLayout

from model.card import Card
from model.card_value import CardValue
from model.suit import Suit
from ui.card_widget import CardWidget
from ui.test_utils import GraphicUnitTest, UiTestCase


class CardWidgetTest(UiTestCase):
  def test_create_widgets_for_all_cards(self):
    card_dict = CardWidget.create_widgets_for_all_cards()
    self.assertEqual(20, len(card_dict.keys()))
    for card, card_widget in card_dict.items():
      self.assertEqual(card, card_widget.card)

  def test_aspect_ratio_is_set_in_constructor(self):
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=0.5)
    self.assertEqual([50, 100], card_widget.children[0].size)
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE),
                             aspect_ratio=0.25)
    self.assertEqual([25, 100], card_widget.children[0].size)

  def test_aspect_ratio_is_enforced(self):
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=0.5)
    card_widget.size = 10, 20
    card_widget.size = 25, 50
    card_widget.size = 26, 50
    card_widget.size = 24, 50
    with self.assertRaisesRegex(AssertionError, r"\(\[23, 50\], 0.5\)"):
      card_widget.size = 23, 50
    with self.assertRaisesRegex(AssertionError, r"\(\[27, 50\], 0.5\)"):
      card_widget.size = 27, 50
    card_widget.check_aspect_ratio(False)
    card_widget.size = 23, 50
    card_widget.size = 27, 50

  def test_visibility(self):
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=0.5)
    self.assertTrue(card_widget.visible)
    card_front_filename = card_widget.children[0].source
    card_widget.visible = False
    self.assertFalse(card_widget.visible)
    card_back_filename = card_widget.children[0].source
    self.assertNotEqual(card_front_filename, card_back_filename)
    card_widget.visible = True
    self.assertTrue(card_widget.visible)
    self.assertEqual(card_front_filename, card_widget.children[0].source)

  def test_grayed_out(self):
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=0.5)
    self.assertFalse(card_widget.grayed_out)
    self.assertEqual(1.0, card_widget.opacity)
    card_widget.grayed_out = False
    self.assertFalse(card_widget.grayed_out)
    self.assertEqual(1.0, card_widget.opacity)
    card_widget.grayed_out = True
    self.assertTrue(card_widget.grayed_out)
    self.assertEqual(0.5, card_widget.opacity)
    card_widget.grayed_out = True
    self.assertTrue(card_widget.grayed_out)
    self.assertEqual(0.5, card_widget.opacity)
    card_widget.grayed_out = False
    self.assertFalse(card_widget.grayed_out)
    self.assertEqual(1.0, card_widget.opacity)

  def test_shadow(self):
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=0.5)
    self.assertTrue(card_widget.shadow)
    card_widget.shadow = 0
    self.assertFalse(card_widget.shadow)
    # TODO(tests): Use Widget.export_as_image() and compare the two images.


class CardWidgetGraphicTest(GraphicUnitTest):
  def test_dragging_a_card_with_the_mouse(self):
    # pylint: disable=too-many-statements
    window = self.window

    on_card_moved_handler = Mock()

    # Place the card in the center of the window.
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=0.5,
                             do_translation=True)
    min_dimension = min(window.width, window.height)
    card_widget.size = min_dimension / 4, min_dimension / 2
    window_center = window.width / 2, window.height / 2
    card_widget.center = window_center
    card_widget.bind(on_card_moved=on_card_moved_handler)

    # Place a second card under the first card. Only the first one will be moved
    # and it will be the only one triggering the on_card_moved event.
    another_card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE),
                                     aspect_ratio=0.5)
    another_card_widget.size = card_widget.size
    another_card_widget.center = card_widget.center
    another_card_widget.bind(on_card_moved=on_card_moved_handler)

    float_layout = FloatLayout()
    float_layout.add_widget(another_card_widget)
    float_layout.add_widget(card_widget)
    self.render(float_layout)

    # Touch down on the card, nothing happens to the card.
    touch = UnitTestTouch(*card_widget.center)
    touch.touch_down()
    self.assertEqual(window_center, card_widget.center)
    on_card_moved_handler.assert_not_called()

    # Drag in a random direction, check that the card moved accordingly.
    new_position = window.width / 3, window.height / 3
    touch.touch_move(*new_position)
    self.assertAlmostEqual(new_position[0], card_widget.center_x)
    self.assertAlmostEqual(new_position[1], card_widget.center_y)
    on_card_moved_handler.assert_not_called()

    # Drag in another random direction, check that the card moved accordingly.
    new_position = window.width * 0.7, window.height * 0.45
    touch.touch_move(*new_position)
    self.assertAlmostEqual(new_position[0], card_widget.center_x)
    self.assertAlmostEqual(new_position[1], card_widget.center_y)
    on_card_moved_handler.assert_not_called()

    # Touch up, nothing happens to the card. The on_card_moved event is
    # triggered.
    touch.touch_up()
    self.assertAlmostEqual(new_position[0], card_widget.center_x)
    self.assertAlmostEqual(new_position[1], card_widget.center_y)
    on_card_moved_handler.assert_called_once_with(card_widget,
                                                  card_widget.center)
    on_card_moved_handler.reset_mock()

    # Move the card back to the window center.
    card_widget.center = window_center

    # CardWidget's position has changed, but was not dragged by the user. The
    # on_card_moved event should not trigger.
    on_card_moved_handler.assert_not_called()

    # A click on the card, without dragging should not trigger the on_card_moved
    # event.
    touch = UnitTestTouch(*card_widget.center)
    touch.touch_down()
    touch.touch_up()
    on_card_moved_handler.assert_not_called()

    # Touch down in the bottom left corner of the window, outside of the card.
    # Nothing happens to the card.
    touch = UnitTestTouch(window.width * 0.1, window.height * 0.1)
    self.assertEqual(window_center, card_widget.center)
    on_card_moved_handler.assert_not_called()

    # Drag to the window center, on the card. Nothing happens to the card.
    touch.touch_move(*window_center)
    self.assertEqual(window_center, card_widget.center)
    on_card_moved_handler.assert_not_called()

    # Drag further to the top right corner of the window. Nothing happens to the
    # card.
    touch.touch_move(window.width * 0.95, window.height * 0.95)
    self.assertEqual(window_center, card_widget.center)
    on_card_moved_handler.assert_not_called()

    # Touch up. Nothing happens to the card.
    touch.touch_up()
    self.assertEqual(window_center, card_widget.center)
    on_card_moved_handler.assert_not_called()

  def test_dragging_a_card_with_the_mouse_translations_disabled(self):
    window = self.window

    on_card_moved_handler = Mock()

    # Place the card in the center of the window.
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=0.5,
                             do_translation=False)
    min_dimension = min(window.width, window.height)
    card_widget.size = min_dimension / 4, min_dimension / 2
    window_center = window.width / 2, window.height / 2
    card_widget.center = window_center
    card_widget.bind(on_card_moved=on_card_moved_handler)

    self.render(card_widget)

    # Touch down on the card, nothing happens to the card.
    touch = UnitTestTouch(*card_widget.center)
    touch.touch_down()
    self.assertEqual(window_center, card_widget.center)
    on_card_moved_handler.assert_not_called()

    # Drag in a random direction, the card should not move.
    new_position = window.width / 3, window.height / 3
    touch.touch_move(*new_position)
    self.assertEqual(window_center, card_widget.center)
    on_card_moved_handler.assert_not_called()

    # Touch up, nothing happens to the card.
    touch.touch_up()
    self.assertEqual(window_center, card_widget.center)
    on_card_moved_handler.assert_not_called()

    # Move the card to a new position. Since it was not dragged by the user, the
    # on_card_moved event should not trigger.
    card_widget.center = window.width / 3, window.height / 3
    on_card_moved_handler.assert_not_called()

    # A click on the card, without dragging should not trigger the on_card_moved
    # event.
    card_widget.center = window_center
    touch = UnitTestTouch(*card_widget.center)
    touch.touch_down()
    touch.touch_up()
    on_card_moved_handler.assert_not_called()

    # Touch down in the bottom left corner of the window, outside of the card.
    # Nothing happens to the card.
    touch = UnitTestTouch(window.width * 0.1, window.height * 0.1)
    self.assertEqual(window_center, card_widget.center)
    on_card_moved_handler.assert_not_called()

    # Drag to the window center, on the card. Nothing happens to the card.
    touch.touch_move(*window_center)
    self.assertEqual(window_center, card_widget.center)
    on_card_moved_handler.assert_not_called()

    # Drag further to the top right corner of the window. Nothing happens to the
    # card.
    touch.touch_move(window.width * 0.95, window.height * 0.95)
    self.assertEqual(window_center, card_widget.center)
    on_card_moved_handler.assert_not_called()

    # Touch up. Nothing happens to the card.
    touch.touch_up()
    self.assertEqual(window_center, card_widget.center)
    on_card_moved_handler.assert_not_called()

  def _run_test_on_double_tap_with_init_args(self, *args, **kwargs):
    """
    The args passed to this function are forwarded to the constructor of the
    CardWidget used in the test.
    """
    window = self.window

    # Place the card in the center of the window.
    card_widget = CardWidget(*args, **kwargs)
    min_dimension = min(window.width, window.height)
    card_widget.size = min_dimension / 4, min_dimension / 2
    window_center = window.width / 2, window.height / 2
    card_widget.center = window_center

    float_layout = FloatLayout()
    float_layout.add_widget(card_widget)
    self.render(float_layout)

    on_double_tap_handler = Mock()
    card_widget.bind(on_double_tap=on_double_tap_handler)

    # Normal click on the card does not trigger on_double_tap.
    touch = UnitTestTouch(*card_widget.center)
    touch.touch_down()
    touch.touch_up()
    on_double_tap_handler.assert_not_called()

    # Double click on the card triggers on_double_tap.
    touch.is_double_tap = True
    touch.touch_down()
    touch.touch_up()
    on_double_tap_handler.assert_called_once_with(card_widget)
    on_double_tap_handler.reset_mock()

    # Double click outside of the card does not trigger on_double_tap.
    touch = UnitTestTouch(0, 0)
    touch.is_double_tap = True
    touch.touch_down()
    touch.touch_up()
    on_double_tap_handler.assert_not_called()

    # Two cards on top of each other. Only the top one triggers on_double_tap.
    another_card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE),
                                     aspect_ratio=0.5)
    another_card_widget.size = card_widget.size
    another_card_widget.center = card_widget.center
    another_card_widget.bind(on_double_tap=on_double_tap_handler)
    float_layout.add_widget(another_card_widget)

    touch = UnitTestTouch(*card_widget.center)
    touch.is_double_tap = True
    touch.touch_down()
    touch.touch_up()
    on_double_tap_handler.assert_called_once_with(another_card_widget)

  def test_on_double_tap_with_enabled_transformations(self):
    self._run_test_on_double_tap_with_init_args(
      Card(Suit.SPADES, CardValue.ACE), aspect_ratio=0.5)

  def test_on_double_tap_with_disabled_transformations(self):
    self._run_test_on_double_tap_with_init_args(
      Card(Suit.SPADES, CardValue.ACE), aspect_ratio=0.5, do_translation=False,
      do_rotation=False, do_scale=False)

  def _run_flip_animation_test(self, fix_center: bool):
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.ACE))
    self.render(card_widget)
    animation = card_widget.get_flip_animation(duration=1,
                                               fixed_center=fix_center)
    on_complete_callback = Mock()
    animation.bind(on_complete=on_complete_callback)
    self.assertTrue(card_widget.visible)
    on_complete_callback.assert_not_called()
    initial_size = card_widget.size
    initial_pos = card_widget.pos
    card_widget.check_aspect_ratio(False)
    animation.start(card_widget)
    self.advance_frames(5)
    on_complete_callback.assert_not_called()
    card_widget.center = 100, 100
    self.wait_for_mock_callback(on_complete_callback)
    self.assertEqual(initial_size, card_widget.size)
    self.assertEqual(fix_center, initial_pos == card_widget.pos)
    self.assertFalse(card_widget.visible)
    animation = card_widget.get_flip_animation(duration=0.5,
                                               fixed_center=fix_center)
    on_complete_callback.reset_mock()
    animation.bind(on_complete=on_complete_callback)
    on_complete_callback.assert_not_called()
    animation.start(card_widget)
    self.wait_for_mock_callback(on_complete_callback)
    self.assertEqual(initial_size, card_widget.size)
    self.assertEqual(fix_center, initial_pos == card_widget.pos)
    self.assertTrue(card_widget.visible)

  def test_flip_animation_with_fixed_center(self):
    self._run_flip_animation_test(True)

  def test_flip_animation_without_fixed_center(self):
    self._run_flip_animation_test(False)
