#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from textwrap import dedent

from kivy.base import runTouchApp
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout

from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState
from model.game_state_test_utils import get_game_state_for_tests
from ui.card_slots_layout import CardSlotsLayout
from ui.card_widget import CardWidget
from ui.talon_widget import TalonWidget

# TODO(ui): Make background a gradient.
# TODO(ui): Maybe add paddings to some widgets.
Builder.load_string(dedent("""
  <GameWidget>:
    canvas.before:
      Color:
        rgba: 0.3, 0.4, 0.3, 1
      Rectangle:
        pos:self.pos
        size:self.size
  
    # The left-side of the widget: players cards, playing area, score info.
    AnchorLayout:
      anchor_x: "left"
      anchor_y: "center"
     
      # BoxLayout used to stack vertically the widgets on this side of the
      # screen.
      BoxLayout:
        orientation: 'vertical'
        size_hint: 0.65, 1
  
        # Placeholder to show the cards of the computer player. It uses only 10%
        # of the height since it mostly contains non-visible cards, so not very
        # useful information.
        BoxLayout:
          id: computer_cards_placeholder
          size_hint_y: 0.1
  
        # Scores for the computer player.
        BoxLayout:
          size_hint_y: 0.1
          orientation: 'vertical'
          Label:
            id: computer_game_score_label
            text: "Game points: 5"
            font_size: self.height / 2
            text_size: self.size
            halign: 'left'
            valign: 'bottom'
            size_hint_y: 0.5
          Label:
            id: computer_trick_score_label
            text: "Trick points: 45"
            font_size: self.height / 2
            text_size: self.size
            halign: 'left'
            valign: 'top'
            size_hint_y: 0.5
          
        # The area where the player can drag and drop cards in order to play
        # them.
        AnchorLayout:
          anchor_x: "center"
          anchor_y: "center"
          size_hint: 1.0, 1 - 0.1 - 0.35 - 0.1 - 0.1
          BoxLayout:
            id: play_area
            canvas:
              Color:
                rgba: 1, 0, 0, 1
              Line:
                rectangle: self.x + 1, self.y + 1, \
                           self.width - 1, self.height - 1
                dash_offset: 5
                dash_length: 5
            size_hint: 0.8, 1
  
        # Scores for the human player.
        BoxLayout:
          size_hint_y: 0.1
          orientation: 'vertical'
          Label:
            id: human_trick_score_label
            text: "Trick points: 27"
            font_size: self.height / 2
            text_size: self.size
            halign: 'left'
            valign: 'bottom'
            size_hint_y: 0.5
          Label:
            id: human_game_score_label
            text: "Game points: 3"
            font_size: self.height / 2
            text_size: self.size
            halign: 'left'
            valign: 'top'
            size_hint_y: 0.5
  
        # Placeholder for the widget that displays the human player's cards.
        BoxLayout:
          id: human_cards_placeholder
          size_hint_y: 0.35
  
    # The right side of the widget. It shows the tricks won by both players, the
    # talon, the trump card and the menu buttons.
    AnchorLayout:
      anchor_x: "right"
      anchor_y: "center"
      
      # BoxLayout used to stack vertically the widget on this side of the
      # screen.
      BoxLayout:
        orientation: 'vertical'
        size_hint: 0.35, 1
        
        # Placeholder for the widget that shows the tricks won by the computer
        # player.
        BoxLayout:
          id: computer_tricks_placeholder
          size_hint: 1, 0.25
          
        # Placeholder for the widget that shows the talon and trump card.
        BoxLayout:
          id: talon_placeholder
          size_hint: 1, None
        
        # Placeholder for the menu buttons.
        BoxLayout:
          id: menu_placeholder
          size_hint: 1, None
          Label:
            text: "Buttons"
  
        # Placeholder for the widget that shows the tricks won by the human
        # player.
        BoxLayout:
          id: human_tricks_placeholder
          size_hint: 1, None
  
        # Empty area in the bottom-right corner of the widget.
        BoxLayout:
          id: fill_area
          size_hint: 1, None
          Label:
            text: "Fill area"
  """))


