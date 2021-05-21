#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import logging
from textwrap import dedent
from typing import Dict

from kivy.base import runTouchApp
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout

from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState
from model.game_state_test_utils import get_game_state_for_tests
from model.player_action import PlayerAction, ExchangeTrumpCardAction, \
  CloseTheTalonAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair
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
  """The main widget used to view/play a game of Schnapsen."""

  def __init__(self, **kwargs):
    """
    Instantiates a new GameWidget and all its children widgets. All the widgets
    are empty (i.e., no cards).
    """
    super().__init__(**kwargs)
    self._cards = CardWidget.create_widgets_for_all_cards()
    self._init_tricks_widgets()
    self._init_cards_in_hand_widgets()
    self._init_talon_widget()
    self.do_layout()

  def _init_talon_widget(self):
    self._talon = TalonWidget()
    self.ids.talon_placeholder.add_widget(self._talon)

  def _init_cards_in_hand_widgets(self):
    computer_cards = CardSlotsLayout(rows=1, cols=5, spacing=0.1,
                                     align_top=False)
    self.ids.computer_cards_placeholder.add_widget(computer_cards)
    computer_cards.size_hint = None, None
    human_cards = CardSlotsLayout(rows=1, cols=5, spacing=0.1,
                                  align_top=True)
    self.ids.human_cards_placeholder.add_widget(human_cards)
    human_cards.bind(size=computer_cards.setter('size'))
    self._player_card_widgets = PlayerPair(one=human_cards, two=computer_cards)

  def _init_tricks_widgets(self):
    computer_tricks = CardSlotsLayout(rows=2, cols=8, spacing=-0.2,
                                      align_top=True)
    computer_tricks.size_hint = 1, 1
    self.ids.computer_tricks_placeholder.add_widget(computer_tricks)
    human_tricks = CardSlotsLayout(rows=2, cols=8, spacing=-0.2,
                                   align_top=True)
    human_tricks.size_hint = 1, 1
    self.ids.human_tricks_placeholder.add_widget(human_tricks)
    self._tricks_widgets = PlayerPair(one=human_tricks, two=computer_tricks)

  @property
  def cards(self) -> Dict[Card, CardWidget]:
    return self._cards

  @property
  def talon_widget(self) -> TalonWidget:
    return self._talon

  @property
  def tricks_widgets(self) -> PlayerPair[CardSlotsLayout]:
    """
    Returns the pair of widgets used to display the tricks won by each player.
    """
    return self._tricks_widgets

  @property
  def player_card_widgets(self) -> PlayerPair[CardSlotsLayout]:
    """
    Returns the pair of widgets used to display the cards held by each player.
    """
    return self._player_card_widgets

  @property
  def play_area(self) -> FloatLayout:
    """
    Returns a reference to the widget representing the area where the cards are
    played during a trick.
    """
    return self.ids.play_area

  def init_from_game_state(self, game_state: GameState) -> None:
    """
    Updates this GameWidget such that it represents the game state provided as
    an argument. It does not hold a reference to the game_state object. This
    GameWidget will not update itself automatically if subsequent changes are
    performed on the game_state object.
    """
    # TODO(ui): maybe reset all widgets and cards.
    for player in PlayerId:
      # noinspection PyTypeChecker
      for i, card in enumerate(sorted(game_state.cards_in_hand[player])):
        self._cards[card].visible = player == PlayerId.ONE
        self._player_card_widgets[player].add_card(self._cards[card], 0, i)

    for player in PlayerId:
      for trick in game_state.won_tricks[player]:
        self._cards[trick.one].visible = True
        self._tricks_widgets[player].add_card(self._cards[trick.one])
        self._cards[trick.two].visible = True
        self._tricks_widgets[player].add_card(self._cards[trick.two])

    self._talon.set_trump_card(self._cards[game_state.trump_card])
    for card in reversed(game_state.talon):
      self._cards[card].visible = False
      self._talon.push_card(self._cards[card])

    self.on_score_modified(game_state.trick_points)

    # TODO(ui): Remove this hack once Card.visible is available.
    for suit in game_state.marriage_suits.one + game_state.marriage_suits.two:
      self._cards[Card(suit, CardValue.QUEEN)].visible = True
      self._cards[Card(suit, CardValue.KING)].visible = True

  def on_score_modified(self, score: PlayerPair[int]) -> None:
    """
    This method should be called whenever the trick points need to be updated.
    :param score: The updated value for trick points.
    """
    self.ids.human_trick_score_label.text = f"Trick points: {score.one}"
    self.ids.computer_trick_score_label.text = f"Trick points: {score.two}"

  def do_layout(self, *args, **kwargs) -> None:
    """
    This function is called when a layout is called by a trigger. That means
    whenever the position, the size or the children of this layout change.
    """
    self.ids.computer_tricks_placeholder.height = 0.25 * self.height
    self.ids.human_tricks_placeholder.height = \
      self.ids.computer_tricks_placeholder.height
    self.ids.human_tricks_placeholder.y = 0.10 * self.height
    self.ids.fill_area.height = 0.10 * self.height
    self.ids.talon_placeholder.height = 0.30 * self.height
    self.ids.menu_placeholder.height = self.height * (
        1 - 0.25 - 0.25 - 0.1 - 0.3)
    super().do_layout(*args, **kwargs)

  def _get_trump_jack_widget(self) -> CardWidget:
    trump_jack = Card(suit=self._talon.trump_card.card.suit,
                      card_value=CardValue.JACK)
    trump_jack_widget = self._cards[trump_jack]
    return trump_jack_widget

  def _exchange_trump_card(self, player: PlayerId) -> None:
    trump_jack_widget = self._get_trump_jack_widget()
    trump_jack_widget.visible = True
    card_slots_widget = self._player_card_widgets[player]
    row, col = card_slots_widget.remove_card(trump_jack_widget)
    assert row is not None and col is not None, \
      "Trump Jack not in player's hand"
    trump_card_widget = self._talon.remove_trump_card()
    trump_card_widget.rotation = 0
    # TODO(ui): Sort the cards in hand.
    card_slots_widget.add_card(trump_card_widget, row, col)
    self._talon.set_trump_card(trump_jack_widget)

  def on_action(self, action: PlayerAction) -> None:
    """
    This method should be called whenever a new player action was performed in a
    game of Schnapsen, in order to update the state of the widget accordingly.
    :param action: The latest action performed by one of the players.
    """
    logging.info("GameWidget: on_action: %s", action)
    if isinstance(action, ExchangeTrumpCardAction):
      self._exchange_trump_card(action.player_id)
    elif isinstance(action, CloseTheTalonAction):
      self._talon.closed = True


if __name__ == "__main__":
  game_widget = GameWidget()
  game_widget.size_hint = 1, 1
  game_widget.init_from_game_state(get_game_state_for_tests())
  game_widget.do_layout()
  runTouchApp(game_widget)
