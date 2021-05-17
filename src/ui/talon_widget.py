#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from typing import Optional, List, Tuple

from kivy.base import runTouchApp
from kivy.uix.layout import Layout

from model.card import Card
from model.card_value import CardValue
from model.suit import Suit
from ui.card_widget import CardWidget
from ui.debuggable_widget import DebuggableWidget


class TalonWidget(Layout, DebuggableWidget):
  """
  Widget used to hold and display the talon and the trump card under it.
  It tries to maximize the area used for displaying these while keeping the
  aspect ratio of the cards and aligning the left edge of the talon to line that
  divides the width of this widget in half.
  """

  def __init__(self, aspect_ratio: float = 24 / 37, **kwargs):
    """
    Instantiates a new TalonWidget.
    :param aspect_ratio: The aspect ratio to be enforced on the cards.
    :param kwargs: Parameters to be forwarded to the base class' constructor.
    """
    super().__init__(**kwargs)
    self._ratio = aspect_ratio
    self._trump_card: Optional[CardWidget] = None
    self._talon: List[Optional[CardWidget]] = []
    self._talon_size: Tuple[int, int] = 0, 0
    self._talon_pos: Tuple[int, int] = 0, 0

    # Trigger a call to do_layout() whenever position, size or children change.
    # pylint: disable=no-member
    self.fbind('children', self._trigger_layout)
    self.fbind('pos', self._trigger_layout)
    self.fbind('pos_hint', self._trigger_layout)
    self.fbind('size', self._trigger_layout)
    self.fbind('size_hint', self._trigger_layout)
    # pylint: enable=no-member

  def set_trump_card(self, widget: CardWidget) -> None:
    assert widget is not None, "Trump card cannot be set to None"
    assert self._trump_card is None, "Trump card is already set"
    self._trump_card = widget
    super().add_widget(widget)

  def remove_trump_card(self) -> CardWidget:
    assert self._trump_card is not None, "No trump card set"
    widget = self._trump_card
    super().remove_widget(widget)
    self._trump_card = None
    return widget

  def push_card(self, widget: CardWidget) -> None:
    """Add a new card on top of the existing talon."""
    assert widget is not None, "Card widget cannot be None"
    self._talon.append(widget)
    super().add_widget(widget)

  def pop_card(self) -> CardWidget:
    """Remove and return a card from the top of the talon."""
    assert len(self._talon) > 0, "The talon is empty"
    widget = self._talon.pop()
    super().remove_widget(widget)
    return widget

  def do_layout(self, *_, **__):
    """
    This function is called when a layout is called by a trigger. That means
    whenever the position, the size or the children of this layout change.
    """
    # TODO(ui): Add space for the deltas of each card.

    # TODO(cleanup): Check if this code can be simplified.
    # Compute the size and position for the talon.
    width_if_using_height = max(self.width / 2, self.height / 2) + \
                            max(self.height * self._ratio, self.width / 2)
    if self.width >= width_if_using_height:
      height = self.height
    else:
      height = self.width / 2 / self._ratio
      if self.width / 2 > self.height:
        height = self.height / self._ratio
      if height > self.height or height > self.width:
        height = self.width
    width = height * self._ratio
    self._talon_size = width, height
    assert abs(self._talon_size[0] / self._talon_size[1] - self._ratio) < 1e-10
    self._talon_pos = self.to_window(self.width / 2.0,
                                     (self.height - height) / 2.0, False, True)

    # Update the size and position for the cards in the talon.
    for card in self._talon:
      card.size = self._talon_size
      card.pos = self._talon_pos

    # Update the size and position for the trump card.
    if self._trump_card is not None:
      self._trump_card.size = self._talon_size
      self._trump_card.rotation = 90
      self._trump_card.pos = self.to_window((self.width - height) / 2.0,
                                            (self.height - width) / 2.0,
                                            False, True)


if __name__ == "__main__":
  RATIO = 10
  talon_widget = TalonWidget(RATIO)
  talon_widget.size = 1000, 1000
  talon_widget.size_hint = None, None

  trump_card = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=RATIO)
  talon_widget.set_trump_card(trump_card)

  _card = CardWidget(Card(Suit.SPADES, CardValue.ACE), aspect_ratio=RATIO)
  _card.visible = False
  talon_widget.push_card(_card)

  runTouchApp(talon_widget)

  # noinspection PyStringFormat
  print("(%.1f, (%d, %d), [%d, %d], (%.1f, %.1f), (%.1f, %.1f))" % (
    RATIO, *talon_widget.size, *_card.size, *_card.pos, *trump_card.pos))
