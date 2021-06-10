#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# pylint: disable=too-many-lines,too-many-statements,too-many-locals
# pylint: disable=too-many-public-methods,too-many-ancestors

import logging
import random
from collections import Counter
from typing import Tuple, List, Optional
from unittest.mock import Mock

from kivy.base import EventLoop
from kivy.metrics import dp
from kivy.tests.common import UnitTestTouch

from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState, Trick
from model.game_state_test_utils import get_game_state_for_tests, \
  get_game_state_with_multiple_cards_in_the_talon_for_tests, \
  get_game_state_with_empty_talon_for_tests, \
  get_game_state_with_all_tricks_played
from model.game_state_validation import GameStateValidator
from model.player_action import ExchangeTrumpCardAction, CloseTheTalonAction, \
  PlayCardAction, AnnounceMarriageAction, PlayerAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit
from ui.card_widget import CardWidget
from ui.game_widget import GameWidget
from ui.test_utils import GraphicUnitTest


def _drag_card_to_pos(card_widget: CardWidget, position: Tuple[int, int]):
  touch = UnitTestTouch(*card_widget.center)
  touch.touch_down()
  touch.touch_move(*position)
  touch.touch_up()


class _GameWidgetBaseTest(GraphicUnitTest):
  @staticmethod
  def create_game_widget():
    return GameWidget(enable_animations=False)

  def _init_from_game_state(self, game_widget: GameWidget,
                            game_state: GameState,
                            game_score: Optional[PlayerPair[int]] = None):
    done_callback = Mock()
    if game_score is None:
      game_widget.init_from_game_state(game_state, done_callback)
    else:
      game_widget.init_from_game_state(game_state, done_callback, game_score)
    self.wait_for_mock_callback(done_callback)

  def _on_action(self, game_widget: GameWidget, action: PlayerAction):
    done_callback = Mock()
    game_widget.on_action(action, done_callback)
    self.wait_for_mock_callback(done_callback)

  # pylint: disable=too-many-arguments
  def _on_trick_completed(self, game_widget: GameWidget, trick: Trick,
                          winner: PlayerId,
                          cards_in_hand: PlayerPair[List[Card]],
                          draw_new_cards: bool):
    done_callback = Mock()
    game_widget.on_trick_completed(trick, winner, cards_in_hand, draw_new_cards,
                                   done_callback)
    self.wait_for_mock_callback(done_callback)


# TODO(tests): Refactor the animation durations in a GameOptions class and
# increase the duration here to make sure the animations get cancelled.
class _GameWidgetWithCancelledAnimations(GraphicUnitTest):
  """
  In these tests the window will be resized during any animation, causing it to
  get cancelled.
  """

  @staticmethod
  def create_game_widget():
    return GameWidget(enable_animations=True)

  def _resize_window(self):
    original_size = new_size = self.window.size
    while new_size == self.window.size:
      new_size = (random.randint(200, 400), random.randint(200, 400))
    logging.info(": window size: %s", new_size)
    # This should cancel the animations.
    self.window.size = new_size
    # Set the size back to the initial values, so the tests that use dimensions
    # or coordinates can succeed.
    self.window.size = int(original_size[0]), int(original_size[1])

  def _init_from_game_state(self, game_widget: GameWidget,
                            game_state: GameState,
                            game_score: Optional[PlayerPair[int]] = None):
    done_callback = Mock()
    if game_score is None:
      game_widget.init_from_game_state(game_state, done_callback)
    else:
      game_widget.init_from_game_state(game_state, done_callback, game_score)
    self.advance_frames(5)
    if game_state.is_game_over:
      done_callback.assert_called_once()
      return
    done_callback.assert_not_called()
    self._resize_window()
    self.wait_for_mock_callback(done_callback)
    self.advance_frames(1)

  def _on_action(self, game_widget: GameWidget, action: PlayerAction):
    done_callback = Mock()
    game_widget.on_action(action, done_callback)
    if done_callback.called:
      return

    self._resize_window()
    self.wait_for_mock_callback(done_callback)
    self.advance_frames(1)

  # pylint: disable=too-many-arguments
  def _on_trick_completed(self, game_widget: GameWidget, trick: Trick,
                          winner: PlayerId,
                          cards_in_hand: PlayerPair[List[Card]],
                          draw_new_cards: bool):
    done_callback = Mock()
    game_widget.on_trick_completed(trick, winner, cards_in_hand, draw_new_cards,
                                   done_callback)
    done_callback.assert_not_called()

    self._resize_window()
    self.wait_for_mock_callback(done_callback)
    self.advance_frames(1)


class GameWidgetInitTest(_GameWidgetBaseTest):
  def _assert_initial_game_widget_state(self, game_widget: GameWidget) -> None:
    # Creates all the cards without a parent widget.
    self.assertEqual(20, len(game_widget.cards.keys()))
    for card_widget in game_widget.cards.values():
      self.assertIsNone(card_widget.parent)

    # Tricks widgets are emtpy.
    trick_widgets = game_widget.tricks_widgets
    self.assertEqual(2, trick_widgets.one.rows)
    self.assertEqual(8, trick_widgets.one.cols)
    self.assertEqual((0, 0), trick_widgets.one.first_free_slot)
    self.assertEqual(2, trick_widgets.two.rows)
    self.assertEqual(8, trick_widgets.two.cols)
    self.assertEqual((0, 0), trick_widgets.two.first_free_slot)

    # No cards in players' hands.
    player_card_widgets = game_widget.player_card_widgets
    self.assertEqual(1, player_card_widgets.one.rows)
    self.assertEqual(5, player_card_widgets.one.cols)
    self.assertEqual((0, 0), player_card_widgets.one.first_free_slot)
    self.assertEqual(1, player_card_widgets.two.rows)
    self.assertEqual(5, player_card_widgets.two.cols)
    self.assertEqual((0, 0), player_card_widgets.two.first_free_slot)

    # No cards in the talon widget.
    self.assertIsNone(game_widget.talon_widget.pop_card())
    self.assertIsNone(game_widget.talon_widget.trump_card)

    counts = Counter(
      [widget.__class__.__name__ for widget in game_widget.walk()])
    self.assertEqual(4, counts["CardSlotsLayout"])
    self.assertEqual(1, counts["TalonWidget"])

  def test_create_empty_widget(self):
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._assert_initial_game_widget_state(game_widget)

  # pylint: disable=too-many-branches
  def _run_init_from_game_state(self, game_state: GameState,
                                played_cards: Optional[
                                  List[Card]] = None) -> GameWidget:
    if played_cards is None:
      played_cards = []

    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)
    card_widgets = game_widget.cards

    # Cards for each player are in the right widgets.
    player_card_widgets = game_widget.player_card_widgets
    for player in PlayerId:
      for card in game_state.cards_in_hand[player]:
        if card in played_cards:
          self.assertIs(game_widget.play_area, card_widgets[card].parent)
        else:
          self.assertIs(player_card_widgets[player], card_widgets[card].parent)
        self.assertEqual(player == PlayerId.ONE and card not in played_cards,
                         card_widgets[card].grayed_out)
        self.assert_do_translation(False, card_widgets[card])
        if player == PlayerId.ONE:
          self.assertTrue(card_widgets[card].visible)
        else:
          self.assertEqual(card.public, card_widgets[card].visible)

    # Cards for already played tricks are in the right widgets.
    tricks_widgets = game_widget.tricks_widgets
    for player in PlayerId:
      for trick in game_state.won_tricks[player]:
        self.assertIs(tricks_widgets[player], card_widgets[trick.one].parent)
        self.assertTrue(card_widgets[trick.one].visible)
        self.assertFalse(card_widgets[trick.one].grayed_out)
        self.assert_do_translation(False, card_widgets[trick.one])
        self.assertIs(tricks_widgets[player], card_widgets[trick.two].parent)
        self.assertTrue(card_widgets[trick.two].visible)
        self.assertFalse(card_widgets[trick.two].grayed_out)
        self.assert_do_translation(False, card_widgets[trick.two])

    # Trump card is correctly set.
    if game_state.trump_card is not None:
      self.assertIs(game_widget.talon_widget.trump_card,
                    card_widgets[game_state.trump_card])
      self.assertTrue(card_widgets[game_state.trump_card].visible)
      self.assertFalse(card_widgets[game_state.trump_card].grayed_out)
      self.assert_do_translation(False, card_widgets[game_state.trump_card])
    else:
      self.assertIsNone(game_widget.talon_widget.trump_card)

    # Remaining cards are in the talon.
    for card in game_state.talon:
      card_widget = game_widget.talon_widget.pop_card()
      self.assertEqual(card, card_widget.card)
      self.assertFalse(card_widget.visible)
      self.assertFalse(card_widget.grayed_out)
      self.assert_do_translation(False, card_widget)
      # Only the last talon card has shadow enabled.
      self.assertEqual(game_widget.talon_widget.top_card() is None,
                       card_widget.shadow)
    self.assertIsNone(game_widget.talon_widget.pop_card())
    self.assertEqual(game_state.is_talon_closed,
                     game_widget.talon_widget.closed)

    # If there are cards in the play area, they should have the same size as the
    # cards in the players hand.
    for child in game_widget.play_area.children:
      if isinstance(child, CardWidget):
        self.assertEqual(list(game_widget.player_card_widgets.one.card_size),
                         child.size)

    return game_widget

  def test_init_from_game_state(self):
    game_widget = self._run_init_from_game_state(get_game_state_for_tests())
    self.assertEqual(Card(Suit.DIAMONDS, CardValue.QUEEN),
                     game_widget.player_card_widgets.two.at(0, 0).card)

  def test_init_from_game_state_with_empty_talon(self):
    self._run_init_from_game_state(get_game_state_with_empty_talon_for_tests())

  def test_init_from_game_state_with_closed_talon(self):
    game_state = get_game_state_for_tests()
    game_state.close_talon()
    self._run_init_from_game_state(game_state)

  def test_init_from_game_state_with_all_tricks_played(self):
    self._run_init_from_game_state(get_game_state_with_all_tricks_played())

  def test_init_from_game_state_with_multiple_cards_in_the_talon(self):
    self._run_init_from_game_state(
      get_game_state_with_multiple_cards_in_the_talon_for_tests())

  def test_init_from_game_state_with_non_empty_current_trick(self):
    game_state = get_game_state_for_tests()
    played_card = Card(Suit.DIAMONDS, CardValue.QUEEN)
    with GameStateValidator(game_state):
      game_state.current_trick.two = played_card
    self._run_init_from_game_state(game_state, [played_card])

  def test_init_from_game_state_with_marriage_announced(self):
    game_state = get_game_state_for_tests()
    king_hearts = Card(Suit.HEARTS, CardValue.KING)
    with GameStateValidator(game_state):
      game_state.current_trick.one = king_hearts
      game_state.marriage_suits.one.append(Suit.HEARTS)
      game_state.cards_in_hand.one[0].public = True  # queen diamonds
      game_state.trick_points = PlayerPair(42, 53)
      game_state.next_player = PlayerId.TWO
    self._run_init_from_game_state(game_state,
                                   [king_hearts, king_hearts.marriage_pair])

  def test_init_form_game_state_with_game_score(self):
    test_cases = [
      (0, "[color=33aa33]Game points: 7[/color]"),
      (1, "[color=33aa33]Game points: 6[/color]"),
      (2, "[color=33aa33]Game points: 5[/color]"),
      (3, "[color=33aa33]Game points: 4[/color]"),
      (4, "[color=ffffff]Game points: 3[/color]"),
      (5, "[color=ffff33]Game points: 2[/color]"),
      (6, "[color=ff3333]Game points: 1[/color]"),
    ]
    for points, expected_text in test_cases:
      game_widget = self.create_game_widget()
      self.render(game_widget)
      self._init_from_game_state(game_widget, GameState.new(),
                                 PlayerPair(points, 0))
      self.assertEqual(expected_text, game_widget.game_score_labels.one.text)
      game_widget = self.create_game_widget()
      self.render(game_widget)
      self._init_from_game_state(game_widget, GameState.new(),
                                 PlayerPair(0, points))
      self.assertEqual(expected_text, game_widget.game_score_labels.two.text)
    with self.assertRaisesRegex(AssertionError, "Invalid game score"):
      game_widget = self.create_game_widget()
      self._init_from_game_state(game_widget, GameState.new(), PlayerPair(7, 4))
    with self.assertRaisesRegex(AssertionError, "Invalid game score"):
      game_widget = self.create_game_widget()
      self._init_from_game_state(game_widget, GameState.new(),
                                 PlayerPair(0, -1))

  def test_reset(self):
    game_widget = self.create_game_widget()
    self._assert_initial_game_widget_state(game_widget)
    self.render(game_widget)
    game_widget.reset()
    self._assert_initial_game_widget_state(game_widget)
    self._init_from_game_state(game_widget, GameState.new())
    with self.assertRaises(AssertionError):
      self._assert_initial_game_widget_state(game_widget)
    game_widget.reset()
    self._assert_initial_game_widget_state(game_widget)

  def test_on_score_modified(self):
    game_widget = self.create_game_widget()
    self.render(game_widget)
    test_cases = [
      (0, "[color=ff3333]Trick points: 0[/color]"),
      (1, "[color=ffff33]Trick points: 1[/color]"),
      (10, "[color=ffff33]Trick points: 10[/color]"),
      (32, "[color=ffff33]Trick points: 32[/color]"),
      (33, "[color=ffffff]Trick points: 33[/color]"),
      (40, "[color=ffffff]Trick points: 40[/color]"),
      (65, "[color=ffffff]Trick points: 65[/color]"),
      (66, "[color=33ff33]Trick points: 66[/color]"),
      (80, "[color=33ff33]Trick points: 80[/color]"),
    ]
    for points, expected_text in test_cases:
      game_widget.on_score_modified(PlayerPair(points, 0))
      self.assertEqual(expected_text, game_widget.trick_score_labels.one.text)
      game_widget.on_score_modified(PlayerPair(0, points))
      self.assertEqual(expected_text, game_widget.trick_score_labels.two.text)


