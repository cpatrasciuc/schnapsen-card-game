#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.
import random

from kivy.graphics.transformation import Matrix
from kivy.uix.floatlayout import FloatLayout

from model.card import Card
from uidemo.card_slots_layout import CardSlotsLayout
from uidemo.card_widget import CardWidget
from uidemo.talon_widget import TalonWidget


class GameWidget(FloatLayout):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._is_moving = False

    tricks_top = CardSlotsLayout(rows=2, cols=8, debug=True, spacing=-0.2,
                                 align_top=True)
    tricks_top.size_hint = 1, 1
    tricks_bot = CardSlotsLayout(rows=2, cols=8, debug=True, spacing=-0.2,
                                 align_top=True)
    tricks_bot.size_hint = 1, 1
    self.ids.computer_tricks.add_widget(tricks_top)
    self.ids.player_tricks.add_widget(tricks_bot)

    cards_bot = CardSlotsLayout(rows=1, cols=5, debug=True, spacing=0.1,
                                align_top=True)
    tricks_bot.size_hint = 1, 1
    self.ids.player_cards_box.add_widget(cards_bot)
    self._cards_bot = cards_bot

    talon = TalonWidget(debug=True)
    talon.debug_text = "TALON"
    self.ids.talon.add_widget(talon)
    self._talon = talon

    cards_top = CardSlotsLayout(aspect_ratio=24 / 37 / 0.1 * 0.35, rows=1,
                                cols=5, debug=True, spacing=0.1, align_top=True)
    cards_top.size_hint = 1, 1
    self.ids.computer_cards_box.add_widget(cards_top)
    self._cards_top = cards_top

    self._player_cards = []
    self._computer_cards = []
    self._talon_cards = []
    self._trump_card = None

  def init_cards(self):
    # Instantiate the cards
    cards = Card.get_all_cards()
    random.shuffle(cards)

    for i, card in enumerate(cards[:5]):
      card_widget = CardWidget(do_rotation=False, do_scale=False)
      card_widget.card_name = f"{card.card_value.name}\n{card.suit.name}"
      self._player_cards.append(card_widget)
      self.add_widget(card_widget)

    for i, card in enumerate(cards[5:10]):
      card_widget = CardWidget(do_rotation=False, do_scale=False,
                               do_translation=False)
      card_widget.card_name = f"{card.card_value.name}\n{card.suit.name}"
      card_widget.set_visible(False)
      self._computer_cards.append(card_widget)
      self.add_widget(card_widget)

    card = cards[11]
    card_widget = CardWidget(do_rotation=False, do_scale=False,
                             do_translation=False)
    card_widget.card_name = f"{card.card_value.name}\n{card.suit.name}"
    m = Matrix()
    m.rotate(3.14 / 2, 0, 0, 1)
    card_widget.apply_transform(m, anchor=(
      card_widget.width / 2, card_widget.height / 2))
    self._trump_card = card_widget
    self.add_widget(card_widget)

    for i, card in enumerate(cards[12:]):
      card_widget = CardWidget(do_rotation=False, do_scale=False,
                               do_translation=False)
      card_widget.card_name = f"{card.card_value.name}\n{card.suit.name}"

      card_widget.set_visible(False)
      self._talon_cards.append(card_widget)
      self.add_widget(card_widget)

  def _do_layout_cards(self):
    for i, card_widget in enumerate(self._player_cards):
      if not self.ids.play_area.collide_point(*card_widget.center):
        card_widget.pos = self._cards_bot.get_relative_pos(0, i)
      card_widget.size = self._cards_bot.get_card_size()
    for i, card_widget in enumerate(self._computer_cards):
      rel_x, rel_y = self._cards_top.get_relative_pos(0, i)
      card_widget.pos = self._cards_top.x + rel_x, self._cards_top.y + rel_y
      card_widget.size = self._cards_bot.get_card_size()
    if self._trump_card is not None:
      size = self._talon.get_trump_card_size()
      self._trump_card.size = size[1], size[0]
      self._trump_card.pos = self._talon.get_trump_card_pos()

    pos = self._talon.get_talon_pos()
    size = self._talon.get_talon_size()
    for i, card_widget in enumerate(self._talon_cards):
      card_widget.pos = pos[0] + i * 2, pos[1] - i * 2
      card_widget.size = size

  def do_layout(self, *args, **kwargs):
    self.ids.computer_tricks.height = 0.25 * self.height
    self.ids.player_tricks.height = self.ids.computer_tricks.height
    self.ids.player_tricks.y = 0.10 * self.height
    self.ids.fill_area.height = 0.10 * self.height
    self.ids.talon.height = 0.3 * self.height
    self.ids.buttons.height = self.height - self.ids.computer_tricks.height \
                              - self.ids.player_tricks.height \
                              - self.ids.talon.height \
                              - self.ids.fill_area.height

    # Max width for talon
    width, _ = self.ids.computer_tricks.children[0].get_card_size()
    rel_x, _ = self.ids.computer_tricks.children[0].get_relative_pos(0, 7)
    self.ids.talon.width = rel_x + width
    if not self._is_moving:
      self._do_layout_cards()
    super().do_layout(*args, **kwargs)

  def trigger_layout(self):
    self._trigger_layout()

  def on_touch_down(self, touch):
    if self.collide_point(*touch.pos):
      self._is_moving = True
    # push the current coordinate, to be able to restore it later
    touch.push()

    # transform the touch coordinate to local space
    touch.apply_transform_2d(self.to_local)

    # dispatch the touch as usual to children
    # the coordinate in the touch is now in local space
    ret = super().on_touch_down(touch)

    # whatever the result, don't forget to pop your transformation
    # after the call, so the coordinate will be back in parent space
    touch.pop()

    # return the result (depending what you want.)
    return ret

  def on_touch_up(self, touch):
    touch.push()

    # transform the touch coordinate to local space
    touch.apply_transform_2d(self.to_local)

    # dispatch the touch as usual to children
    # the coordinate in the touch is now in local space
    ret = super().on_touch_up(touch)

    # whatever the result, don't forget to pop your transformation
    # after the call, so the coordinate will be back in parent space
    touch.pop()

    self._is_moving = False
    self._do_layout_cards()

    # return the result (depending what you want.)
    return ret