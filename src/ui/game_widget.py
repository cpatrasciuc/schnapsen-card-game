#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import copy
import logging
import os.path
from typing import Dict, Tuple, Optional, List, Callable

from kivy.animation import Animation
from kivy.base import runTouchApp
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
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
from model.suit import Suit
from ui.animation_controller import AnimationController
from ui.card_slots_layout import CardSlotsLayout
from ui.card_widget import CardWidget
from ui.game_options import GameOptions
from ui.player import Player
from ui.talon_widget import TalonWidget

Closure = Callable[[], None]


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


def _remove_card_children(widget: Widget) -> List[CardWidget]:
  """Removes all CardWidget children of widget and returns them as a list."""
  cards_children = [child for child in widget.children if
                    isinstance(child, CardWidget)]
  for child in cards_children:
    widget.remove_widget(child)
  return cards_children


def _delete_widget(widget: Widget) -> None:
  if widget.parent is not None:
    widget.parent.remove_widget(widget)
  del widget


def _sort_cards_for_player(cards: List[Card], player: PlayerId) -> List[Card]:
  """
  For the human player (ONE), it sorts the cards in hand based on suit first and
  then card value. For the computer player (TWO), it sorts the public cards by
  suit and then card value. The non-public cards are left as they are.
  """
  cards_copy = copy.deepcopy(cards)
  if player == PlayerId.ONE:
    # noinspection PyTypeChecker
    return list(sorted(cards_copy))
  public_cards = [card for card in cards_copy if card.public]
  non_public_cards = [card for card in cards_copy if not card.public]
  # noinspection PyTypeChecker
  return list(sorted(public_cards)) + non_public_cards


def _get_card_list(card_slots_widget: CardSlotsLayout) -> List[Card]:
  cards = []
  for col in range(5):
    card_widget = card_slots_widget.at(0, col)
    if card_widget is None:
      continue
    card = card_widget.card
    card.public = card_widget.visible
    cards.append(card_widget.card)
  return cards


# TODO(tests): Add tests for padding_pct.
Builder.load_file(os.path.join(os.path.dirname(__file__), "game_widget.kv"),
                  rulesonly=True)


class GameWidgetMeta(FloatLayout.__metaclass__, Player.__metaclass__):
  pass