class GameWidgetInitTestWithAnimations(GameWidgetInitTest):
  @staticmethod
  def create_game_widget():
    return GameWidget(enable_animations=True)


class InitFromGameStateWaitsOneFrame(_GameWidgetBaseTest):
  """
  This tests checks that we wait one frame before animating the cards. After
  calling GameWidget.init_from_game_state(), we need to wait one frame for
  do_layout() to be called and the card widgets' sizes to be updated. If we
  start the animation without waiting one frame, it will not play correctly.
  """

  @staticmethod
  def create_game_widget():
    return GameWidget(enable_animations=True)

  def test_init_from_game_state_with_current_trick_animation_is_played(self):
    """
    The animation here is playing a card corresponding to the non-empty current
    trick.
    """
    game_state = get_game_state_for_tests()
    played_card = Card(Suit.DIAMONDS, CardValue.QUEEN)
    with GameStateValidator(game_state):
      game_state.current_trick.two = played_card
    game_widget = GameWidget(enable_animations=True)
    self.render(game_widget)
    done_callback = Mock()
    game_widget.init_from_game_state(game_state, done_callback)
    self.advance_frames(1)
    self.assertEqual(list(game_widget.player_card_widgets.two.card_size),
                     game_widget.cards[played_card].size)
    self.wait_for_mock_callback(done_callback)

  def test_init_from_game_state_without_current_trick_animation_is_played(self):
    """The animation here is flipping the cards in the player's hand."""
    game_state = get_game_state_for_tests()
    game_widget = GameWidget(enable_animations=True)
    self.render(game_widget)
    done_callback = Mock()
    game_widget.init_from_game_state(game_state, done_callback)
    self.advance_frames(1)
    self.assertEqual(list(game_widget.player_card_widgets.two.card_size),
                     game_widget.cards[game_state.cards_in_hand.one[0]].size)
    self.wait_for_mock_callback(done_callback)


class GameWidgetInitTestWithCancelledAnimations(
  _GameWidgetWithCancelledAnimations, GameWidgetInitTestWithAnimations):
  pass