class GameWidget(FloatLayout):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._cards = CardWidget.create_widgets_for_all_cards()
    self._init_tricks_widgets()
    self._init_cards_in_hand_widgets()
    self._init_talon_widget()

  def _init_talon_widget(self):
    self._talon = TalonWidget()
    self.ids.talon_placeholder.add_widget(self._talon)

  def _init_cards_in_hand_widgets(self):
    self._computer_cards = CardSlotsLayout(rows=1, cols=5, spacing=0.1,
                                           align_top=False)
    self.ids.computer_cards_placeholder.add_widget(self._computer_cards)
    self._computer_cards.size_hint = None, None
    self._human_cards = CardSlotsLayout(rows=1, cols=5, spacing=0.1,
                                        align_top=True)
    self.ids.human_cards_placeholder.add_widget(self._human_cards)
    self._human_cards.bind(size=self._computer_cards.setter('size'))

  def _init_tricks_widgets(self):
    self._computer_tricks = CardSlotsLayout(rows=2, cols=8, spacing=-0.2,
                                            align_top=True)
    self._computer_tricks.size_hint = 1, 1
    self.ids.computer_tricks_placeholder.add_widget(self._computer_tricks)
    self._human_tricks = CardSlotsLayout(rows=2, cols=8, spacing=-0.2,
                                         align_top=True)
    self._human_tricks.size_hint = 1, 1
    self.ids.human_tricks_placeholder.add_widget(self._human_tricks)

  @property
  def cards(self):
    return self._cards

  def init_from_game_state(self, game_state: GameState) -> None:
    # TODO(ui): maybe reset all widgets and cards.
    # noinspection PyTypeChecker
    for i, card in enumerate(sorted(game_state.cards_in_hand.one)):
      self._human_cards.add_card(self._cards[card], 0, i)
    # noinspection PyTypeChecker
    for i, card in enumerate(sorted(game_state.cards_in_hand.two)):
      self._cards[card].visible = False
      self._computer_cards.add_card(self._cards[card], 0, i)
    for i, trick in enumerate(game_state.won_tricks.one):
      row = i // 4
      col = (2 * i) % 8
      self._human_tricks.add_card(self._cards[trick.one], row, col)
      self._human_tricks.add_card(self._cards[trick.two], row, col + 1)
    for i, trick in enumerate(game_state.won_tricks.two):
      row = i // 4
      col = (2 * i) % 8
      self._computer_tricks.add_card(self._cards[trick.one], row, col)
      self._computer_tricks.add_card(self._cards[trick.two], row, col + 1)
    self._talon.set_trump_card(self._cards[game_state.trump_card])
    for card in reversed(game_state.talon):
      self._cards[card].visible = False
      self._talon.push_card(self._cards[card])

    self.ids.human_trick_score_label.text = \
      f"Trick points: {game_state.trick_points.one}"
    self.ids.computer_trick_score_label.text = \
      f"Trick points: {game_state.trick_points.two}"

    for suit in game_state.marriage_suits.one + game_state.marriage_suits.two:
      self._cards[Card(suit, CardValue.QUEEN)].visible = True
      self._cards[Card(suit, CardValue.KING)].visible = True

  def do_layout(self, *args, **kwargs):
    self.ids.computer_tricks_placeholder.height = 0.25 * self.height
    self.ids.human_tricks_placeholder.height = \
      self.ids.computer_tricks_placeholder.height
    self.ids.human_tricks_placeholder.y = 0.10 * self.height
    self.ids.fill_area.height = 0.10 * self.height
    self.ids.talon_placeholder.height = 0.30 * self.height
    self.ids.menu_placeholder.height = self.height * (
        1 - 0.25 - 0.25 - 0.1 - 0.3)
    super().do_layout(*args, **kwargs)


if __name__ == "__main__":
  game_widget = GameWidget()
  game_widget.size_hint = 1, 1
  game_widget.init_from_game_state(get_game_state_for_tests())
  game_widget.do_layout()
  runTouchApp(game_widget)