class GameWidget(FloatLayout, Player, metaclass=GameWidgetMeta):
  """The main widget used to view/play a game of Schnapsen."""

  # pylint: disable=too-many-instance-attributes

  def __init__(self, game_options: Optional[GameOptions] = None, **kwargs):
    """
    Instantiates a new GameWidget and all its children widgets. All the widgets
    are empty (i.e., no cards).
    """
    # Store or initialize the game options. This has to be done before the call
    # to Widget.__init__() so the options are available when the game_widget.kv
    # file is parsed.
    self._game_options = game_options or GameOptions()

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

    # The cards in the players' hands, sorted in display order.
    self._sorted_cards: Optional[PlayerPair[List[Card]]] = None

    # Widgets that store the cards.
    self._player_card_widgets: Optional[PlayerPair[CardSlotsLayout]] = None
    self._tricks_widgets: Optional[PlayerPair[CardSlotsLayout]] = None
    self._talon: Optional[TalonWidget] = None

    # Image that displays the trump suit, if the talon is empty.
    self._trump_suit_image: Optional[Image] = None

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

    # AnimationController that coordinates all card animations.
    self._animation_controller = AnimationController()
    self.fbind('size', self._cancel_animations)

    self._init_widgets()

  def _init_widgets(self):
    self._init_cards()
    self._init_tricks_widgets()
    self._init_cards_in_hand_widgets()
    self._init_talon_widget()
    self.do_layout()

  def _init_cards(self):
    self._cards = CardWidget.create_widgets_for_all_cards(
      path=self._game_options.cards_path)
    for card_widget in self._cards.values():
      card_widget.bind(on_card_moved=self._on_card_moved)

  def _init_talon_widget(self):
    self._talon = TalonWidget(delta_pct=0.005)
    self._talon.size_hint = 1, 1
    self._talon.pos_hint = {'x': 0, 'y': 0}
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

  def _init_trump_suit_image(self, suit: Suit):
    image_filename = str(suit.name.lower())[0] + ".png"
    image_full_path = os.path.join(self._game_options.cards_path,
                                   image_filename)
    self._trump_suit_image = Image(source=image_full_path)
    self._trump_suit_image.size_hint = None, None
    self._trump_suit_image.opacity = 0
    self.ids.talon_placeholder.add_widget(self._trump_suit_image)

    def center_trump_image_inside_talon_widget(*_):
      size = min(self._talon.size) / 2
      self._trump_suit_image.size = size, size
      self._trump_suit_image.center = self._talon.center

    center_trump_image_inside_talon_widget()
    self._talon.bind(center=center_trump_image_inside_talon_widget)
    self._talon.bind(size=center_trump_image_inside_talon_widget)

  def _cancel_animations(self, *_):
    if self._animation_controller.is_running:
      self._animation_controller.cancel()

  def reset(self) -> None:
    """
    Resets the GameWidget and leaves it ready to be initialized from a new game
    state.
    """
    self._trigger_layout.cancel()
    self._cancel_animations()
    _delete_widget(self._player_card_widgets.one)
    _delete_widget(self._player_card_widgets.two)
    self._player_card_widgets = None
    _delete_widget(self._talon)
    if self._trump_suit_image is not None:
      _delete_widget(self._trump_suit_image)
      self._trump_suit_image = None
    _delete_widget(self._tricks_widgets.one)
    _delete_widget(self._tricks_widgets.two)
    self._tricks_widgets = None
    for card_widget in self._cards.values():
      _delete_widget(card_widget)
    self._cards = {}
    self._sorted_cards = None
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

  @property
  def trump_suit_image(self) -> Optional[Image]:
    """
    Returns the image used to display the trump suit when the talon is empty.
    """
    return self._trump_suit_image

  def init_from_game_state(self, game_state: GameState, done_callback: Closure,
                           game_score: PlayerPair[int] = PlayerPair(0,
                                                                    0)) -> None:
    """
    Updates this GameWidget such that it represents the game state provided as
    an argument. It does not hold a reference to the game_state object. This
    GameWidget will not update itself automatically if subsequent changes are
    performed on the game_state object.
    :param game_state The initial game_state that this widget should represent.
    :param done_callback The closure that should be called once the GameWidget
    has finished initializing itself.
    :param game_score The Bummerl game score.
    """
    # Init the cards for each player.
    self._sorted_cards = PlayerPair(
      _sort_cards_for_player(game_state.cards_in_hand.one, PlayerId.ONE),
      _sort_cards_for_player(game_state.cards_in_hand.two, PlayerId.TWO))
    self._update_cards_in_hand_after_animation()

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

    # Init the scores.
    self.on_score_modified(game_state.trick_points)
    self._update_game_score(game_score)

    # Set the trump image source here since we know what the trump suit is, but
    # only make it visible when the talon is empty.
    self._init_trump_suit_image(game_state.trump)

    # If a card is already played check if it was a simple card play or a
    # marriage announcement and execute the corresponding action.
    for player in PlayerId:
      card = game_state.current_trick[player]
      if card is None:
        continue
      if card.suit in game_state.marriage_suits[player] and \
          card.card_value in [CardValue.QUEEN, CardValue.KING] and \
          card.marriage_pair in game_state.cards_in_hand[player]:
        action = AnnounceMarriageAction(player, card)
      else:
        action = PlayCardAction(player, card)
      # pylint: disable=cell-var-from-loop
      Clock.schedule_once(lambda *_: self.on_action(action, done_callback), -1)
      # pylint: enable=cell-var-from-loop
      return

    # If we didn't call on_action() above, we are done with the initialization.
    # If animations are enabled, we just flip the cards in the human player's
    # hand.
    Clock.schedule_once(
      lambda *_: self._flip_human_player_cards(game_state, done_callback), -1)

  def _flip_human_player_cards(self, game_state: GameState,
                               done_callback: Closure) -> None:
    for card in game_state.cards_in_hand.one:
      card_widget = self._cards[card]
      card_widget.visible = False
      card_widget.check_aspect_ratio(False)
      self._player_card_widgets.one.remove_card(card_widget)
      self.add_widget(card_widget)
      animation = card_widget.get_flip_animation(
        self._game_options.draw_cards_duration, True)
      self._add_animation(card_widget, animation)
    self._animation_controller.start(
      lambda: self._update_cards_in_hand_after_animation(done_callback))

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

  def _animate_exchange_trump_card(self, player: PlayerId) -> None:
    trump_jack_widget = self._get_trump_jack_widget()
    trump_jack_widget.grayed_out = False
    card_slots_widget = self._player_card_widgets[player]
    row, col = card_slots_widget.remove_card(trump_jack_widget)
    assert row is not None and col is not None, \
      "Trump Jack not in player's hand"
    trump_card_widget = self._talon.remove_trump_card()
    self.add_widget(trump_card_widget, index=len(self.children))
    self.add_widget(trump_jack_widget)

    exchange_pos = self._get_trump_exchange_pos()
    duration = self._game_options.exchange_trump_duration
    trump_jack_animation = Animation(center_x=exchange_pos[0],
                                     center_y=exchange_pos[1],
                                     duration=duration / 2)
    if not trump_jack_widget.visible:
      trump_jack_widget.check_aspect_ratio(False)
      trump_jack_animation &= trump_jack_widget.get_flip_animation(
        duration / 2, False)
    trump_jack_animation += Animation(rotation=90,
                                      center_x=trump_card_widget.center_x,
                                      center_y=trump_card_widget.center_y,
                                      duration=duration / 4)
    self._add_animation(trump_jack_widget, trump_jack_animation)

    cards_in_hand = _get_card_list(card_slots_widget)
    cards_in_hand.append(trump_card_widget.card)
    cards_in_hand[-1].public = True
    assert len(cards_in_hand) == 5, \
      "Cannot exchange trump with less then five cards in hand"
    self._sorted_cards[player] = _sort_cards_for_player(cards_in_hand, player)

    def bring_trump_card_to_front(*_):
      self.remove_widget(trump_card_widget)
      self.add_widget(trump_card_widget)
      self.remove_widget(trump_jack_widget)
      self.add_widget(trump_jack_widget, index=len(self.children))

    trump_card_col = self._sorted_cards[player].index(trump_card_widget.card)
    pos = card_slots_widget.get_card_pos(0, trump_card_col)
    pos = pos[0] + trump_jack_widget.width / 2, \
          pos[1] + trump_jack_widget.height / 2
    trump_card_animation = Animation(center_x=exchange_pos[0],
                                     center_y=exchange_pos[1],
                                     rotation=0,
                                     duration=duration / 4)
    trump_card_animation.bind(on_complete=bring_trump_card_to_front)
    trump_card_animation += Animation(center_x=pos[0], center_y=pos[1],
                                      duration=duration / 2)
    self._add_animation(trump_card_widget, trump_card_animation)
    self._animate_cards_for_player(player, duration=duration / 4,
                                   skip_cards=[trump_card_widget.card])

  def _get_trump_exchange_pos(self):
    exchange_pos = self._talon.pos[0], \
                   self._talon.pos[1] + self._talon.height / 2
    return exchange_pos

  def _exchange_trump_card(self, player: PlayerId) -> None:
    card_children = _remove_card_children(self)
    assert len(card_children) == 2
    jack_card_children = [child for child in card_children if
                          child.card.card_value == CardValue.JACK]
    assert len(jack_card_children) == 1
    trump_jack_widget = jack_card_children[0]
    trump_jack_widget.check_aspect_ratio(True)
    self._talon.set_trump_card(trump_jack_widget)

    card_children.remove(trump_jack_widget)
    trump_card_widget = card_children[0]
    trump_card_widget.rotation = 0
    self._player_card_widgets[player].add_card(trump_card_widget)
    if player == PlayerId.ONE:
      trump_card_widget.grayed_out = True

    self._update_cards_in_hand_for_player_after_animation(player)

  def _animate_talon_closed(self):
    trump_card_widget = self._talon.remove_trump_card()
    self.add_widget(trump_card_widget, index=len(self.children))
    exchange_pos = self._get_trump_exchange_pos()
    duration = self._game_options.close_talon_duration
    trump_card_animation = Animation(center_x=exchange_pos[0],
                                     center_y=exchange_pos[1],
                                     rotation=40,
                                     duration=duration / 2)

    def bring_trump_card_to_front(*_):
      self.remove_widget(trump_card_widget)
      self.add_widget(trump_card_widget)

    trump_card_animation.bind(on_complete=bring_trump_card_to_front)
    pos = self._talon.top_card().center
    trump_card_animation += Animation(center_x=pos[0], center_y=pos[1],
                                      rotation=10, duration=duration / 2)
    self._add_animation(trump_card_widget, trump_card_animation)

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

  def _animate_card_to_play_area(self, player: PlayerId, card: Card,
                                 center: Optional[
                                   Tuple[int, int]] = None) -> None:
    card_widget = self._cards[card]
    duration = self._game_options.play_card_duration
    if card_widget.parent is not self._play_area:
      card_widget.grayed_out = False
      card_slots_widget = self._player_card_widgets[player]
      pos = card_slots_widget.remove_card(card_widget)
      assert pos[0] is not None, "Player %s does not hold %s" % (player, card)
      self.add_widget(card_widget)
      if center is None:
        center = self._get_default_play_location(player)
      animation = Animation(center_x=center[0], center_y=center[1],
                            duration=duration)
      if not card_widget.visible:
        card_widget.check_aspect_ratio(False)
        animation &= card_widget.get_flip_animation(duration, False)
      self._add_animation(card_widget, animation)

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
    if card_widget.parent != self._play_area:
      logging.info("GameWidget: Moving %s to play area.", card)
      if center is None:
        center = self._get_default_play_location(player)
      self.remove_widget(card_widget)
      self._play_area.add_widget(card_widget)
      card_widget.visible = True
      card_widget.check_aspect_ratio(True)
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

  def on_action(self, action: PlayerAction, done_callback: Closure) -> None:
    """
    This method should be called whenever a new player action was performed in a
    game of Schnapsen, in order to update the state of the widget accordingly.
    :param action: The latest action performed by one of the players.
    :param done_callback: The closure to be called once the GameWidget is done
    updating itself according to the player action.
    """
    logging.info("GameWidget: on_action: %s", action)
    if isinstance(action, ExchangeTrumpCardAction):
      self._animate_exchange_trump_card(action.player_id)
    elif isinstance(action, CloseTheTalonAction):
      self._animate_talon_closed()
    elif isinstance(action, PlayCardAction):
      self._animate_card_to_play_area(action.player_id, action.card)
    elif isinstance(action, AnnounceMarriageAction):
      center = self._get_default_play_location(action.player_id)
      delta = self._get_card_pos_delta(action.player_id)
      pair_center = center[0] + delta[0], center[1] + delta[1]
      self._animate_card_to_play_area(action.player_id,
                                      action.card.marriage_pair,
                                      pair_center)
      self._animate_card_to_play_area(action.player_id, action.card)
    else:
      assert False, "Should not reach this code"
    assert not self._animation_controller.is_running
    self._animation_controller.start(
      lambda: self._on_action_after_animations(action, done_callback))

  def _on_action_after_animations(self, action: PlayerAction,
                                  done_callback: Closure) -> None:
    if isinstance(action, ExchangeTrumpCardAction):
      self._exchange_trump_card(action.player_id)
    elif isinstance(action, CloseTheTalonAction):
      card_children = _remove_card_children(self)
      assert len(card_children) == 1, card_children
      trump_card_widget = card_children[0]
      self._talon.set_trump_card(trump_card_widget)
      self._talon.closed = True
    elif isinstance(action, PlayCardAction):
      self._move_player_card_to_play_area(action.player_id, action.card)
    elif isinstance(action, AnnounceMarriageAction):
      center = self._get_default_play_location(action.player_id)
      delta = self._get_card_pos_delta(action.player_id)
      pair_center = center[0] + delta[0], center[1] + delta[1]
      self._move_player_card_to_play_area(action.player_id,
                                          action.card.marriage_pair,
                                          pair_center)
      self._move_player_card_to_play_area(action.player_id, action.card, center)
    else:
      assert False, "Should not reach this code"  # pragma: no cover
    done_callback()

  # pylint: disable=too-many-arguments
  def on_trick_completed(self, trick: Trick, winner: PlayerId,
                         cards_in_hand: PlayerPair[List[Card]],
                         draw_new_cards: bool,
                         done_callback: Closure) -> None:
    """
    This method should be called whenever a trick is completed in a game of
    Schnapsen, in order to update the state of this GameWidget accordingly.
    :param trick: The trick that just got completed.
    :param winner: The player that won the trick.
    :param cards_in_hand: The updated list of cards that each player holds.
    :param draw_new_cards: If True, it means that each player drew a new card
    from the talon at the end of the trick.
    :param done_callback Closure to be called when the GameWidget has finished
    updating itself based on this trick-completed event.
    """
    assert not self._animation_controller.is_running

    # Move the cards from the play area to self and keep the same z-order.
    for child in reversed(self._play_area.children):
      if not isinstance(child, CardWidget):
        continue
      if child.card not in [trick.one, trick.two]:
        continue
      self._play_area.remove_widget(child)
      self.add_widget(child)

    tricks_widget = self._tricks_widgets[winner]
    duration = self._game_options.trick_completed_duration

    # Animate the first card.
    row, col = tricks_widget.first_free_slot
    pos = tricks_widget.get_card_pos(row, col)
    size = tricks_widget.card_size
    card_widget = self._cards[trick.one]
    card_widget.check_aspect_ratio(False)
    self._add_animation(card_widget,
                        Animation(x=pos[0], y=pos[1], width=size[0],
                                  height=size[1], duration=duration))

    # Animate the second card.
    pos = tricks_widget.get_card_pos(row, col + 1)
    card_widget = self._cards[trick.two]
    card_widget.check_aspect_ratio(False)
    self._add_animation(card_widget,
                        Animation(x=pos[0], y=pos[1], width=size[0],
                                  height=size[1], duration=duration))

    # Update the list of sorted cards for each player.
    self._sorted_cards = PlayerPair(
      _sort_cards_for_player(cards_in_hand.one, PlayerId.ONE),
      _sort_cards_for_player(cards_in_hand.two, PlayerId.TWO))

    self._animation_controller.start(
      lambda: self._on_trick_completed_after_animations(trick, winner,
                                                        draw_new_cards,
                                                        done_callback))

  # pydgdgdlint: disable=too-many-arguments
  def _on_trick_completed_after_animations(self, trick: Trick, winner: PlayerId,
                                           draw_new_cards: bool,
                                           done_callback: Closure) -> None:
    tricks_widget = self._tricks_widgets[winner]

    for card in [trick.one, trick.two]:
      card_widget = self._cards[card]
      self.remove_widget(card_widget)
      tricks_widget.add_card(card_widget)
      card_widget.check_aspect_ratio(True)

    if draw_new_cards:
      first_card = self._talon.pop_card()
      self.add_widget(first_card)
      second_card = self._talon.pop_card()
      if second_card is None:
        # TODO(ui): If talon is empty maybe show opponent cards in hand as well.
        second_card = self._talon.remove_trump_card()
      self.add_widget(second_card)
    self._update_cards_in_hand(done_callback)

  def _update_cards_in_hand(self, done_callback: Closure) -> None:
    duration = self._game_options.draw_cards_duration
    self._animate_cards_for_player(PlayerId.ONE, duration)
    self._animate_cards_for_player(PlayerId.TWO, duration)
    self._animation_controller.start(
      lambda: self._update_cards_in_hand_after_animation(done_callback))

  def _animate_cards_for_player(self, player: PlayerId, duration: float,
                                skip_cards: List[Card] = None) -> None:
    cards_slots_widget = self._player_card_widgets[player]
    for i, card in enumerate(self._sorted_cards[player]):
      if skip_cards is not None and card in skip_cards:
        continue
      card_widget = self._cards[card]
      card_widget.do_translation = False
      card_widget.shadow = True
      if cards_slots_widget.at(0, i) == card_widget:
        continue
      pos = cards_slots_widget.get_card_pos(0, i)
      size = cards_slots_widget.card_size
      card_widget.check_aspect_ratio(False)
      animation_params = {
        'x': pos[0], 'y': pos[1], 'width': size[0], 'height': size[1],
        'duration': duration
      }
      if card_widget.rotation != 0:
        animation_params['rotation'] = 0
      animation = Animation(**animation_params)
      if player == PlayerId.ONE and not card_widget.visible:
        animation &= card_widget.get_flip_animation(duration, False)
      self._add_animation(card_widget, animation)

  def _update_cards_in_hand_after_animation(self,
                                            done_callback: Optional[
                                              Closure] = None) -> None:
    self._update_cards_in_hand_for_player_after_animation(PlayerId.ONE)
    self._update_cards_in_hand_for_player_after_animation(PlayerId.TWO)
    if self._talon.top_card() is None and self._trump_suit_image is not None:
      self._trump_suit_image.opacity = 1
    if done_callback is not None:
      done_callback()

  def _update_cards_in_hand_for_player_after_animation(self, player: PlayerId):
    for col in range(5):
      self._player_card_widgets[player].remove_card_at(0, col)
    _remove_card_children(self)
    _remove_card_children(self._play_area)

    for i, card in enumerate(self._sorted_cards[player]):
      card_widget = self._cards[card]
      card_widget.do_translation = False
      card_widget.shadow = True
      card_widget.rotation = 0
      if player == PlayerId.ONE:
        card_widget.visible = True
        card_widget.grayed_out = True
      else:
        card_widget.visible = card.public
      self._player_card_widgets[player].add_card(card_widget, 0, i)
      card_widget.check_aspect_ratio(True)

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

  def _card_action_callback(self, card_widget: CardWidget) -> None:
    """
    Function executed when a card is double clicked.
    :param card_widget: The card that was double-clicked.
    """
    self._reply_with_action(self._actions[card_widget])

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

  def _add_animation(self, card_widget: CardWidget,
                     animation: Animation) -> None:
    if not self._game_options.enable_animations:
      return
    self._animation_controller.add_card_animation(card_widget, animation)


if __name__ == "__main__":
  game_widget = GameWidget()
  game_widget.size_hint = 1, 1
  game_widget.init_from_game_state(get_game_state_for_tests(), lambda: None)
  runTouchApp(game_widget)
