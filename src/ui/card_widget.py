#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import os.path
import random
from typing import Dict

from kivy.base import runTouchApp
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.scatter import Scatter

from model.card import Card


def _get_image_full_path(filename: str) -> str:
  module_dir = os.path.join(os.path.dirname(__file__))
  image_folder = os.path.join(module_dir, "resources", "cards")
  return os.path.join(image_folder, filename + ".png")


def _get_card_filename(card: Card) -> str:
  filename = card.card_value.name.lower()[0] + card.suit.name.lower()[0]
  return _get_image_full_path(filename)


def _get_card_back_filename() -> str:
  return _get_image_full_path("card_back")


# TODO(ui): Add an atlas with all card images.
# TODO(ui): Add a drop shadow.
class CardWidget(Scatter):
  """
  A widget that represents a playing card. It can be moved, scaled and rotated
  using fingers on a multi-touch system. It makes sure that the aspect ratio of
  the card does not change.
  """

  # pylint: disable=too-many-instance-attributes

  def __init__(self, card: Card, aspect_ratio: float = 24 / 37, **kwargs):
    """
    Instantiates a new CardWidget.
    :param card: The card value to associate to this widget.
    :param aspect_ratio: The aspect ratio that will be enforced.
    :param kwargs: Parameters to be forwarded to the base class' constructor.
    """
    super().__init__(**kwargs)
    self._card = card
    self._visible = True
    self._grayed_out = False
    self.auto_bring_to_front = False
    image = Image(source=_get_card_filename(card))
    image.keep_ratio = False
    image.allow_stretch = True
    self.add_widget(image)
    self._ratio = aspect_ratio
    self.width = self.height * self._ratio
    self.size_hint = None, None
    self.register_event_type("on_double_tap")
    self.fbind("size", image.setter("size"))
    # noinspection PyUnreachableCode
    if __debug__:
      self.fbind("size", self._assert_aspect_ratio)

  def _assert_aspect_ratio(self, _, size):
    assert abs(size[0] - size[1] * self._ratio) <= 1, (size, self._ratio)

  @property
  def visible(self) -> bool:
    """
    Specifies whether the player can see this card or not (i.e., the player can
    only see the back of the card).
    """
    return self._visible

  @visible.setter
  def visible(self, visible):
    self._visible = visible
    if self._visible:
      self.children[0].source = _get_card_filename(self._card)
    else:
      self.children[0].source = _get_card_back_filename()

  @property
  def grayed_out(self) -> bool:
    return self._grayed_out

  @grayed_out.setter
  def grayed_out(self, grayed_out: bool) -> None:
    self._grayed_out = grayed_out
    self.opacity = 0.5 if self._grayed_out else 1.0

  @staticmethod
  def create_widgets_for_all_cards() -> Dict[Card, "CardWidget"]:
    """Creates a CardWidget for each of the 20 possible cards."""
    kwargs = {'do_rotation': False, 'do_scale': False, 'do_translation': False}
    return {card: CardWidget(card, **kwargs) for card in Card.get_all_cards()}

  def on_touch_up(self, touch):
    """
    In addition to the handling performed by the base class (Scatter), it also
    checks whether a double tap/click was performed on this widget. If that is
    the case, it triggers the on_double_tap event.
    """
    return_value = super().on_touch_up(touch)
    if touch.is_double_tap and touch.grab_current is self:
      self.dispatch("on_double_tap")
      return True
    return return_value

  def on_double_tap(self):
    """
    Default handler for the on_double_tap event. This event is triggered
    whenever there is a double tap or double click on the card itself.
    """


if __name__ == "__main__":
  def toggle_visible(clicked_card_widget):
    clicked_card_widget.visible = not clicked_card_widget.visible


  float_layout = FloatLayout()
  float_layout.size = 1000, 1000
  deck = Card.get_all_cards()
  random.shuffle(deck)

  for _card in deck:
    card_widget = CardWidget(_card)
    card_widget.size = 240, 370
    card_widget.grayed_out = random.random() > 0.5
    card_widget.pos = random.randint(100, 900), random.randint(100, 900)
    card_widget.rotation = random.randint(0, 180)
    card_widget.bind(on_double_tap=toggle_visible)
    float_layout.add_widget(card_widget)

  runTouchApp(float_layout)