class GameWidgetGraphicTest(_GameWidgetBaseTest):
  def test_on_action_exchange_trump_card_player_two(self):
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, get_game_state_for_tests())
    trump_card_widget = game_widget.talon_widget.trump_card
    self.assertEqual(Card(Suit.CLUBS, CardValue.ACE), trump_card_widget.card)
    trump_jack_widget = game_widget.cards[Card(Suit.CLUBS, CardValue.JACK)]
    self.assertIs(game_widget.player_card_widgets.two, trump_jack_widget.parent)
    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    queen_diamonds_widget = game_widget.cards[queen_diamonds]
    self.assertEqual(queen_diamonds_widget,
                     game_widget.player_card_widgets.two.at(0, 0))
    self.assertEqual(trump_jack_widget,
                     game_widget.player_card_widgets.two.at(0, 2))
    with self.assertRaisesRegex(AssertionError,
                                "Trump Jack not in player's hand"):
      self._on_action(game_widget, ExchangeTrumpCardAction(PlayerId.ONE))
    self._on_action(game_widget, ExchangeTrumpCardAction(PlayerId.TWO))
    self.assertEqual(Card(Suit.CLUBS, CardValue.JACK),
                     game_widget.talon_widget.trump_card.card)
    self.assertIs(game_widget.player_card_widgets.two, trump_card_widget.parent)
    self.assertTrue(trump_jack_widget.visible)
    self.assertTrue(trump_card_widget.visible)
    self.assertEqual(queen_diamonds_widget,
                     game_widget.player_card_widgets.two.at(0, 0))
    self.assertEqual(trump_card_widget,
                     game_widget.player_card_widgets.two.at(0, 1))

  def test_on_action_exchange_trump_card_player_one(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      trump_jack = game_state.cards_in_hand.two.pop(2)
      ten_hearts = game_state.cards_in_hand.one.pop(2)
      game_state.cards_in_hand.two.append(ten_hearts)
      game_state.cards_in_hand.one.append(trump_jack)
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)
    trump_card_widget = game_widget.talon_widget.trump_card
    self.assertFalse(trump_card_widget.grayed_out)
    self.assertEqual(Card(Suit.CLUBS, CardValue.ACE), trump_card_widget.card)
    trump_jack_widget = game_widget.cards[Card(Suit.CLUBS, CardValue.JACK)]
    self.assertTrue(trump_jack_widget.grayed_out)
    self.assertIs(game_widget.player_card_widgets.one, trump_jack_widget.parent)
    with self.assertRaisesRegex(AssertionError,
                                "Trump Jack not in player's hand"):
      self._on_action(game_widget, ExchangeTrumpCardAction(PlayerId.TWO))
    self._on_action(game_widget, ExchangeTrumpCardAction(PlayerId.ONE))
    self.assertEqual(Card(Suit.CLUBS, CardValue.JACK),
                     game_widget.talon_widget.trump_card.card)
    self.assertIs(game_widget.player_card_widgets.one, trump_card_widget.parent)
    self.assertTrue(trump_card_widget.grayed_out)
    self.assertFalse(trump_jack_widget.grayed_out)
    self.assertTrue(trump_jack_widget.visible)
    self.assertTrue(trump_card_widget.visible)
    self.assertEqual(trump_card_widget,
                     game_widget.player_card_widgets.one.at(0, 4))

  def test_on_action_close_the_talon(self):
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, get_game_state_for_tests())
    self.assertFalse(game_widget.talon_widget.closed)
    self._on_action(game_widget, CloseTheTalonAction(PlayerId.ONE))
    self.assertTrue(game_widget.talon_widget.closed)

  def test_on_action_unsupported_action(self):
    class UnsupportedAction(PlayerAction):
      def can_execute_on(self, _):
        return True

      def execute(self, _):
        pass

    game_widget = self.create_game_widget()
    self.render(game_widget)
    with self.assertRaisesRegex(AssertionError, "Should not reach this code"):
      self._on_action(game_widget, UnsupportedAction(PlayerId.ONE))

  def test_on_trick_completed_player_one_wins(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    ace_spades_widget = game_widget.cards[ace_spades]
    action = PlayCardAction(PlayerId.ONE, ace_spades)
    action.execute(game_state)
    self._on_action(game_widget, action)
    self.assertIs(game_widget.play_area, ace_spades_widget.parent)

    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    queen_diamonds_widget = game_widget.cards[queen_diamonds]
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    action.execute(game_state)
    self._on_action(game_widget, action)
    self.assertIs(game_widget.play_area, queen_diamonds_widget.parent)

    trick = PlayerPair(ace_spades, queen_diamonds)
    self._on_trick_completed(game_widget, trick, PlayerId.ONE,
                             game_state.cards_in_hand, True)
    self.assertIs(game_widget.tricks_widgets.one, ace_spades_widget.parent)
    self.assertIs(game_widget.tricks_widgets.one, queen_diamonds_widget.parent)

  def test_on_trick_completed_player_two_wins(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    queen_diamonds_widget = game_widget.cards[queen_diamonds]
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    action.execute(game_state)
    self._on_action(game_widget, action)
    self.assertIs(game_widget.play_area, queen_diamonds_widget.parent)

    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    ace_spades_widget = game_widget.cards[ace_spades]
    action = PlayCardAction(PlayerId.ONE, ace_spades)
    action.execute(game_state)
    self._on_action(game_widget, action)
    self.assertIs(game_widget.play_area, ace_spades_widget.parent)

    trick = PlayerPair(ace_spades, queen_diamonds)
    self._on_trick_completed(game_widget, trick, PlayerId.TWO,
                             game_state.cards_in_hand, True)
    self.assertIs(game_widget.tricks_widgets.two, ace_spades_widget.parent)
    self.assertIs(game_widget.tricks_widgets.two, queen_diamonds_widget.parent)

  def test_on_trick_completed_after_marriage_announced(self):
    game_widget = self.create_game_widget()
    game_state = get_game_state_for_tests()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    king_hearts = Card(Suit.HEARTS, CardValue.KING)
    king_hearts_widget = game_widget.cards[king_hearts]
    queen_hearts_widget = game_widget.cards[king_hearts.marriage_pair]
    action = AnnounceMarriageAction(PlayerId.ONE, king_hearts)
    action.execute(game_state)
    self._on_action(game_widget, action)
    self.assertIs(game_widget.play_area, king_hearts_widget.parent)
    self.assertIs(game_widget.play_area, queen_hearts_widget.parent)

    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    queen_diamonds_widget = game_widget.cards[queen_diamonds]
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    action.execute(game_state)
    self._on_action(game_widget, action)
    self.assertIs(game_widget.play_area, queen_diamonds_widget.parent)
    self.assertIs(game_widget.play_area, queen_hearts_widget.parent)

    trick = PlayerPair(king_hearts, queen_diamonds)
    self._on_trick_completed(game_widget, trick, PlayerId.TWO,
                             game_state.cards_in_hand, True)
    self.assertIs(game_widget.tricks_widgets.two, king_hearts_widget.parent)
    self.assertIs(game_widget.player_card_widgets.one,
                  queen_hearts_widget.parent)
    self.assertIs(game_widget.tricks_widgets.two, queen_diamonds_widget.parent)

  def test_on_trick_completed_talon_is_closed(self):
    game_state = get_game_state_with_multiple_cards_in_the_talon_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
      game_state.close_talon()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    first_talon_card = game_widget.cards[game_state.talon[0]]
    second_talon_card = game_widget.cards[game_state.talon[1]]

    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    action.execute(game_state)
    self._on_action(game_widget, action)
    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    action = PlayCardAction(PlayerId.ONE, queen_hearts)
    action.execute(game_state)
    self._on_action(game_widget, action)

    self.assertIs(first_talon_card, game_widget.talon_widget.top_card())
    self.assertIs(game_widget.talon_widget, second_talon_card.parent)

    trick = PlayerPair(queen_hearts, queen_diamonds)
    self._on_trick_completed(game_widget, trick, PlayerId.TWO,
                             game_state.cards_in_hand, False)
    self.assertIs(first_talon_card, game_widget.talon_widget.top_card())
    self.assertFalse(first_talon_card.visible)
    self.assertFalse(first_talon_card.grayed_out)
    self.assertFalse(first_talon_card.shadow)
    self.assert_do_translation(False, first_talon_card)
    self.assertIs(game_widget.talon_widget, second_talon_card.parent)
    self.assertFalse(second_talon_card.visible)
    self.assertFalse(second_talon_card.grayed_out)
    self.assertFalse(second_talon_card.shadow)
    self.assert_do_translation(False, second_talon_card)

  def test_on_trick_completed_talon_is_empty(self):
    game_state = get_game_state_with_empty_talon_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    ace_clubs = Card(Suit.CLUBS, CardValue.ACE)
    ace_clubs_widget = game_widget.cards[ace_clubs]
    action = PlayCardAction(PlayerId.ONE, ace_clubs)
    action.execute(game_state)
    self._on_action(game_widget, action)
    self.assertIs(game_widget.play_area, ace_clubs_widget.parent)

    jack_clubs = Card(Suit.CLUBS, CardValue.JACK)
    jack_clubs_widget = game_widget.cards[jack_clubs]
    action = PlayCardAction(PlayerId.TWO, jack_clubs)
    action.execute(game_state)
    self._on_action(game_widget, action)
    self.assertIs(game_widget.play_area, jack_clubs_widget.parent)

    trick = PlayerPair(ace_clubs, jack_clubs)
    self._on_trick_completed(game_widget, trick, PlayerId.ONE,
                             game_state.cards_in_hand, False)
    self.assertIs(game_widget.tricks_widgets.one, ace_clubs_widget.parent)
    self.assertIs(game_widget.tricks_widgets.one, jack_clubs_widget.parent)

  def test_on_new_cards_drawn_last_talon_card_player_one_wins(self):
    game_widget = self.create_game_widget()
    game_state = get_game_state_for_tests()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    ace_spades_widget = game_widget.cards[ace_spades]
    action = PlayCardAction(PlayerId.ONE, ace_spades)
    action.execute(game_state)
    self._on_action(game_widget, action)
    self.assertIs(game_widget.play_area, ace_spades_widget.parent)

    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    queen_diamonds_widget = game_widget.cards[queen_diamonds]
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    action.execute(game_state)
    self._on_action(game_widget, action)
    self.assertIs(game_widget.play_area, queen_diamonds_widget.parent)

    trick = PlayerPair(ace_spades, queen_diamonds)
    last_talon_card = game_widget.talon_widget.top_card()
    self.assertIsNotNone(last_talon_card)
    trump_card = game_widget.talon_widget.trump_card
    self.assertIsNotNone(trump_card)
    self._on_trick_completed(game_widget, trick, PlayerId.TWO,
                             game_state.cards_in_hand, True)
    self.assertIs(game_widget.tricks_widgets.two, ace_spades_widget.parent)
    self.assertIs(game_widget.tricks_widgets.two, queen_diamonds_widget.parent)
    self.assertIsNone(game_widget.talon_widget.top_card())
    self.assertIsNone(game_widget.talon_widget.trump_card)
    self.assertIs(game_widget.player_card_widgets.one, last_talon_card.parent)
    self.assertTrue(last_talon_card.visible)
    self.assertTrue(last_talon_card.grayed_out)
    self.assertTrue(last_talon_card.shadow)
    self.assert_do_translation(False, last_talon_card)
    self.assertIs(game_widget.player_card_widgets.two, trump_card.parent)
    self.assertTrue(trump_card.visible)
    self.assertFalse(trump_card.grayed_out)
    self.assertTrue(trump_card.shadow)
    self.assert_do_translation(False, trump_card)

  def test_on_new_cards_drawn_last_talon_card_player_two_wins(self):
    game_widget = self.create_game_widget()
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    queen_diamonds_widget = game_widget.cards[queen_diamonds]
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    action.execute(game_state)
    self._on_action(game_widget, action)
    self.assertIs(game_widget.play_area, queen_diamonds_widget.parent)

    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    ace_spades_widget = game_widget.cards[ace_spades]
    action = PlayCardAction(PlayerId.ONE, ace_spades)
    action.execute(game_state)
    self._on_action(game_widget, action)
    self.assertIs(game_widget.play_area, ace_spades_widget.parent)

    last_talon_card = game_widget.talon_widget.top_card()
    self.assertIsNotNone(last_talon_card)
    trump_card = game_widget.talon_widget.trump_card
    self.assertIsNotNone(trump_card)

    trick = PlayerPair(ace_spades, queen_diamonds)
    self._on_trick_completed(game_widget, trick, PlayerId.ONE,
                             game_state.cards_in_hand, True)

    self.assertIs(game_widget.tricks_widgets.one, ace_spades_widget.parent)
    self.assertIs(game_widget.tricks_widgets.one, queen_diamonds_widget.parent)
    self.assertIsNone(game_widget.talon_widget.top_card())
    self.assertIsNone(game_widget.talon_widget.trump_card)
    self.assertIs(game_widget.player_card_widgets.two, last_talon_card.parent)
    self.assertFalse(last_talon_card.visible)
    self.assertFalse(last_talon_card.grayed_out)
    self.assertTrue(last_talon_card.shadow)
    self.assert_do_translation(False, last_talon_card)
    self.assertIs(game_widget.player_card_widgets.one, trump_card.parent)
    self.assertTrue(trump_card.visible)
    self.assertTrue(trump_card.grayed_out)
    self.assertTrue(trump_card.shadow)
    self.assert_do_translation(False, trump_card)

  def test_on_new_cards_drawn_talon_has_more_cards_player_one_wins(self):
    game_state = get_game_state_with_multiple_cards_in_the_talon_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    first_talon_card = game_widget.cards[game_state.talon[0]]
    second_talon_card = game_widget.cards[game_state.talon[1]]

    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    action = PlayCardAction(PlayerId.ONE, queen_hearts)
    action.execute(game_state)
    self._on_action(game_widget, action)
    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    action.execute(game_state)
    self._on_action(game_widget, action)

    self.assertIs(first_talon_card, game_widget.talon_widget.top_card())
    self.assertIs(game_widget.talon_widget, second_talon_card.parent)

    trick = PlayerPair(queen_hearts, queen_diamonds)
    self._on_trick_completed(game_widget, trick, PlayerId.ONE,
                             game_state.cards_in_hand, True)

    self.assertIsNot(first_talon_card, game_widget.talon_widget.top_card())
    self.assertIs(game_widget.player_card_widgets.one, first_talon_card.parent)
    self.assertTrue(first_talon_card.visible)
    self.assertTrue(first_talon_card.grayed_out)
    self.assertTrue(first_talon_card.shadow)
    self.assert_do_translation(False, first_talon_card)
    self.assertIs(game_widget.player_card_widgets.two, second_talon_card.parent)
    self.assertFalse(second_talon_card.visible)
    self.assertFalse(second_talon_card.grayed_out)
    self.assertTrue(second_talon_card.shadow)
    self.assert_do_translation(False, second_talon_card)

  def test_on_new_cards_drawn_talon_has_more_cards_player_two_wins(self):
    game_state = get_game_state_with_multiple_cards_in_the_talon_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    first_talon_card = game_widget.cards[game_state.talon[0]]
    second_talon_card = game_widget.cards[game_state.talon[1]]

    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    action.execute(game_state)
    self._on_action(game_widget, action)
    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    action = PlayCardAction(PlayerId.ONE, queen_hearts)
    action.execute(game_state)
    self._on_action(game_widget, action)

    self.assertIs(first_talon_card, game_widget.talon_widget.top_card())
    self.assertIs(game_widget.talon_widget, second_talon_card.parent)

    trick = PlayerPair(queen_hearts, queen_diamonds)
    self._on_trick_completed(game_widget, trick, PlayerId.TWO,
                             game_state.cards_in_hand, True)

    self.assertIsNot(first_talon_card, game_widget.talon_widget.top_card())
    self.assertIs(game_widget.player_card_widgets.two, first_talon_card.parent)
    self.assertFalse(first_talon_card.visible)
    self.assertFalse(first_talon_card.grayed_out)
    self.assertTrue(first_talon_card.shadow)
    self.assert_do_translation(False, first_talon_card)
    self.assertIs(game_widget.player_card_widgets.one, second_talon_card.parent)
    self.assertTrue(second_talon_card.visible)
    self.assertTrue(second_talon_card.grayed_out)
    self.assertTrue(second_talon_card.shadow)
    self.assert_do_translation(False, second_talon_card)

  # pylint: disable=too-many-statements
  def test_do_layout(self):
    game_widget = self.create_game_widget()
    self.render(game_widget)

    # The initial window size is 320 x 240.
    self.assert_pixels_almost_equal([dp(320), dp(240)], game_widget.size)
    self.assert_pixels_almost_equal([dp(112), dp(60)],
                                    game_widget.tricks_widgets.one.size)
    self.assert_pixels_almost_equal([dp(208), dp(24)],
                                    game_widget.tricks_widgets.one.pos)
    self.assert_pixels_almost_equal([dp(112), dp(60)],
                                    game_widget.tricks_widgets.two.size)
    self.assert_pixels_almost_equal([dp(208), dp(180)],
                                    game_widget.tricks_widgets.two.pos)
    self.assert_pixels_almost_equal([dp(112), dp(72)],
                                    game_widget.talon_widget.size)
    self.assert_pixels_almost_equal([dp(208), dp(108)],
                                    game_widget.talon_widget.pos)
    self.assert_pixels_almost_equal([dp(208), dp(84)],
                                    game_widget.player_card_widgets.one.size)
    self.assert_pixels_almost_equal([dp(0), dp(0)],
                                    game_widget.player_card_widgets.one.pos)
    self.assert_pixels_almost_equal([dp(208), dp(84)],
                                    game_widget.player_card_widgets.two.size)
    self.assert_pixels_almost_equal([dp(0), dp(216)],
                                    game_widget.player_card_widgets.two.pos)
    self.assert_pixels_almost_equal([dp(166), dp(84)],
                                    game_widget.play_area.size)
    self.assert_pixels_almost_equal([dp(21), dp(108)],
                                    game_widget.play_area.pos)

    # Stretch window horizontally to 640 x 240.
    EventLoop.window.size = 640, 240
    self.advance_frames(1)
    self.assert_pixels_almost_equal([dp(640), dp(240)], game_widget.size)
    self.assert_pixels_almost_equal([dp(224), dp(60)],
                                    game_widget.tricks_widgets.one.size)
    self.assert_pixels_almost_equal([dp(416), dp(24)],
                                    game_widget.tricks_widgets.one.pos)
    self.assert_pixels_almost_equal([dp(224), dp(60)],
                                    game_widget.tricks_widgets.two.size)
    self.assert_pixels_almost_equal([dp(416), dp(180)],
                                    game_widget.tricks_widgets.two.pos)
    self.assert_pixels_almost_equal([dp(224), dp(72)],
                                    game_widget.talon_widget.size)
    self.assert_pixels_almost_equal([dp(416), dp(108)],
                                    game_widget.talon_widget.pos)
    self.assert_pixels_almost_equal([dp(416), dp(84)],
                                    game_widget.player_card_widgets.one.size)
    self.assert_pixels_almost_equal([dp(0), dp(0)],
                                    game_widget.player_card_widgets.one.pos)
    self.assert_pixels_almost_equal([dp(416), dp(84)],
                                    game_widget.player_card_widgets.two.size)
    self.assert_pixels_almost_equal([dp(0), dp(216)],
                                    game_widget.player_card_widgets.two.pos)
    self.assert_pixels_almost_equal([dp(333), dp(84)],
                                    game_widget.play_area.size)
    self.assert_pixels_almost_equal([dp(41), dp(108)],
                                    game_widget.play_area.pos)

    # Stretch window vertically to 320 x 480.
    EventLoop.window.size = 320, 480
    self.advance_frames(1)
    self.assert_pixels_almost_equal([dp(320), dp(480)], game_widget.size)
    self.assert_pixels_almost_equal([dp(112), dp(120)],
                                    game_widget.tricks_widgets.one.size)
    self.assert_pixels_almost_equal([dp(208), dp(48)],
                                    game_widget.tricks_widgets.one.pos)
    self.assert_pixels_almost_equal([dp(112), dp(120)],
                                    game_widget.tricks_widgets.two.size)
    self.assert_pixels_almost_equal([dp(208), dp(360)],
                                    game_widget.tricks_widgets.two.pos)
    self.assert_pixels_almost_equal([dp(112), dp(144)],
                                    game_widget.talon_widget.size)
    self.assert_pixels_almost_equal([dp(208), dp(216)],
                                    game_widget.talon_widget.pos)
    self.assert_pixels_almost_equal([dp(208), dp(168)],
                                    game_widget.player_card_widgets.one.size)
    self.assert_pixels_almost_equal([dp(0), dp(0)],
                                    game_widget.player_card_widgets.one.pos)
    self.assert_pixels_almost_equal([dp(208), dp(168)],
                                    game_widget.player_card_widgets.two.size)
    self.assert_pixels_almost_equal([dp(0), dp(432)],
                                    game_widget.player_card_widgets.two.pos)
    self.assert_pixels_almost_equal([dp(166), dp(168)],
                                    game_widget.play_area.size)
    self.assert_pixels_almost_equal([dp(21), dp(216)],
                                    game_widget.play_area.pos)

    # Stretch window vertically and horizontally to 640 x 480.
    EventLoop.window.size = 640, 480
    self.advance_frames(1)
    self.assert_pixels_almost_equal([dp(640), dp(480)], game_widget.size)
    self.assert_pixels_almost_equal([dp(224), dp(120)],
                                    game_widget.tricks_widgets.one.size)
    self.assert_pixels_almost_equal([dp(416), dp(48)],
                                    game_widget.tricks_widgets.one.pos)
    self.assert_pixels_almost_equal([dp(224), dp(120)],
                                    game_widget.tricks_widgets.two.size)
    self.assert_pixels_almost_equal([dp(416), dp(360)],
                                    game_widget.tricks_widgets.two.pos)
    self.assert_pixels_almost_equal([dp(224), dp(144)],
                                    game_widget.talon_widget.size)
    self.assert_pixels_almost_equal([dp(416), dp(216)],
                                    game_widget.talon_widget.pos)
    self.assert_pixels_almost_equal([dp(416), dp(168)],
                                    game_widget.player_card_widgets.one.size)
    self.assert_pixels_almost_equal([dp(0), dp(0)],
                                    game_widget.player_card_widgets.one.pos)
    self.assert_pixels_almost_equal([dp(416), dp(168)],
                                    game_widget.player_card_widgets.two.size)
    self.assert_pixels_almost_equal([dp(0), dp(432)],
                                    game_widget.player_card_widgets.two.pos)
    self.assert_pixels_almost_equal([dp(333), dp(168)],
                                    game_widget.play_area.size)
    self.assert_pixels_almost_equal([dp(41), dp(216)],
                                    game_widget.play_area.pos)

  def test_on_action_play_card(self):
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, get_game_state_for_tests())

    with self.assertRaisesRegex(AssertionError, "Player ONE does not hold J♥"):
      self._on_action(game_widget,
                      PlayCardAction(PlayerId.ONE,
                                     Card(Suit.HEARTS, CardValue.JACK)))

    ten_spades = Card(Suit.SPADES, CardValue.TEN)
    ten_spades_widget = game_widget.cards[ten_spades]
    self.assertIs(game_widget.player_card_widgets.one, ten_spades_widget.parent)
    self._on_action(game_widget, PlayCardAction(PlayerId.ONE, ten_spades))
    self.assertIs(game_widget.play_area, ten_spades_widget.parent)
    self.assertTrue(ten_spades_widget.visible)
    self.assertFalse(ten_spades_widget.grayed_out)
    self.assert_do_translation(False, ten_spades_widget)
    self.assert_pixels_almost_equal([dp(38), dp(59)], ten_spades_widget.size)
    self.assertEqual(game_widget.play_area.center,
                     list(ten_spades_widget.center))

    king_clubs = Card(Suit.CLUBS, CardValue.KING)
    king_clubs_widget = game_widget.cards[king_clubs]
    self.assertIs(game_widget.player_card_widgets.two, king_clubs_widget.parent)
    self.assertFalse(king_clubs_widget.visible)
    self.assertFalse(king_clubs_widget.grayed_out)
    self.assert_do_translation(False, king_clubs_widget)
    self._on_action(game_widget, PlayCardAction(PlayerId.TWO, king_clubs))
    self.assertIs(game_widget.play_area, king_clubs_widget.parent)
    self.assertTrue(king_clubs_widget.visible)
    self.assertFalse(king_clubs_widget.grayed_out)
    self.assert_do_translation(False, king_clubs_widget)
    self.assert_pixels_almost_equal([dp(38), dp(59)], king_clubs_widget.size)
    self.assert_pixels_almost_equal([dp(111), dp(161)],
                                    king_clubs_widget.center)

  def test_on_action_play_card_by_dragging(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    drag_pos = game_widget.play_area.x + dp(10), \
               game_widget.play_area.y + dp(10)
    self.assertNotEqual(game_widget.play_area.center, drag_pos)

    ten_spades = Card(Suit.SPADES, CardValue.TEN)
    ten_spades_widget = game_widget.cards[ten_spades]
    self.assertIs(game_widget.player_card_widgets.one, ten_spades_widget.parent)
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    _drag_card_to_pos(ten_spades_widget, drag_pos)
    self.advance_frames(1)
    callback.assert_called_once()
    self._on_action(game_widget, PlayCardAction(PlayerId.ONE, ten_spades))
    self.assertIs(game_widget.play_area, ten_spades_widget.parent)
    self.assertTrue(ten_spades_widget.visible)
    self.assertFalse(ten_spades_widget.grayed_out)
    self.assert_do_translation(False, ten_spades_widget)
    self.assert_pixels_almost_equal([dp(38), dp(59)], ten_spades_widget.size)
    self.assertEqual(drag_pos, ten_spades_widget.center)

  def test_on_action_play_card_reply_is_relative_to_first_card(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    drag_pos = game_widget.play_area.x + dp(10), \
               game_widget.play_area.y + dp(10)
    self.assertNotEqual(game_widget.play_area.center, drag_pos)

    ten_spades = Card(Suit.SPADES, CardValue.TEN)
    ten_spades_widget = game_widget.cards[ten_spades]
    self.assertIs(game_widget.player_card_widgets.one, ten_spades_widget.parent)
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    _drag_card_to_pos(ten_spades_widget, drag_pos)
    self.advance_frames(1)
    callback.assert_called_once()
    self._on_action(game_widget, PlayCardAction(PlayerId.ONE, ten_spades))
    self.assertIs(game_widget.play_area, ten_spades_widget.parent)
    self.assertTrue(ten_spades_widget.visible)
    self.assertFalse(ten_spades_widget.grayed_out)
    self.assert_do_translation(False, ten_spades_widget)
    self.assert_pixels_almost_equal([dp(38), dp(59)], ten_spades_widget.size)
    self.assertEqual(drag_pos, ten_spades_widget.center)

    jack_spades = Card(Suit.SPADES, CardValue.JACK)
    jack_spades_widget = game_widget.cards[jack_spades]
    self.assertIs(game_widget.player_card_widgets.two,
                  jack_spades_widget.parent)
    self._on_action(game_widget, PlayCardAction(PlayerId.TWO, jack_spades))
    self.assertIs(game_widget.play_area, jack_spades_widget.parent)
    self.assertTrue(jack_spades_widget.visible)
    self.assertFalse(jack_spades_widget.grayed_out)
    self.assert_do_translation(False, jack_spades_widget)
    self.assert_pixels_almost_equal([dp(38), dp(59)], jack_spades_widget.size)
    self.assert_pixels_almost_equal([dp(38), dp(129)],
                                    jack_spades_widget.center)

  def test_on_action_announce_marriage_reply_is_relative_to_first_card(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    drag_pos = game_widget.play_area.x + dp(10), \
               game_widget.play_area.y + dp(10)
    self.assertNotEqual(game_widget.play_area.center, drag_pos)

    king_hearts = Card(Suit.HEARTS, CardValue.KING)
    king_hearts_widget = game_widget.cards[king_hearts]
    self.assertIs(game_widget.player_card_widgets.one,
                  king_hearts_widget.parent)
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    _drag_card_to_pos(king_hearts_widget, drag_pos)
    self.advance_frames(1)
    callback.assert_called_once()
    self._on_action(game_widget,
                    AnnounceMarriageAction(PlayerId.ONE, king_hearts))
    self.assertIs(game_widget.play_area, king_hearts_widget.parent)
    self.assertTrue(king_hearts_widget.visible)
    self.assertFalse(king_hearts_widget.grayed_out)
    self.assert_do_translation(False, king_hearts_widget)
    self.assert_pixels_almost_equal([dp(38), dp(59)], king_hearts_widget.size)
    self.assertEqual(drag_pos, king_hearts_widget.center)

    jack_spades = Card(Suit.SPADES, CardValue.JACK)
    jack_spades_widget = game_widget.cards[jack_spades]
    self.assertIs(game_widget.player_card_widgets.two,
                  jack_spades_widget.parent)
    self._on_action(game_widget, PlayCardAction(PlayerId.TWO, jack_spades))
    self.assertIs(game_widget.play_area, jack_spades_widget.parent)
    self.assertTrue(jack_spades_widget.visible)
    self.assertFalse(jack_spades_widget.grayed_out)
    self.assert_do_translation(False, jack_spades_widget)
    self.assert_pixels_almost_equal([dp(38), dp(59)], jack_spades_widget.size)
    self.assert_pixels_almost_equal([dp(38), dp(129)],
                                    jack_spades_widget.center)

  def test_on_action_announce_marriage(self):
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, get_game_state_for_tests())

    with self.assertRaisesRegex(AssertionError, "Player ONE does not hold K♠"):
      self._on_action(game_widget,
                      PlayCardAction(PlayerId.ONE,
                                     Card(Suit.SPADES, CardValue.KING)))

    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    queen_hearts_widget = game_widget.cards[queen_hearts]
    king_hearts = queen_hearts.marriage_pair
    king_hearts_widget = game_widget.cards[king_hearts]
    self.assertIs(game_widget.player_card_widgets.one,
                  queen_hearts_widget.parent)
    self.assertIs(game_widget.player_card_widgets.one,
                  king_hearts_widget.parent)
    self._on_action(game_widget,
                    AnnounceMarriageAction(PlayerId.ONE, queen_hearts))
    self.assertIs(game_widget.play_area, queen_hearts_widget.parent)
    self.assertIs(game_widget.play_area, king_hearts_widget.parent)
    self.assertTrue(queen_hearts_widget.visible)
    self.assertFalse(queen_hearts_widget.grayed_out)
    self.assert_do_translation(False, queen_hearts_widget)
    self.assertTrue(king_hearts_widget.visible)
    self.assertFalse(king_hearts_widget.grayed_out)
    self.assert_do_translation(False, king_hearts_widget)
    self.assert_pixels_almost_equal([dp(38), dp(59)], queen_hearts_widget.size)
    self.assert_pixels_almost_equal([dp(38), dp(59)], king_hearts_widget.size)
    self.assertEqual(game_widget.play_area.center,
                     list(queen_hearts_widget.center))
    self.assert_pixels_almost_equal([dp(96), dp(138)],
                                    king_hearts_widget.center)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

    game_widget.reset()
    self.render(game_widget)
    self._init_from_game_state(game_widget, get_game_state_for_tests())

    king_clubs = Card(Suit.CLUBS, CardValue.KING)
    king_clubs_widget = game_widget.cards[king_clubs]
    queen_clubs = king_clubs.marriage_pair
    queen_clubs_widget = game_widget.cards[queen_clubs]
    self.assertIs(game_widget.player_card_widgets.two, king_clubs_widget.parent)
    self.assertIs(game_widget.player_card_widgets.two,
                  queen_clubs_widget.parent)
    self.assertFalse(king_clubs_widget.visible)
    self.assertFalse(king_clubs_widget.grayed_out)
    self.assert_do_translation(False, king_clubs_widget)
    self.assertFalse(queen_clubs_widget.visible)
    self.assertFalse(queen_clubs_widget.grayed_out)
    self.assert_do_translation(False, queen_clubs_widget)
    self._on_action(game_widget,
                    AnnounceMarriageAction(PlayerId.TWO, king_clubs))
    self.assertIs(game_widget.play_area, king_clubs_widget.parent)
    self.assertIs(game_widget.play_area, queen_clubs_widget.parent)
    self.assertTrue(king_clubs_widget.visible)
    self.assertFalse(king_clubs_widget.grayed_out)
    self.assert_do_translation(False, king_clubs_widget)
    self.assertTrue(queen_clubs_widget.visible)
    self.assertFalse(queen_clubs_widget.grayed_out)
    self.assert_do_translation(False, queen_clubs_widget)
    self.assert_pixels_almost_equal([dp(38), dp(59)], king_clubs_widget.size)
    self.assert_pixels_almost_equal([dp(38), dp(59)], queen_clubs_widget.size)
    self.assert_pixels_almost_equal(game_widget.play_area.center,
                                    list(king_clubs_widget.center))
    self.assert_pixels_almost_equal([dp(111), dp(161)],
                                    queen_clubs_widget.center)
    self.assert_is_drawn_on_top(king_clubs_widget, queen_clubs_widget)

  def test_on_action_announce_marriage_by_dragging(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    with self.assertRaisesRegex(AssertionError, "Player ONE does not hold K♠"):
      self._on_action(game_widget,
                      PlayCardAction(PlayerId.ONE,
                                     Card(Suit.SPADES, CardValue.KING)))

    drag_pos = game_widget.play_area.center
    self.assert_pixels_almost_equal([dp(104), dp(150)], drag_pos)

    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    queen_hearts_widget = game_widget.cards[queen_hearts]
    king_hearts = queen_hearts.marriage_pair
    king_hearts_widget = game_widget.cards[king_hearts]
    self.assertIs(game_widget.player_card_widgets.one,
                  queen_hearts_widget.parent)
    self.assertIs(game_widget.player_card_widgets.one,
                  king_hearts_widget.parent)

    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    _drag_card_to_pos(queen_hearts_widget, drag_pos)
    callback.assert_called_once()

    self.assert_pixels_almost_equal((dp(104), dp(150)),
                                    queen_hearts_widget.center)
    self.assert_pixels_almost_equal([dp(96), dp(138)],
                                    king_hearts_widget.center)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

    self._on_action(game_widget,
                    AnnounceMarriageAction(PlayerId.ONE, queen_hearts))

    self.assertIs(game_widget.play_area, queen_hearts_widget.parent)
    self.assertIs(game_widget.play_area, king_hearts_widget.parent)
    self.assertTrue(queen_hearts_widget.visible)
    self.assertFalse(queen_hearts_widget.grayed_out)
    self.assert_do_translation(False, queen_hearts_widget)
    self.assertTrue(king_hearts_widget.visible)
    self.assertFalse(king_hearts_widget.grayed_out)
    self.assert_do_translation(False, king_hearts_widget)
    self.assert_pixels_almost_equal([dp(38), dp(59)], queen_hearts_widget.size)
    self.assert_pixels_almost_equal([dp(38), dp(59)], king_hearts_widget.size)
    self.assert_pixels_almost_equal((dp(104), dp(150)),
                                    queen_hearts_widget.center)
    self.assert_pixels_almost_equal([dp(96), dp(138)],
                                    king_hearts_widget.center)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

  def test_cards_in_play_area_are_updated_on_window_resize(self):
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, get_game_state_for_tests())

    ten_spades = Card(Suit.SPADES, CardValue.TEN)
    ten_spades_widget = game_widget.cards[ten_spades]
    self.assertIs(game_widget.player_card_widgets.one, ten_spades_widget.parent)
    self._on_action(game_widget, PlayCardAction(PlayerId.ONE, ten_spades))
    self.assertIs(game_widget.play_area, ten_spades_widget.parent)
    self.assertTrue(ten_spades_widget.visible)
    self.assertFalse(ten_spades_widget.grayed_out)
    self.assert_do_translation(False, ten_spades_widget)
    self.assert_pixels_almost_equal([dp(38), dp(59)], ten_spades_widget.size)
    self.assertEqual(game_widget.play_area.center,
                     list(ten_spades_widget.center))
    EventLoop.window.size = 640, 480
    self.advance_frames(1)
    self.assert_pixels_almost_equal([dp(77), dp(118)], ten_spades_widget.size)
    self.assert_pixels_almost_equal(game_widget.play_area.center,
                                    list(ten_spades_widget.center))

  def test_cards_dragged_in_play_area_are_updated_on_window_resize(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    drag_pos = game_widget.play_area.x + dp(10), \
               game_widget.play_area.y + dp(10)
    self.assertNotEqual(game_widget.play_area.center, drag_pos)

    ten_spades = Card(Suit.SPADES, CardValue.TEN)
    ten_spades_widget = game_widget.cards[ten_spades]
    self.assertIs(game_widget.player_card_widgets.one, ten_spades_widget.parent)
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    _drag_card_to_pos(ten_spades_widget, drag_pos)
    callback.assert_called_once()
    self._on_action(game_widget, PlayCardAction(PlayerId.ONE, ten_spades))
    self.assertIs(game_widget.play_area, ten_spades_widget.parent)
    self.assertTrue(ten_spades_widget.visible)
    self.assertFalse(ten_spades_widget.grayed_out)
    self.assert_do_translation(False, ten_spades_widget)
    self.assert_pixels_almost_equal([dp(38), dp(59)], ten_spades_widget.size)
    self.assertEqual(drag_pos, ten_spades_widget.center)
    self.window.size = 640, 480
    self.advance_frames(1)
    self.assert_pixels_almost_equal([dp(77), dp(118)], ten_spades_widget.size)
    self.assert_pixels_almost_equal([dp(61), dp(236)],
                                    list(ten_spades_widget.center))

  def test_marriage_dragged_in_play_area_is_updated_on_window_resize(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    drag_pos = game_widget.play_area.x + dp(10), \
               game_widget.play_area.y + dp(10)
    self.assertTrue(game_widget.play_area.collide_point(*drag_pos))
    self.assert_pixels_almost_equal([dp(30), dp(118)], list(drag_pos))

    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    queen_hearts_widget = game_widget.cards[queen_hearts]
    king_hearts = queen_hearts.marriage_pair
    king_hearts_widget = game_widget.cards[king_hearts]
    self.assertIs(game_widget.player_card_widgets.one,
                  queen_hearts_widget.parent)
    self.assertIs(game_widget.player_card_widgets.one,
                  king_hearts_widget.parent)

    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    _drag_card_to_pos(queen_hearts_widget, drag_pos)
    callback.assert_called_once()

    self.assert_pixels_almost_equal([dp(30), dp(118)],
                                    queen_hearts_widget.center)
    self.assert_pixels_almost_equal([dp(23), dp(106)],
                                    king_hearts_widget.center)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

    self._on_action(game_widget,
                    AnnounceMarriageAction(PlayerId.ONE, queen_hearts))

    self.assertIs(game_widget.play_area, queen_hearts_widget.parent)
    self.assertIs(game_widget.play_area, king_hearts_widget.parent)
    self.assertTrue(queen_hearts_widget.visible)
    self.assertFalse(queen_hearts_widget.grayed_out)
    self.assert_do_translation(False, queen_hearts_widget)
    self.assertTrue(king_hearts_widget.visible)
    self.assertFalse(king_hearts_widget.grayed_out)
    self.assert_do_translation(False, king_hearts_widget)
    self.assert_pixels_almost_equal([dp(38), dp(59)], queen_hearts_widget.size)
    self.assert_pixels_almost_equal([dp(38), dp(59)], king_hearts_widget.size)
    self.assert_pixels_almost_equal([dp(30), dp(118)],
                                    queen_hearts_widget.center)
    self.assert_pixels_almost_equal([dp(23), dp(106)],
                                    king_hearts_widget.center)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

    # Resize the window.
    self.window.size = 640, 480
    self.advance_frames(1)
    self.assert_pixels_almost_equal([dp(77), dp(118)], queen_hearts_widget.size)
    self.assert_pixels_almost_equal([dp(77), dp(118)], king_hearts_widget.size)
    self.assert_pixels_almost_equal([dp(61), dp(236)],
                                    queen_hearts_widget.center)
    self.assert_pixels_almost_equal([dp(46), dp(212)],
                                    king_hearts_widget.center)


class GameWidgetGraphicTestWithAnimations(GameWidgetGraphicTest):
  @staticmethod
  def create_game_widget():
    return GameWidget(enable_animations=True)


class GameWidgetGraphicTestWithCancelledAnimations(
  _GameWidgetWithCancelledAnimations, GameWidgetGraphicTestWithAnimations):
  pass


class GameWidgetPlayerGraphicTest(_GameWidgetBaseTest):
  def test_exchange_trump_card_with_double_click(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      trump_jack = game_state.cards_in_hand.two.pop(2)
      ten_hearts = game_state.cards_in_hand.one.pop(2)
      game_state.cards_in_hand.two.append(ten_hearts)
      game_state.cards_in_hand.one.append(trump_jack)

    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    trump_card_widget = game_widget.talon_widget.trump_card

    # A double-click on the trump card should have no effect.
    touch = UnitTestTouch(
      trump_card_widget.center_x - trump_card_widget.width / 4,
      trump_card_widget.center_y)
    touch.is_double_tap = True
    touch.touch_down()
    touch.touch_up()
    self.assertIs(trump_card_widget, game_widget.talon_widget.trump_card)

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()

    # A double-click on the trump card should call the callback with an
    # ExchangeTrumpCardAction.
    touch.touch_down()
    touch.touch_up()
    callback.assert_called_once()
    self.assertEqual(1, len(callback.call_args.args))
    self.assertEqual({}, callback.call_args.kwargs)
    action = callback.call_args.args[0]
    self.assertIsInstance(action, ExchangeTrumpCardAction)
    self.assertEqual(PlayerId.ONE, action.player_id)

    # A double-click on the trump card should have no effect.
    callback.reset_mock()
    touch.touch_down()
    touch.touch_up()
    callback.assert_not_called()

  def test_exchange_trump_card_by_dragging(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      trump_jack = game_state.cards_in_hand.two.pop(2)
      ten_hearts = game_state.cards_in_hand.one.pop(2)
      game_state.cards_in_hand.two.append(ten_hearts)
      game_state.cards_in_hand.one.append(trump_jack)

    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    trump_card_widget = game_widget.talon_widget.trump_card
    trump_jack_widget = game_widget.cards[trump_jack]
    self.assertIs(trump_card_widget, game_widget.talon_widget.trump_card)
    self.assertIs(game_widget.player_card_widgets.one, trump_jack_widget.parent)
    self.assertTrue(trump_jack_widget.grayed_out)
    self.assert_do_translation(False, trump_jack_widget)
    self.assertFalse(trump_card_widget.grayed_out)
    self.assert_do_translation(False, trump_card_widget)

    # Dragging the trump jack onto the trump card should have no effect.
    _drag_card_to_pos(trump_jack_widget, trump_card_widget.center)
    self.assertIs(trump_card_widget, game_widget.talon_widget.trump_card)
    self.assertIs(game_widget.player_card_widgets.one, trump_jack_widget.parent)
    self.assertTrue(trump_jack_widget.grayed_out)
    self.assert_do_translation(False, trump_jack_widget)
    self.assertFalse(trump_card_widget.grayed_out)
    self.assert_do_translation(False, trump_card_widget)

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()
    self.assertFalse(trump_jack_widget.grayed_out)
    self.assert_do_translation(True, trump_jack_widget)
    self.assertFalse(trump_card_widget.grayed_out)
    self.assert_do_translation(False, trump_card_widget)

    # Dragging the trump jack outside the play area and outside the trump card,
    # should have no effect.
    pos = trump_jack_widget.pos
    _drag_card_to_pos(trump_jack_widget, game_widget.tricks_widgets.two.center)
    self.advance_frames(1)
    callback.assert_not_called()
    self.assertEqual(pos, trump_jack_widget.pos)

    # Dragging the trump jack onto the trump card should call the callback with
    # an ExchangeTrumpCardAction.
    _drag_card_to_pos(trump_jack_widget, trump_card_widget.center)
    callback.assert_called_once()
    self.assertEqual(1, len(callback.call_args.args))
    self.assertEqual({}, callback.call_args.kwargs)
    action = callback.call_args.args[0]
    self.assertIsInstance(action, ExchangeTrumpCardAction)
    self.assertEqual(PlayerId.ONE, action.player_id)
    self.assertTrue(trump_jack_widget.grayed_out)
    self.assert_do_translation(False, trump_jack_widget)
    self.assertFalse(trump_card_widget.grayed_out)
    self.assert_do_translation(False, trump_card_widget)

    # Dragging again the trump jack onto the trump card should have no effect.
    callback.reset_mock()
    _drag_card_to_pos(trump_jack_widget, trump_card_widget.center)
    callback.assert_not_called()
    self.assertTrue(trump_jack_widget.grayed_out)
    self.assert_do_translation(False, trump_jack_widget)
    self.assertFalse(trump_card_widget.grayed_out)
    self.assert_do_translation(False, trump_card_widget)

  def test_exchange_trump_card_by_dragging_not_on_lead(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      trump_jack = game_state.cards_in_hand.two.pop(2)
      ten_hearts = game_state.cards_in_hand.one.pop(2)
      game_state.cards_in_hand.two.append(ten_hearts)
      game_state.cards_in_hand.one.append(trump_jack)
      game_state.next_player = PlayerId.TWO

    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)
    action = PlayCardAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.QUEEN))
    action.execute(game_state)

    trump_card_widget = game_widget.talon_widget.trump_card
    trump_jack_widget = game_widget.cards[trump_jack]
    self.assertIs(trump_card_widget, game_widget.talon_widget.trump_card)
    self.assertIs(game_widget.player_card_widgets.one, trump_jack_widget.parent)
    self.assertTrue(trump_jack_widget.grayed_out)
    self.assert_do_translation(False, trump_jack_widget)
    self.assertFalse(trump_card_widget.grayed_out)
    self.assert_do_translation(False, trump_card_widget)

    # Dragging the trump jack onto the trump card should have no effect.
    _drag_card_to_pos(trump_jack_widget, trump_card_widget.center)
    self.assertIs(trump_card_widget, game_widget.talon_widget.trump_card)
    self.assertIs(game_widget.player_card_widgets.one, trump_jack_widget.parent)
    self.assertTrue(trump_jack_widget.grayed_out)
    self.assert_do_translation(False, trump_jack_widget)
    self.assertFalse(trump_card_widget.grayed_out)
    self.assert_do_translation(False, trump_card_widget)

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()
    self.assertFalse(trump_jack_widget.grayed_out)
    # This is true since the trump jack can be dragged on the play area to play
    # it, but it cannot be dragged onto the trump card to exchange it.
    self.assert_do_translation(True, trump_jack_widget)
    self.assertFalse(trump_card_widget.grayed_out)
    self.assert_do_translation(False, trump_card_widget)

    # Dragging the trump jack outside the play area and outside the trump card,
    # should have no effect.
    pos = trump_jack_widget.pos
    _drag_card_to_pos(trump_jack_widget, game_widget.tricks_widgets.two.center)
    self.advance_frames(1)
    callback.assert_not_called()
    self.assertEqual(pos, trump_jack_widget.pos)

    # Dragging the trump jack onto the trump card should have no effect.
    _drag_card_to_pos(trump_jack_widget, trump_card_widget.center)
    self.advance_frames(1)
    callback.not_called()
    self.assertEqual(pos, trump_jack_widget.pos)

  def test_exchange_trump_card_by_dragging_talon_is_empty(self):
    game_state = get_game_state_with_empty_talon_for_tests()
    with GameStateValidator(game_state):
      trump_jack = game_state.cards_in_hand.two.pop(2)
      ten_hearts = game_state.cards_in_hand.one.pop(2)
      game_state.cards_in_hand.two.append(ten_hearts)
      game_state.cards_in_hand.one.append(trump_jack)

    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    trump_jack_widget = game_widget.cards[trump_jack]
    self.assertIsNone(game_widget.talon_widget.trump_card)
    self.assertIs(game_widget.player_card_widgets.one, trump_jack_widget.parent)
    self.assertTrue(trump_jack_widget.grayed_out)
    self.assert_do_translation(False, trump_jack_widget)

    # Dragging the trump jack onto the talon widget should have no effect.
    _drag_card_to_pos(trump_jack_widget, game_widget.talon_widget.center)
    self.assertIsNone(game_widget.talon_widget.trump_card)
    self.assertIs(game_widget.player_card_widgets.one, trump_jack_widget.parent)
    self.assertTrue(trump_jack_widget.grayed_out)
    self.assert_do_translation(False, trump_jack_widget)

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()
    self.assertFalse(trump_jack_widget.grayed_out)
    # This is true since the trump jack can be dragged on the play area to play
    # it, but it cannot be dragged onto the talon to exchange it.
    self.assert_do_translation(True, trump_jack_widget)

    # Dragging the trump jack outside the play area should have no effect.
    pos = trump_jack_widget.pos
    _drag_card_to_pos(trump_jack_widget, game_widget.tricks_widgets.two.center)
    self.advance_frames(1)
    callback.assert_not_called()
    self.assertEqual(pos, trump_jack_widget.pos)

    # Dragging the trump jack onto the talon widget should have no effect.
    _drag_card_to_pos(trump_jack_widget, game_widget.talon_widget.center)
    self.advance_frames(1)
    callback.not_called()
    self.assertEqual(pos, trump_jack_widget.pos)

  def test_dragging_non_trump_jack_card_over_the_trump_card(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    ten_spades = Card(Suit.SPADES, CardValue.TEN)
    ten_spades_widget = game_widget.cards[ten_spades]
    trump_card_widget = game_widget.talon_widget.trump_card
    self.assertIs(trump_card_widget, game_widget.talon_widget.trump_card)
    self.assertIs(game_widget.player_card_widgets.one, ten_spades_widget.parent)
    self.assertTrue(ten_spades_widget.grayed_out)
    self.assert_do_translation(False, ten_spades_widget)
    self.assertFalse(trump_card_widget.grayed_out)
    self.assert_do_translation(False, trump_card_widget)

    # Dragging the ten of spades onto the trump card should have no effect.
    _drag_card_to_pos(ten_spades_widget, trump_card_widget.center)
    self.assertIs(trump_card_widget, game_widget.talon_widget.trump_card)
    self.assertIs(game_widget.player_card_widgets.one, ten_spades_widget.parent)
    self.assertTrue(ten_spades_widget.grayed_out)
    self.assert_do_translation(False, ten_spades_widget)
    self.assertFalse(trump_card_widget.grayed_out)
    self.assert_do_translation(False, trump_card_widget)

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()
    self.assertFalse(ten_spades_widget.grayed_out)
    # This is true since the ten of spades can be dragged on the play area to
    # play it, but it cannot be dragged onto the trump card to exchange it.
    self.assert_do_translation(True, ten_spades_widget)
    self.assertFalse(trump_card_widget.grayed_out)
    self.assert_do_translation(False, trump_card_widget)

    # Dragging the ten of spades outside the play area and outside the trump
    # card, should have no effect.
    pos = ten_spades_widget.pos
    _drag_card_to_pos(ten_spades_widget, game_widget.tricks_widgets.two.center)
    self.advance_frames(1)
    callback.assert_not_called()
    self.assertEqual(pos, ten_spades_widget.pos)

    # Dragging the ten of spades onto the trump card should have no effect.
    _drag_card_to_pos(ten_spades_widget, trump_card_widget.center)
    self.advance_frames(1)
    callback.not_called()
    self.assertEqual(pos, ten_spades_widget.pos)

  def test_double_click_trump_card_when_cannot_exchange_trump_card(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    trump_card_widget = game_widget.talon_widget.trump_card

    touch = UnitTestTouch(
      trump_card_widget.center_x - trump_card_widget.width / 4,
      trump_card_widget.center_y)
    touch.is_double_tap = True
    touch.touch_down()
    touch.touch_up()

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()

    # A double-click on the trump card should have no effect.
    touch.touch_down()
    touch.touch_up()
    callback.assert_not_called()

  def test_close_the_talon_with_double_click(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    top_talon_card = game_widget.talon_widget.top_card()

    # A double-click on the talon should have no effect.
    touch = UnitTestTouch(*top_talon_card.center)
    touch.is_double_tap = True
    touch.touch_down()
    touch.touch_up()

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()

    # A double-click on the talon should call the callback with a
    # CloseTheTalonAction.
    touch.touch_down()
    touch.touch_up()
    callback.assert_called_once()
    self.assertEqual(1, len(callback.call_args.args))
    self.assertEqual({}, callback.call_args.kwargs)
    action = callback.call_args.args[0]
    self.assertIsInstance(action, CloseTheTalonAction)
    self.assertEqual(PlayerId.ONE, action.player_id)

    # A double-click on the talon card should have no effect.
    callback.reset_mock()
    touch.touch_down()
    touch.touch_up()
    callback.assert_not_called()

    # Close the talon and request the next action.
    action.execute(game_state)
    game_widget.request_next_action(game_state, callback)

    # A double-click on the talon card should have no effect.
    touch.touch_down()
    touch.touch_up()
    callback.assert_not_called()

  def test_double_click_the_talon_when_cannot_close_the_talon(self):
    # Player TWO plays a card. Player ONE will not be able close the talon.
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    action = PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.JACK))
    action.execute(game_state)

    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    top_talon_card = game_widget.talon_widget.top_card()

    # A double-click on the talon should have no effect.
    touch = UnitTestTouch(*top_talon_card.center)
    touch.is_double_tap = True
    touch.touch_down()
    touch.touch_up()

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()

    # A double-click on the talon should have no effect.
    touch.touch_down()
    touch.touch_up()
    callback.assert_not_called()

  def test_play_a_card_using_double_click(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    # A double-click on any player card should have no effect.
    for card in game_state.cards_in_hand.one:
      card_widget = game_widget.cards[card]
      self.assertTrue(card_widget.grayed_out)
      touch = UnitTestTouch(*card_widget.center)
      touch.is_double_tap = True
      touch.touch_down()
      touch.touch_up()

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()

    # All cards can be played.
    for card in game_state.cards_in_hand.one:
      card_widget = game_widget.cards[card]
      self.assertFalse(card_widget.grayed_out)

    # A double-click on a player's card should play it.
    ten_spades = Card(Suit.SPADES, CardValue.TEN)
    ten_spades_widget = game_widget.cards[ten_spades]
    touch = UnitTestTouch(*ten_spades_widget.center)
    touch.is_double_tap = True
    touch.touch_down()
    touch.touch_up()
    callback.assert_called_once()
    self.assertEqual(1, len(callback.call_args.args))
    self.assertEqual({}, callback.call_args.kwargs)
    action = callback.call_args.args[0]
    self.assertIsInstance(action, PlayCardAction)
    self.assertEqual(PlayerId.ONE, action.player_id)
    self.assertEqual(ten_spades, action.card)

    # All the player's cards are grayed out.
    for card in game_state.cards_in_hand.one:
      card_widget = game_widget.cards[card]
      self.assertTrue(card_widget.grayed_out, msg=card_widget.card)

    # A double-click on the same card should have no effect.
    callback.reset_mock()
    touch.touch_down()
    touch.touch_up()
    callback.assert_not_called()

    # A double-click on other player card should have no effect.
    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    ace_spades_widget = game_widget.cards[ace_spades]
    touch = UnitTestTouch(*ace_spades_widget.center)
    touch.is_double_tap = True
    touch.touch_down()
    touch.touch_up()
    callback.assert_not_called()

  def test_play_a_card_by_dragging(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    play_area_pos = game_widget.play_area.center[0], \
                    game_widget.play_area.center[1]

    # Dragging any player card should have no effect.
    for i, card in enumerate(game_state.cards_in_hand.one):
      card_widget = game_widget.cards[card]
      self.assertTrue(card_widget.grayed_out)
      self.assert_do_translation(False, card_widget)
      _drag_card_to_pos(card_widget, play_area_pos)
      self.assertEqual(list(game_widget.player_card_widgets.one.card_size),
                       card_widget.size, msg=card_widget.card)
      self.assertEqual(game_widget.player_card_widgets.one.get_card_pos(0, i),
                       card_widget.pos, msg=card_widget.card)

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()

    # All cards can be played.
    for card in game_state.cards_in_hand.one:
      card_widget = game_widget.cards[card]
      self.assertFalse(card_widget.grayed_out)
      self.assert_do_translation(True, card_widget)

    # Dragging any player card somewhere other than the playing area, should
    # have no effect.
    position_outside_play_area = game_widget.tricks_widgets.two.center
    for i, card in enumerate(game_state.cards_in_hand.one):
      card_widget = game_widget.cards[card]
      _drag_card_to_pos(card_widget, position_outside_play_area)
      self.assertNotEqual(
        game_widget.player_card_widgets.one.get_card_pos(0, i), card_widget.pos,
        msg=card_widget.card)
      self.advance_frames(1)
      self.assertEqual(list(game_widget.player_card_widgets.one.card_size),
                       card_widget.size, msg=card_widget.card)
      self.assertEqual(game_widget.player_card_widgets.one.get_card_pos(0, i),
                       card_widget.pos, msg=card_widget.card)

    # Dragging a player's card onto the play area, should play it.
    ten_spades = Card(Suit.SPADES, CardValue.TEN)
    ten_spades_widget = game_widget.cards[ten_spades]
    _drag_card_to_pos(ten_spades_widget, play_area_pos)
    self.advance_frames(1)
    self.assertEqual(list(game_widget.player_card_widgets.one.card_size),
                     ten_spades_widget.size)
    self.assertNotEqual(game_widget.player_card_widgets.one.get_card_pos(0, 3),
                        ten_spades_widget.pos)
    callback.assert_called_once()
    self.assertEqual(1, len(callback.call_args.args))
    self.assertEqual({}, callback.call_args.kwargs)
    action = callback.call_args.args[0]
    self.assertIsInstance(action, PlayCardAction)
    self.assertEqual(PlayerId.ONE, action.player_id)
    self.assertEqual(ten_spades, action.card)

    # All the player's cards are grayed out and cannot be dragged anymore.
    for card in game_state.cards_in_hand.one:
      card_widget = game_widget.cards[card]
      self.assertEqual(card_widget is not ten_spades_widget,
                       card_widget.grayed_out, msg=card_widget.card)
      self.assert_do_translation(False, card_widget)

    # Dragging the same card should have no effect.
    callback.reset_mock()
    old_pos = ten_spades_widget.x, ten_spades_widget.y
    new_play_area_pos = game_widget.play_area.x + 10, \
                        game_widget.play_area.y + 10
    self.assertTrue(game_widget.play_area.collide_point(*new_play_area_pos))
    _drag_card_to_pos(ten_spades_widget, new_play_area_pos)
    self.advance_frames(1)
    callback.assert_not_called()
    self.assertEqual(old_pos, ten_spades_widget.pos)

    # Dragging other player cards should have no effect.
    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    ace_spades_widget = game_widget.cards[ace_spades]
    old_pos = ace_spades_widget.x, ace_spades_widget.y
    _drag_card_to_pos(ace_spades_widget, new_play_area_pos)
    self.advance_frames(1)
    callback.assert_not_called()
    self.assertEqual(old_pos, ace_spades_widget.pos)
    callback.assert_not_called()

  def test_play_a_card_with_double_click_must_follow_suit(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
      game_state.close_talon()
    action = PlayCardAction(PlayerId.TWO, Card(Suit.SPADES, CardValue.JACK))
    action.execute(game_state)
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    # A double-click on any player card should have no effect.
    for card in game_state.cards_in_hand.one:
      card_widget = game_widget.cards[card]
      self.assertTrue(card_widget.grayed_out)
      touch = UnitTestTouch(*card_widget.center)
      touch.is_double_tap = True
      touch.touch_down()
      touch.touch_up()

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()

    # Since the player must follow suit, they can only play their SPADES cards.
    # A double-click on any of the other cards should have no effect.
    for card in game_state.cards_in_hand.one:
      card_widget = game_widget.cards[card]
      self.assertEqual(card_widget.card.suit != Suit.SPADES,
                       card_widget.grayed_out)
      if card_widget.grayed_out:
        touch = UnitTestTouch(*card_widget.center)
        touch.is_double_tap = True
        touch.touch_down()
        touch.touch_up()
        callback.assert_not_called()

  def test_play_a_card_by_dragging_must_follow_suit(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
      game_state.close_talon()
    action = PlayCardAction(PlayerId.TWO, Card(Suit.SPADES, CardValue.JACK))
    action.execute(game_state)
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    play_area_pos = game_widget.play_area.center[0], \
                    game_widget.play_area.center[1]

    # Dragging any player card should have no effect.
    for i, card in enumerate(game_state.cards_in_hand.one):
      card_widget = game_widget.cards[card]
      self.assertTrue(card_widget.grayed_out)
      self.assert_do_translation(False, card_widget)
      _drag_card_to_pos(card_widget, play_area_pos)
      self.assertEqual(list(game_widget.player_card_widgets.one.card_size),
                       card_widget.size, msg=card_widget.card)
      self.assertEqual(game_widget.player_card_widgets.one.get_card_pos(0, i),
                       card_widget.pos, msg=card_widget.card)

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()

    # Since the player must follow suit, they can only play their SPADES cards.
    # Dragging any of the other cards should have no effect.
    for i, card in enumerate(game_state.cards_in_hand.one):
      card_widget = game_widget.cards[card]
      self.assertEqual(card_widget.card.suit != Suit.SPADES,
                       card_widget.grayed_out)
      self.assert_do_translation(card_widget.card.suit == Suit.SPADES,
                                 card_widget)
      if card_widget.grayed_out:
        _drag_card_to_pos(card_widget, play_area_pos)
        self.assertEqual(list(game_widget.player_card_widgets.one.card_size),
                         card_widget.size, msg=card_widget.card)
        self.assertEqual(game_widget.player_card_widgets.one.get_card_pos(0, i),
                         card_widget.pos, msg=card_widget.card)
        callback.assert_not_called()

  def test_announce_marriage_using_double_click(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    # A double-click on any player card should have no effect.
    for card in game_state.cards_in_hand.one:
      card_widget = game_widget.cards[card]
      self.assertTrue(card_widget.grayed_out)
      touch = UnitTestTouch(*card_widget.center)
      touch.is_double_tap = True
      touch.touch_down()
      touch.touch_up()

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()

    # All cards can be played.
    for card in game_state.cards_in_hand.one:
      card_widget = game_widget.cards[card]
      self.assertFalse(card_widget.grayed_out)

    # A double-click on a marriage card should announce it.
    king_hearts = Card(Suit.HEARTS, CardValue.KING)
    king_hearts_widget = game_widget.cards[king_hearts]
    touch = UnitTestTouch(*king_hearts_widget.center)
    touch.is_double_tap = True
    touch.touch_down()
    touch.touch_up()
    callback.assert_called_once()
    self.assertEqual(1, len(callback.call_args.args))
    self.assertEqual({}, callback.call_args.kwargs)
    action = callback.call_args.args[0]
    self.assertIsInstance(action, AnnounceMarriageAction)
    self.assertEqual(PlayerId.ONE, action.player_id)
    self.assertEqual(king_hearts, action.card)

    # All the player's cards are grayed out.
    for card in game_state.cards_in_hand.one:
      card_widget = game_widget.cards[card]
      self.assertTrue(card_widget.grayed_out, msg=card_widget.card)

    # A double-click on the same card should have no effect.
    callback.reset_mock()
    touch.touch_down()
    touch.touch_up()
    callback.assert_not_called()

    # A double-click on the marriage pair card should have no effect.
    queen_hearts_widget = game_widget.cards[king_hearts.marriage_pair]
    touch = UnitTestTouch(*queen_hearts_widget.center)
    touch.is_double_tap = True
    touch.touch_down()
    touch.touch_up()
    callback.assert_not_called()

    # A double-click on other player card should have no effect.
    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    ace_spades_widget = game_widget.cards[ace_spades]
    touch = UnitTestTouch(*ace_spades_widget.center)
    touch.is_double_tap = True
    touch.touch_down()
    touch.touch_up()
    callback.assert_not_called()

  def test_announce_marriage_by_dragging(self):
    game_state = get_game_state_for_tests()
    game_widget = self.create_game_widget()
    self.render(game_widget)
    self._init_from_game_state(game_widget, game_state)

    play_area_pos = game_widget.play_area.center[0], \
                    game_widget.play_area.center[1]

    # Dragging any player card should have no effect.
    for i, card in enumerate(game_state.cards_in_hand.one):
      card_widget = game_widget.cards[card]
      self.assertTrue(card_widget.grayed_out)
      self.assert_do_translation(False, card_widget)
      _drag_card_to_pos(card_widget, play_area_pos)
      self.assertEqual(list(game_widget.player_card_widgets.one.card_size),
                       card_widget.size, msg=card_widget.card)
      self.assertEqual(game_widget.player_card_widgets.one.get_card_pos(0, i),
                       card_widget.pos, msg=card_widget.card)

    # Request the next player's action.
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    callback.assert_not_called()

    # All cards can be played.
    for card in game_state.cards_in_hand.one:
      card_widget = game_widget.cards[card]
      self.assertFalse(card_widget.grayed_out)
      self.assert_do_translation(True, card_widget)

    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    queen_hearts_widget = game_widget.cards[queen_hearts]
    king_hearts_widget = game_widget.cards[queen_hearts.marriage_pair]
    self.assert_pixels_almost_equal((dp(42), dp(25)), king_hearts_widget.pos)
    self.assert_pixels_almost_equal((dp(0), dp(25)), queen_hearts_widget.pos)

    # Announce the marriage using the card that is drawn at the bottom, to make
    # sure we test the scenario where it is moved to the top.
    self.assert_is_drawn_on_top(king_hearts_widget, queen_hearts_widget)

    # Dragging a marriage card should move the marriage pair as well.
    touch = UnitTestTouch(*queen_hearts_widget.center)
    touch.touch_down()
    touch.touch_move(*game_widget.tricks_widgets.two.pos)
    self.assert_pixels_almost_equal((dp(188), dp(150)), queen_hearts_widget.pos)
    self.assert_pixels_almost_equal([dp(181), dp(138)], king_hearts_widget.pos)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)
    callback.assert_not_called()

    # Stopping the drag outside the playing area should move the cards back to
    # their initial position.
    touch.touch_up()
    callback.assert_not_called()
    self.advance_frames(1)
    self.assert_pixels_almost_equal((dp(42), dp(25)), king_hearts_widget.pos)
    self.assert_pixels_almost_equal((dp(0), dp(25)), queen_hearts_widget.pos)

    # Dragging the card to the playing area should announce the marriage.
    _drag_card_to_pos(queen_hearts_widget, play_area_pos)
    callback.assert_called_once()
    self.assertEqual(1, len(callback.call_args.args))
    self.assertEqual({}, callback.call_args.kwargs)
    action = callback.call_args.args[0]
    self.assertIsInstance(action, AnnounceMarriageAction)
    self.assertEqual(PlayerId.ONE, action.player_id)
    self.assertEqual(queen_hearts, action.card)
    self.assert_pixels_almost_equal([dp(85), dp(120)], queen_hearts_widget.pos)
    self.assert_pixels_almost_equal([dp(77), dp(108)], king_hearts_widget.pos)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

    # All the player's cards are grayed out and cannot be dragged.
    for card in game_state.cards_in_hand.one:
      card_widget = game_widget.cards[card]
      self.assertEqual(
        card_widget not in [queen_hearts_widget, king_hearts_widget],
        card_widget.grayed_out, msg=card_widget.card)
      self.assert_do_translation(False, card_widget)

    new_drag_pos = game_widget.play_area.x + 10, game_widget.play_area.y + 10
    self.assertTrue(game_widget.collide_point(*new_drag_pos))

    # Dragging the same card should have no effect.
    callback.reset_mock()
    _drag_card_to_pos(queen_hearts_widget, new_drag_pos)
    self.advance_frames(1)
    callback.assert_not_called()
    self.assert_pixels_almost_equal([dp(85), dp(120)], queen_hearts_widget.pos)
    self.assert_pixels_almost_equal([dp(77), dp(108)], king_hearts_widget.pos)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

    # Dragging the marriage pair should have no effect.
    _drag_card_to_pos(king_hearts_widget, new_drag_pos)
    self.advance_frames(1)
    callback.assert_not_called()
    self.assert_pixels_almost_equal([dp(85), dp(120)], queen_hearts_widget.pos)
    self.assert_pixels_almost_equal([dp(77), dp(108)], king_hearts_widget.pos)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

    # Dragging other player card should have no effect.
    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    ace_spades_widget = game_widget.cards[ace_spades]
    _drag_card_to_pos(ace_spades_widget, new_drag_pos)
    callback.assert_not_called()
    self.assert_pixels_almost_equal([dp(85), dp(120)], queen_hearts_widget.pos)
    self.assert_pixels_almost_equal([dp(77), dp(108)], king_hearts_widget.pos)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)


class GameWidgetPlayerGraphicTestWithAnimations(GameWidgetPlayerGraphicTest):
  @staticmethod
  def create_game_widget():
    return GameWidget(enable_animations=True)


class GameWidgetPlayerGraphicTestWithCancelledAnimations(
  _GameWidgetWithCancelledAnimations,
  GameWidgetPlayerGraphicTestWithAnimations):
  pass
