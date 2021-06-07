#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from unittest.mock import Mock

from kivy.animation import Animation
from kivy.uix.floatlayout import FloatLayout

from model.card import Card
from model.card_value import CardValue
from model.suit import Suit
from ui.animation_controller import AnimationController
from ui.card_widget import CardWidget
from ui.test_utils import GraphicUnitTest


class AnimationControllerStatesTest(unittest.TestCase):
  def test_can_only_cancel_in_running_state(self):
    with self.assertRaisesRegex(AssertionError,
                                r"call cancel\(\) in the RUNNING state: IDLE"):
      AnimationController().cancel()

    animation_controller = AnimationController()
    animation = Animation(x=10)
    animation.bind(on_complete=lambda *_: animation_controller.cancel())
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.QUEEN))
    animation_controller.add_card_animation(card_widget, animation)
    self.assertFalse(animation_controller.is_running)
    animation_controller.start()
    self.assertTrue(animation_controller.is_running)
    with self.assertRaisesRegex(AssertionError,
                                r"cancel\(\) in the RUNNING state: CANCELLED"):
      animation_controller.cancel()

  def test_can_only_call_start_in_idle_state(self):
    animation_controller = AnimationController()
    animation = Animation(x=10)
    animation.bind(on_complete=lambda *_: animation_controller.start())
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.QUEEN))
    animation_controller.add_card_animation(card_widget, animation)
    self.assertFalse(animation_controller.is_running)
    animation_controller.start()
    self.assertTrue(animation_controller.is_running)
    with self.assertRaisesRegex(AssertionError,
                                r" start\(\) in IDLE state: RUNNING"):
      animation_controller.start()
    with self.assertRaisesRegex(AssertionError,
                                r" start\(\) in IDLE state: CANCELLED"):
      animation_controller.cancel()

  def test_run_controller_with_no_animations(self):
    animation_controller = AnimationController()
    callback = Mock()
    self.assertFalse(animation_controller.is_running)
    animation_controller.start(callback)
    self.assertFalse(animation_controller.is_running)
    callback.assert_called_once()

  def test_cannot_add_multiple_animations_for_the_same_card(self):
    animation_controller = AnimationController()
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.QUEEN))
    animation_controller.add_card_animation(card_widget, Animation(x=10))
    with self.assertRaisesRegex(AssertionError,
                                "already an animation for this CardWidget"):
      animation_controller.add_card_animation(card_widget, Animation(y=10))

  def test_can_only_add_animations_in_the_idle_state(self):
    animation_controller = AnimationController()
    animation = Animation(x=10)
    animation.bind(
      on_complete=lambda *_: animation_controller.add_card_animation(
        CardWidget(Card(Suit.SPADES, CardValue.QUEEN)), Animation(y=10)))
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.QUEEN))
    animation_controller.add_card_animation(card_widget, animation)
    self.assertFalse(animation_controller.is_running)
    animation_controller.start()
    self.assertTrue(animation_controller.is_running)
    with self.assertRaisesRegex(AssertionError,
                                "add animations in the IDLE state: RUNNING"):
      animation_controller.add_card_animation(
        CardWidget(Card(Suit.SPADES, CardValue.QUEEN)), Animation(y=10))
    with self.assertRaisesRegex(AssertionError,
                                "add animations in the IDLE state: CANCELLED"):
      animation_controller.cancel()


