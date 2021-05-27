#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import logging
from textwrap import dedent
from typing import Dict, Tuple, Optional, List, Callable

from kivy.base import runTouchApp
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState, Trick
from model.game_state_test_utils import get_game_state_for_tests
from model.player_action import PlayerAction, ExchangeTrumpCardAction, \
  CloseTheTalonAction, PlayCardAction, AnnounceMarriageAction, \
  get_available_actions
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from ui.card_slots_layout import CardSlotsLayout
from ui.card_widget import CardWidget
from ui.talon_widget import TalonWidget


def _get_trick_points_color(points: int) -> str:
  """Returns the markup color that should be used to display the trick score."""
  if points == 0:
    return "ff3333"  # red
  if points < 33:
    return "ffff33"  # yellow
  if points < 66:
    return "ffffff"  # white
  return "33ff33"  # green


def _get_game_points_color(points: int) -> str:
  """Returns the markup color that should be used to display the game score."""
  assert 0 <= points < 7, "Invalid game points: %s" % points
  if points < 4:
    return "33aa33"  # green
  if points == 4:
    return "ffffff"  # white
  if points == 5:
    return "ffff33"  # yellow
  return "ff3333"  # red


def _delete_widget(widget: Widget) -> None:
  if widget.parent is not None:
    widget.parent.remove_widget(widget)
  del widget


# TODO(tests): Add tests for padding_pct.
Builder.load_string(dedent("""
  <GameWidget>:
    # Adds some padding to the left/right side of the GameWidget layout, as a
    # percentage of those components width/height.
    padding_pct: 0.00
    canvas.before:
      Rectangle:
        source: 'resources/background.png'
        pos: self.pos
        size: self.size
  
    # The right side of the widget. It shows the tricks won by both players, the
    # talon, the trump card and the menu buttons.
    AnchorLayout:
      anchor_x: "right"
      anchor_y: "center"
      
      # BoxLayout used to stack vertically the widget on this side of the
      # screen.
      BoxLayout:
        orientation: "vertical"
        size_hint: 0.35, 1
        padding: root.padding_pct * self.width, root.padding_pct * self.height
        
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
          DebuggableWidget:
            debug_text: "Menu buttons"
  
        # Placeholder for the widget that shows the tricks won by the human
        # player.
        BoxLayout:
          id: human_tricks_placeholder
          size_hint: 1, None
  
        # Empty area in the bottom-right corner of the widget.
        BoxLayout:
          id: fill_area
          size_hint: 1, None
          DebuggableWidget:
            debug_text: "Fill area"

    # The left-side of the widget: players cards, playing area, score info.
    AnchorLayout:
      anchor_x: "left"
      anchor_y: "center"
     
      # BoxLayout used to stack vertically the widgets on this side of the
      # screen.
      BoxLayout:
        orientation: 'vertical'
        size_hint: 0.65, 1
        padding: root.padding_pct * self.width, root.padding_pct * self.height
  
        # Placeholder to show the cards of the computer player. It uses only 10%
        # of the height since it mostly contains non-visible cards, so not very
        # useful information.
        BoxLayout:
          id: computer_cards_placeholder
          size_hint_y: 0.1
  
        # Scores for the computer player.
        BoxLayout:
          size_hint_y: 0.1
          orientation: "vertical"
          Label:
            id: computer_game_score_label
            text: "Game points: 5"
            font_size: self.height / 2
            text_size: self.size
            halign: "left"
            valign: "bottom"
            size_hint_y: 0.5
            markup: True
          Label:
            id: computer_trick_score_label
            text: "Trick points: 45"
            font_size: self.height / 2
            text_size: self.size
            halign: "left"
            valign: "top"
            size_hint_y: 0.5
            markup: True
          
        # The area where the player can drag and drop cards in order to play
        # them.
        AnchorLayout:
          anchor_x: "center"
          anchor_y: "center"
          size_hint: 1.0, 1 - 0.1 - 0.35 - 0.1 - 0.1
          FloatLayout:
            id: play_area
            size_hint: 0.8, 1
            DebuggableWidget:
              debug_text: "Play area"
              color_rgba: 1, 0, 0, 1
              background_rgba: 1, 1, 1, 0.1
              size_hint: 1, 1
              pos: play_area.pos
  
        # Scores for the human player.
        BoxLayout:
          size_hint_y: 0.1
          orientation: "vertical"
          Label:
            id: human_trick_score_label
            text: "Trick points: 27"
            font_size: self.height / 2
            text_size: self.size
            halign: "left"
            valign: "bottom"
            size_hint_y: 0.5
            markup: True
          Label:
            id: human_game_score_label
            text: "Game points: 3"
            font_size: self.height / 2
            text_size: self.size
            halign: "left"
            valign: "top"
            size_hint_y: 0.5
            markup: True
  
        # Placeholder for the widget that displays the human player's cards.
        BoxLayout:
          id: human_cards_placeholder
          size_hint_y: 0.35
  """))


