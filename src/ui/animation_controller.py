#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import enum
import logging
from typing import Dict, Callable, Optional

from kivy.animation import Animation
from kivy.base import EventLoop, runTouchApp
from kivy.clock import Clock
from kivy.uix.floatlayout import FloatLayout

from model.card import Card
from model.card_value import CardValue
from model.suit import Suit
from ui.card_widget import CardWidget


class _State(enum.Enum):
  IDLE = enum.auto()
  RUNNING = enum.auto()
  CANCELLED = enum.auto()


class AnimationController:
  """
  The AnimationController manages animations for multiple CardWidgets. One can
  start or cancel all these animations simultaneously.
  """

  def __init__(self):
    self._animations: Dict[CardWidget, Animation] = {}
    self._state: _State = _State.IDLE
    self._on_complete_callback: Optional[Callable[[], None]] = None

  @property
  def is_running(self) -> bool:
    return self._state == _State.RUNNING

  def add_card_animation(self, card_widget: CardWidget,
                         animation: Animation) -> None:
    """
    Register an animation for a given CardWidget. There can only be one
    Animation per CardWidget.
    """
    assert self._state == _State.IDLE, \
      f"Only add animations in the IDLE state: {self._state.name}"
    assert card_widget not in self._animations, \
      "There is already an animation for this CardWidget"
    self._animations[card_widget] = animation

  def start(self,
            on_complete_callback: Optional[Callable[[], None]] = None) -> None:
    """
    Run all registered animations on the corresponding CardWidgets.
    If on_complete_callback is not None, it will be called by the
    AnimationController when all animations are completed or when the run is
    cancelled.
    """
    assert self._state == _State.IDLE, \
      f"Can only call start() in IDLE state: {self._state.name}"
    logging.info("AnimationCtrl: Starting %s animation(s)",
                 len(self._animations))
    self._state = _State.RUNNING
    self._on_complete_callback = on_complete_callback
    if len(self._animations) == 0:
      self._on_complete()
    else:
      for card_widget, animation in self._animations.items():
        animation.bind(on_complete=self._finalize_animation)
        animation.start(card_widget)

  def _finalize_animation(self, animation: Animation, card_widget: CardWidget):
    assert self._animations[card_widget] == animation
    assert self._state != _State.IDLE, \
      f"This should not be called in the IDLE state: {self._state.name}"
    if self._state == _State.RUNNING:
      del self._animations[card_widget]
      if len(self._animations) == 0:
        self._on_complete()

  def cancel(self) -> None:
    """
    Cancels all the running animations and calls on_complete_callback.
    """
    assert self._state == _State.RUNNING, \
      f"Can only call cancel() in the RUNNING state: {self._state.name}"
    self._state = _State.CANCELLED
    for card_widget, anim in self._animations.items():
      anim.stop(card_widget)
    self._animations = {}
    self._on_complete()

  def _on_complete(self) -> None:
    assert len(self._animations) == 0, self._animations
    self._state = _State.IDLE
    if self._on_complete_callback is not None:
      self._on_complete_callback()


if __name__ == "__main__":
  EventLoop.ensure_window()
  EventLoop.window.size = 400, 400
  _float_layout = FloatLayout()
  _float_layout.size = 400, 400
  _float_layout.size_hint = 1, 1

  _animation_controller = AnimationController()
  _animation = Animation(rotation=-45) + \
               Animation(center_x=_float_layout.width / 4,
                         center_y=_float_layout.height / 4) + \
               Animation(rotation=270) + \
               Animation(center_x=_float_layout.width / 4 * 3,
                         center_y=_float_layout.height / 4) + \
               Animation(rotation=270 + 90) + \
               Animation(center_x=_float_layout.width / 4 * 3,
                         center_y=_float_layout.height / 4 * 3) + \
               Animation(rotation=90) + \
               Animation(center_x=_float_layout.width / 4,
                         center_y=_float_layout.height / 4 * 3) + \
               Animation(rotation=45) + \
               Animation(center_x=_float_layout.width / 2,
                         center_y=_float_layout.height / 2) + \
               Animation(rotation=0)

  _card_widget = CardWidget(Card(Suit.SPADES, CardValue.QUEEN))
  _card_widget.size_hint = None, None
  _card_widget.bind(on_double_tap=lambda *_: _animation_controller.start())
  _float_layout.add_widget(_card_widget)


  def _reset_pos():
    _card_widget.center = _float_layout.center
    _card_widget.visible = True
    _card_widget.rotation = 0
    Clock.schedule_once(
      lambda _: _animation_controller.add_card_animation(_card_widget,
                                                         _animation))


  def _cancel():
    if _animation_controller.is_running:
      _animation_controller.cancel()


  _animation.bind(on_complete=lambda *_: _reset_pos())
  _reset_pos()
  EventLoop.window.on_resize = lambda *_: _cancel()
  runTouchApp(_float_layout)