class AnimationControllerTest(GraphicUnitTest):
  def test_animate_one_card_no_callback(self):
    card_widget = CardWidget(Card(Suit.SPADES, CardValue.QUEEN))
    card_widget.pos = 0, 0
    float_layout = FloatLayout()
    float_layout.add_widget(card_widget)
    self.render(float_layout)

    self.assert_pixels_almost_equal([0, 0], card_widget.pos)
    animation_controller = AnimationController()
    animation = Animation(x=self.window.size[0], y=self.window.size[1])
    on_complete_callback = Mock()
    animation.bind(on_complete=on_complete_callback)
    animation_controller.add_card_animation(card_widget, animation)
    self.assertFalse(animation_controller.is_running)
    animation_controller.start()
    self.assertTrue(animation_controller.is_running)
    self.wait_for_mock_callback(on_complete_callback)
    self.assertFalse(animation_controller.is_running)
    self.assert_pixels_almost_equal(self.window.size, card_widget.pos)

  def test_animate_two_cards_with_callback(self):
    card_widget_1 = CardWidget(Card(Suit.SPADES, CardValue.QUEEN))
    card_widget_1.pos = 0, 0
    card_widget_2 = CardWidget(Card(Suit.SPADES, CardValue.KING))
    card_widget_2.pos = self.window.size[0], 0
    float_layout = FloatLayout()
    float_layout.add_widget(card_widget_1)
    float_layout.add_widget(card_widget_2)
    self.render(float_layout)

    self.assert_pixels_almost_equal([0, 0], card_widget_1.pos)
    self.assert_pixels_almost_equal([self.window.size[0], 0], card_widget_2.pos)
    animation_controller = AnimationController()
    animation_1 = Animation(x=self.window.size[0], y=self.window.size[1],
                            duration=0.5)
    on_complete_callback_1 = Mock()
    animation_1.bind(on_complete=on_complete_callback_1)
    animation_controller.add_card_animation(card_widget_1, animation_1)
    animation_2 = Animation(x=0, y=self.window.size[1],
                            duration=2 * animation_1.duration)
    on_complete_callback_2 = Mock()
    animation_2.bind(on_complete=on_complete_callback_2)
    animation_controller.add_card_animation(card_widget_2, animation_2)
    on_both_animations_complete_callback = Mock()
    self.assertFalse(animation_controller.is_running)
    animation_controller.start(on_both_animations_complete_callback)
    self.assertTrue(animation_controller.is_running)

    on_complete_callback_1.assert_not_called()
    on_complete_callback_2.assert_not_called()
    on_both_animations_complete_callback.assert_not_called()

    self.wait_for_mock_callback(on_complete_callback_1)
    self.assertTrue(animation_controller.is_running)
    self.assert_pixels_almost_equal(self.window.size, card_widget_1.pos)
    on_complete_callback_2.assert_not_called()
    on_both_animations_complete_callback.assert_not_called()

    self.wait_for_mock_callback(on_complete_callback_2)
    self.assertFalse(animation_controller.is_running)
    self.assert_pixels_almost_equal(self.window.size, card_widget_1.pos)
    self.assert_pixels_almost_equal([0, self.window.size[1]], card_widget_2.pos)
    on_both_animations_complete_callback.assert_called_once()

    # Verify that the AnimationController can be reused.
    self.assertFalse(animation_controller.is_running)
    animation_controller.add_card_animation(card_widget_1, animation_1)

  def test_cancel_two_cards_animation_with_callback(self):
    card_widget_1 = CardWidget(Card(Suit.SPADES, CardValue.QUEEN))
    card_widget_1.pos = 0, 0
    card_widget_2 = CardWidget(Card(Suit.SPADES, CardValue.KING))
    card_widget_2.pos = self.window.size[0], 0
    float_layout = FloatLayout()
    float_layout.add_widget(card_widget_1)
    float_layout.add_widget(card_widget_2)
    self.render(float_layout)

    self.assert_pixels_almost_equal([0, 0], card_widget_1.pos)
    self.assert_pixels_almost_equal([self.window.size[0], 0], card_widget_2.pos)
    animation_controller = AnimationController()
    animation_1 = Animation(x=self.window.size[0], y=self.window.size[1],
                            duration=5)
    on_complete_callback_1 = Mock()
    animation_1.bind(on_complete=on_complete_callback_1)
    animation_controller.add_card_animation(card_widget_1, animation_1)
    animation_2 = Animation(x=0, y=self.window.size[1],
                            duration=2 * animation_1.duration)
    on_complete_callback_2 = Mock()
    animation_2.bind(on_complete=on_complete_callback_2)
    animation_controller.add_card_animation(card_widget_2, animation_2)
    on_both_animations_complete_callback = Mock()
    self.assertFalse(animation_controller.is_running)
    animation_controller.start(on_both_animations_complete_callback)
    self.assertTrue(animation_controller.is_running)

    on_complete_callback_1.assert_not_called()
    on_complete_callback_2.assert_not_called()
    on_both_animations_complete_callback.assert_not_called()

    # Advance a couple of frames to move the cards a little bit, but not
    # complete any animation.
    self.advance_frames(5)
    self.assertNotEqual(0, card_widget_1.x)
    self.assertNotEqual(0, card_widget_1.y)
    self.assertNotEqual(self.window.size[0], card_widget_2.x)
    self.assertNotEqual(0, card_widget_2.y)

    # No callback should be called.
    on_complete_callback_1.assert_not_called()
    on_complete_callback_2.assert_not_called()
    on_both_animations_complete_callback.assert_not_called()

    # Cancel the animations.
    self.assertTrue(animation_controller.is_running)
    animation_controller.cancel()
    self.assertFalse(animation_controller.is_running)

    # All callbacks should be called.
    on_complete_callback_1.assert_called_once()
    on_complete_callback_2.assert_called_once()
    on_both_animations_complete_callback.assert_called_once()

    # Verify that the AnimationController can be reused.
    animation_controller.add_card_animation(card_widget_1, animation_1)