class GameWidget(FloatLayout):
  """The main widget used to view/play a game of Schnapsen."""

  # pylint: disable=too-many-instance-attributes

  def __init__(self, **kwargs):
    """
    Instantiates a new GameWidget and all its children widgets. All the widgets
    are empty (i.e., no cards).
    """
    super().__init__(**kwargs)

    # Dictionary used to store all the cards widgets.
    self._cards: Dict[Card, CardWidget] = {}

    # A reference to the area where the cards are moved when one player plays a
    # card.
    self._play_area = self.ids.play_area.__self__
    # Store the current play area size in order to update the position of the
    # already played cards accordingly, when the window is resized.
    self._prev_play_area_size = self._play_area.size[0], self._play_area.size[1]
    self._prev_play_area_pos = self._play_area.pos[0], self._play_area.pos[1]
    self._play_area.bind(size=lambda *_: self._update_play_area_cards())

    # When a marriage is announced, this stores the details of the card that is
    # only shown and not played, in order to return it to the player's hand when
    # the trick is completed.
    self._marriage_card: Optional[Tuple[PlayerId, CardWidget]] = None

    # Widgets that store the cards.
    self._player_card_widgets: Optional[PlayerPair[CardSlotsLayout]] = None
    self._tricks_widgets: Optional[PlayerPair[CardSlotsLayout]] = None
    self._talon: Optional[TalonWidget] = None

    # Labels used to display the trick points and game points.
    self._trick_score_labels: PlayerPair[Label] = PlayerPair(
      one=self.ids.human_trick_score_label.__self__,
      two=self.ids.computer_trick_score_label.__self__)
    self._game_score_labels: PlayerPair[Label] = PlayerPair(
      one=self.ids.human_game_score_label.__self__,
      two=self.ids.computer_game_score_label.__self__)

    # Stores the callback that is passed by the GameController when it requests
    # a new player action.
    self._action_callback: Optional[Callable[[PlayerAction], None]] = None

    # When a player action is requested, this dict stores the default action
    # associated to each card that can be double clicked.
    self._actions: Dict[CardWidget, PlayerAction] = {}

    # Function executed when a card is double clicked.
    def card_action_callback(card_widget: CardWidget):
      self._reply_with_action(self._actions[card_widget])

    # When request_next_action() is called, we bind this callback to all the
    # cards that have an associated available action. We need to store a
    # reference to this callback, since we want to unbind it from all cards once
    # the player picks an action.
    self._card_action_callback = card_action_callback

    self._init_widgets()

  def _init_widgets(self):
    self._init_cards()
    self._init_tricks_widgets()
    self._init_cards_in_hand_widgets()
    self._init_talon_widget()
    self.do_layout()

  def _init_cards(self):
    self._cards = CardWidget.create_widgets_for_all_cards()
    for card_widget in self._cards.values():
      card_widget.bind(on_card_moved=self._on_card_moved)

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

  def reset(self) -> None:
    """
    Resets the GameWidget and leaves it ready to be initialized from a new game
    state.
    """
    _delete_widget(self._player_card_widgets.one)
    _delete_widget(self._player_card_widgets.two)
    self._player_card_widgets = None
    _delete_widget(self._talon)
    _delete_widget(self._tricks_widgets.one)
    _delete_widget(self._tricks_widgets.two)
    self._tricks_widgets = None
    for card_widget in self._cards.values():
      _delete_widget(card_widget)
    self._cards = {}
    self._marriage_card = None
    self._init_widgets()

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
    return self._play_area

  @property
  def trick_score_labels(self) -> PlayerPair[Label]:
    """
    Returns the pair of labels used to display the trick points for each player.
    """
    return self._trick_score_labels

  @property
  def game_score_labels(self) -> PlayerPair[Label]:
    """
    Returns the pair of labels used to display the game points for each player.
    """
    return self._game_score_labels

  def init_from_game_state(self, game_state: GameState,
                           game_score: PlayerPair[int] = PlayerPair(0,
                                                                    0)) -> None:
    """
    Updates this GameWidget such that it represents the game state provided as
    an argument. It does not hold a reference to the game_state object. This
    GameWidget will not update itself automatically if subsequent changes are
    performed on the game_state object.
    Optionally, one can pass the Bummerl game score through the game_score arg.
    """
    # TODO(ui): Remove this hack once Card.visible is available.
    for card_widget in self._cards.values():
      card_widget.visible = False
    for suit in game_state.marriage_suits.one + game_state.marriage_suits.two:
      self._cards[Card(suit, CardValue.QUEEN)].visible = True
      self._cards[Card(suit, CardValue.KING)].visible = True

    # Init the cards for each player.
    self._update_cards_in_hand(game_state.cards_in_hand)

    # Init the won tricks for each player.
    for player in PlayerId:
      for trick in game_state.won_tricks[player]:
        self._cards[trick.one].visible = True
        self._tricks_widgets[player].add_card(self._cards[trick.one])
        self._cards[trick.two].visible = True
        self._tricks_widgets[player].add_card(self._cards[trick.two])

    # Init the trump card and the talon.
    if game_state.trump_card is not None:
      self._talon.set_trump_card(self._cards[game_state.trump_card])
    for i, card in enumerate(reversed(game_state.talon)):
      card_widget = self._cards[card]
      card_widget.visible = False
      if i != 0:
        card_widget.shadow = False
      self._talon.push_card(card_widget)

    if game_state.is_talon_closed:
      self._talon.closed = True

    # TODO(ui): If the current_trick is not empty, play a card to the play area.

    # Init the scores.
    self.on_score_modified(game_state.trick_points)
    self._update_game_score(game_score)

  def on_score_modified(self, score: PlayerPair[int]) -> None:
    """
    This method should be called whenever the trick points need to be updated.
    :param score: The updated value for trick points.
    """
    score_template = "[color=%s]Trick points: %s[/color]"
    color = _get_trick_points_color(score.one)
    self._trick_score_labels.one.text = score_template % (color, score.one)
    color = _get_trick_points_color(score.two)
    self._trick_score_labels.two.text = score_template % (color, score.two)

  def _update_game_score(self, score: PlayerPair[int]) -> None:
    assert 0 <= score.one < 7 and 0 <= score.two < 7, "Invalid game score"
    score_template = "[color=%s]Game points: %s[/color]"
    color = _get_game_points_color(score.one)
    self._game_score_labels.one.text = score_template % (color, 7 - score.one)
    color = _get_game_points_color(score.two)
    self._game_score_labels.two.text = score_template % (color, 7 - score.two)

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
    trump_jack_widget.grayed_out = False
    card_slots_widget = self._player_card_widgets[player]
    row, col = card_slots_widget.remove_card(trump_jack_widget)
    assert row is not None and col is not None, \
      "Trump Jack not in player's hand"
    trump_card_widget = self._talon.remove_trump_card()
    trump_card_widget.rotation = 0
    # TODO(ui): Sort the cards in hand.
    card_slots_widget.add_card(trump_card_widget, row, col)
    if player == PlayerId.ONE:
      trump_card_widget.grayed_out = True
    self._talon.set_trump_card(trump_jack_widget)

  def _get_card_pos_delta(self, player) -> Tuple[int, int]:
    """
    Position delta that should be used to avoid card overlaps when multiple
    cards should be moved roughly to the same position.

    Examples:
    * separate cards that are played to the center of the play area by double
    clicking on them instead of dragging;
    * separate the cards in a marriage when it is announced.

    :param player: The player that plays the card. For PlayerId.ONE the deltas
    move the second card towards the bottom-left corner. For PlayerId.TWO the
    deltas move the second card towards the upper-right corner.
    """
    delta = self._player_card_widgets[player].card_size
    if player == PlayerId.ONE:
      delta = -delta[0], -delta[1]
    return 0.2 * delta[0], 0.2 * delta[1]

  def _move_player_card_to_play_area(self, player: PlayerId, card: Card,
                                     center: Optional[
                                       Tuple[int, int]] = None) -> None:
    """
    Move the card given as argument from the player's hand to the play area.
    :param player: The player holding the card to be moved.
    :param card: The card to be moved.
    :param center: The position of the center of the card after the move.
    """
    card_widget = self._cards[card]
    card_widget.visible = True
    card_widget.grayed_out = False
    if card_widget.parent != self._play_area:
      logging.info("GameWidget: Moving %s to play area.", card)
      card_slots_widget = self._player_card_widgets[player]
      if center is None:
        center = self._get_default_play_location(player)
      pos = card_slots_widget.remove_card(card_widget)
      assert pos[0] is not None, "Player %s does not hold %s" % (player, card)
      self._play_area.add_widget(card_widget)
      card_widget.size = self.player_card_widgets.one.card_size
      card_widget.center = center[0], center[1]

  def _get_default_play_location(self, player: PlayerId) -> Tuple[int, int]:
    """
    Returns the coordinates where a card should be moved when it is played
    without using dragging (i.e., it's a card played by the computer or the user
    double-clicked it instead of dragging it).
    """
    pos = self._play_area.center
    for widget in self._play_area.children:
      if isinstance(widget, CardWidget):
        pos = widget.center
        delta = self._get_card_pos_delta(player)
        pos = pos[0] + delta[0], pos[1] + delta[1]
        break
    return pos[0], pos[1]

  def _update_play_area_cards(self) -> None:
    """
    Whenever the size of the play area changes (because the size of the
    GameWidget changes), we resize the cards to match the size of the cards in
    the player's hand and we reposition them proportionally to the new size of
    the play area.
    """
    for widget in self._play_area.children:
      if not isinstance(widget, CardWidget):
        continue
      new_center_x = (widget.center[0] - self._prev_play_area_pos[0]) / \
                     self._prev_play_area_size[0] * self._play_area.size[0]
      new_center_y = (widget.center[1] - self._prev_play_area_pos[1]) / \
                     self._prev_play_area_size[1] * self._play_area.size[1]
      widget.size = self.player_card_widgets.one.card_size
      widget.center = self._play_area.pos[0] + new_center_x, \
                      self._play_area.pos[1] + new_center_y
    self._prev_play_area_size = self._play_area.size[0], self._play_area.size[1]
    self._prev_play_area_pos = self._play_area.pos[0], self._play_area.pos[1]

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
    elif isinstance(action, PlayCardAction):
      self._move_player_card_to_play_area(action.player_id, action.card)
    elif isinstance(action, AnnounceMarriageAction):
      center = self._get_default_play_location(action.player_id)
      delta = self._get_card_pos_delta(action.player_id)
      pair_center = center[0] + delta[0], center[1] + delta[1]
      self._marriage_card = (action.player_id,
                             self._cards[action.card.marriage_pair])
      self._move_player_card_to_play_area(action.player_id,
                                          action.card.marriage_pair,
                                          pair_center)
      self._move_player_card_to_play_area(action.player_id, action.card, center)
    else:
      assert False, "Should not reach this code"

  def on_trick_completed(self, trick: Trick, winner: PlayerId) -> None:
    """
    This method should be called whenever a trick is completed in a game of
    Schnapsen, in order to update the state of this GameWidget accordingly.
    :param trick: The trick that just got completed.
    :param winner: The player that won the trick.
    """
    tricks_widget = self._tricks_widgets[winner]

    # TODO(ui): Make sure translations are disabled after the card is dropped on
    # the play area.
    for card in [trick.one, trick.two]:
      card_widget = self._cards[card]
      self._play_area.remove_widget(card_widget)
      tricks_widget.add_card(card_widget)

    # In case there was a marriage, move the card that was not played back to
    # the player's hand.
    if self._marriage_card is not None:
      player, card_widget = self._marriage_card
      self._play_area.remove_widget(card_widget)
      self._player_card_widgets[player].add_card(card_widget)
      self._marriage_card = None

  def on_new_cards_drawn(self, cards_in_hand: PlayerPair[List[Card]]) -> None:
    """
    This method should be called every time new cards are drawn from the talon
    after a trick is completed, in order to update the state of this GameWidget
    accordingly.
    :param cards_in_hand: The updated list of cards that each play holds.
    """
    self._talon.pop_card()
    if self._talon.pop_card() is None:
      # TODO(ui): Leave an image with the trump suit.
      # TODO(ui): If talon is empty maybe show opponent cards in hand as well.
      trump_card = self._talon.remove_trump_card()
      trump_card.rotation = 0
    self._update_cards_in_hand(cards_in_hand)

  def _update_cards_in_hand(self,
                            cards_in_hand: PlayerPair[List[Card]]) -> None:
    for player in PlayerId:
      for col in range(5):
        self._player_card_widgets[player].remove_card_at(0, col)

      # noinspection PyTypeChecker
      for i, card in enumerate(sorted(cards_in_hand[player])):
        # TODO(ui): Sort this by visibility and then randomize the hidden ones.
        card_widget = self._cards[card]
        self._player_card_widgets[player].add_card(card_widget, 0, i)
        card_widget.do_translation = False
        card_widget.shadow = True
        if player == PlayerId.ONE:
          card_widget.visible = True
          card_widget.grayed_out = True

  def request_next_action(self, game_state: GameState,
                          callback: Callable[[PlayerAction], None]) -> None:
    available_actions = get_available_actions(game_state)
    logging.info("GameWidget: Action requested. Available actions are: %s",
                 available_actions)
    self._action_callback = callback

    for action in available_actions:
      if isinstance(action, ExchangeTrumpCardAction):
        self._bind_card_action(self._talon.trump_card, action)
      elif isinstance(action, CloseTheTalonAction):
        self._bind_card_action(self._talon.top_card(), action)
      elif isinstance(action, (AnnounceMarriageAction, PlayCardAction)):
        card = self._cards[action.card]
        card.grayed_out = False
        self._bind_card_action(card, action)
        card.do_translation = True
        if isinstance(action, AnnounceMarriageAction):
          card.bind(on_transform_with_touch=self._on_transform_with_touch)
      else:  # pragma: no cover
        assert False, "Should not be reachable"

  def _bind_card_action(self, card: CardWidget, action: PlayerAction) -> None:
    self._actions[card] = action
    card.bind(on_double_tap=self._card_action_callback)

  def _reply_with_action(self, action: PlayerAction) -> None:
    """
    This method is executed once the player decided which is the next action
    they want to play. We call the callback provided by the GameController when
    it called request_next_action() and we clear all the other card actions.
    :param action: The action that the player decided to execute.
    """
    logging.info("GameWidget: Executing action %s", action)
    for card_widget in self._actions:
      if card_widget.parent is self._player_card_widgets.one:
        card_widget.grayed_out = True
    self._clear_actions()
    callback = self._action_callback
    self._action_callback = None
    callback(action)

  def _clear_actions(self):
    """
    Remove all actions associated to a card. Unbinds all double-click callbacks.
    """
    for card_widget in self._actions:
      card_widget.unbind(on_double_tap=self._card_action_callback)
      card_widget.unbind(on_transform_with_touch=self._on_transform_with_touch)
      card_widget.do_translation = False
    self._actions = {}

  def _on_card_moved(self, card_widget: CardWidget,
                     center: Tuple[int, int]) -> None:
    # If the card is dragged onto the play area, play it.
    if self._play_area.collide_point(*center):
      logging.info("GameWidget: Card %s was dragged to the playing area",
                   card_widget)

      action = self._actions[card_widget]

      # If the player announces a marriage, first move the un-played card to the
      # play area, so it will be displayed under the card that is played.
      if isinstance(action, AnnounceMarriageAction):
        marriage_pair_widget = self._cards[card_widget.card.marriage_pair]
        self._player_card_widgets.one.remove_card(marriage_pair_widget)
        self._play_area.add_widget(marriage_pair_widget)

      self._player_card_widgets.one.remove_card(card_widget)
      self._play_area.add_widget(card_widget)
      self._reply_with_action(action)
      return

    # If the trump jack is dragged onto the trump card, exchange the trump card,
    # if this action is available.
    if self._talon.trump_card is not None:
      if card_widget == self._get_trump_jack_widget():
        action = self._actions.get(self._talon.trump_card, None)
        if action is not None:
          if self._talon.trump_card.collide_point(*center):
            self._reply_with_action(action)
            return

    # If the card is dragged anywhere else, trigger a call to do_layout() which
    # will bring the dragged card back to the player's hand before the next
    # frame is drawn.
    self._player_card_widgets.one.trigger_layout()

  def _on_transform_with_touch(self, card_widget: CardWidget, _) -> None:
    """
    This method is called whenever a marriage card is dragged by the user to a
    new position, so we can update the position of the marriage pair card
    accordingly.
    :param card_widget: The CardWidget that got dragged.
    """
    pos = card_widget.pos
    delta = self._get_card_pos_delta(PlayerId.ONE)
    pos = pos[0] + delta[0], pos[1] + delta[1]
    marriage_pair_widget = self._cards[card_widget.card.marriage_pair]
    marriage_pair_widget.pos = pos


if __name__ == "__main__":
  game_widget = GameWidget()
  game_widget.size_hint = 1, 1
  game_widget.init_from_game_state(get_game_state_for_tests())
  game_widget.do_layout()
  runTouchApp(game_widget)
