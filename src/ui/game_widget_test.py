#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# pylint: disable=too-many-lines,too-many-statements,too-many-locals

from collections import Counter
from typing import Tuple
from unittest.mock import Mock

from kivy.base import EventLoop
from kivy.tests.common import UnitTestTouch

from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState
from model.game_state_test_utils import get_game_state_for_tests, \
  get_game_state_with_multiple_cards_in_the_talon_for_tests
from model.game_state_validation import GameStateValidator
from model.player_action import ExchangeTrumpCardAction, CloseTheTalonAction, \
  PlayCardAction, AnnounceMarriageAction, PlayerAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit
from ui.card_widget import CardWidget
from ui.game_widget import GameWidget
from ui.test_utils import GraphicUnitTest, UiTestCase


def _drag_card_to_pos(card_widget: CardWidget, position: Tuple[int, int]):
  touch = UnitTestTouch(*card_widget.center)
  touch.touch_down()
  touch.touch_move(*position)
  touch.touch_up()


class GameWidgetTest(UiTestCase):
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
    game_widget = GameWidget()
    self._assert_initial_game_widget_state(game_widget)

  def test_init_from_game_state(self):
    game_widget = GameWidget()

    game_state = get_game_state_for_tests()
    game_widget.init_from_game_state(game_state)
    card_widgets = game_widget.cards

    # Cards for each player are in the right widgets.
    # TODO(tests): Check the visibility of the cards after adding Card.visible.
    player_card_widgets = game_widget.player_card_widgets
    for player in PlayerId:
      for card in game_state.cards_in_hand[player]:
        self.assertIs(player_card_widgets[player], card_widgets[card].parent)
        self.assertEqual(player == PlayerId.ONE, card_widgets[card].grayed_out)
        self.assert_do_translation(False, card_widgets[card])

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
    self.assertIs(game_widget.talon_widget.trump_card,
                  card_widgets[game_state.trump_card])
    self.assertTrue(card_widgets[game_state.trump_card].visible)
    self.assertFalse(card_widgets[game_state.trump_card].grayed_out)
    self.assert_do_translation(False, card_widgets[game_state.trump_card])

    # Remaining cards are in the talon.
    for card in game_state.talon:
      card_widget = game_widget.talon_widget.pop_card()
      self.assertEqual(card, card_widget.card)
      self.assertFalse(card_widget.visible)
      self.assertFalse(card_widget.grayed_out)
      self.assert_do_translation(False, card_widget)
    self.assertIsNone(game_widget.talon_widget.pop_card())

    # The trick points are correctly displayed.
    self.assertEqual("[color=ffff33]Trick points: 22[/color]",
                     game_widget.ids.human_trick_score_label.text)
    self.assertEqual("[color=ffffff]Trick points: 53[/color]",
                     game_widget.ids.computer_trick_score_label.text)

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
      game_widget = GameWidget()
      game_widget.init_from_game_state(GameState.new(), PlayerPair(points, 0))
      self.assertEqual(expected_text, game_widget.game_score_labels.one.text)
      game_widget = GameWidget()
      game_widget.init_from_game_state(GameState.new(), PlayerPair(0, points))
      self.assertEqual(expected_text, game_widget.game_score_labels.two.text)
    with self.assertRaisesRegex(AssertionError, "Invalid game score"):
      game_widget = GameWidget()
      game_widget.init_from_game_state(GameState.new(), PlayerPair(7, 4))
    with self.assertRaisesRegex(AssertionError, "Invalid game score"):
      game_widget = GameWidget()
      game_widget.init_from_game_state(GameState.new(), PlayerPair(0, -1))

  def test_reset(self):
    game_widget = GameWidget()
    self._assert_initial_game_widget_state(game_widget)
    game_widget.reset()
    self._assert_initial_game_widget_state(game_widget)
    game_widget.init_from_game_state(GameState.new())
    with self.assertRaises(AssertionError):
      self._assert_initial_game_widget_state(game_widget)
    game_widget.reset()
    self._assert_initial_game_widget_state(game_widget)

  def test_on_score_modified(self):
    game_widget = GameWidget()
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

  def test_on_action_exchange_trump_card(self):
    game_widget = GameWidget()
    game_widget.init_from_game_state(get_game_state_for_tests())
    trump_card_widget = game_widget.talon_widget.trump_card
    self.assertEqual(Card(Suit.CLUBS, CardValue.ACE), trump_card_widget.card)
    trump_jack_widget = game_widget.cards[Card(Suit.CLUBS, CardValue.JACK)]
    self.assertIs(game_widget.player_card_widgets.two, trump_jack_widget.parent)
    with self.assertRaisesRegex(AssertionError,
                                "Trump Jack not in player's hand"):
      game_widget.on_action(ExchangeTrumpCardAction(PlayerId.ONE))
    game_widget.on_action(ExchangeTrumpCardAction(PlayerId.TWO))
    self.assertEqual(Card(Suit.CLUBS, CardValue.JACK),
                     game_widget.talon_widget.trump_card.card)
    self.assertIs(game_widget.player_card_widgets.two, trump_card_widget.parent)

  def test_on_action_close_the_talon(self):
    game_widget = GameWidget()
    game_widget.init_from_game_state(get_game_state_for_tests())
    self.assertFalse(game_widget.talon_widget.closed)
    game_widget.on_action(CloseTheTalonAction(PlayerId.ONE))
    self.assertTrue(game_widget.talon_widget.closed)

  def test_on_action_unsupported_action(self):
    class UnsupportedAction(PlayerAction):
      def can_execute_on(self, _):
        return True

      def execute(self, _):
        pass

    game_widget = GameWidget()
    with self.assertRaisesRegex(AssertionError, "Should not reach this code"):
      game_widget.on_action(UnsupportedAction(PlayerId.ONE))

  def test_on_trick_completed_player_one_wins(self):
    game_widget = GameWidget()
    game_widget.init_from_game_state(get_game_state_for_tests())

    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    ace_spades_widget = game_widget.cards[ace_spades]
    game_widget.on_action(PlayCardAction(PlayerId.ONE, ace_spades))
    self.assertIs(game_widget.play_area, ace_spades_widget.parent)

    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    queen_diamonds_widget = game_widget.cards[queen_diamonds]
    game_widget.on_action(PlayCardAction(PlayerId.TWO, queen_diamonds))
    self.assertIs(game_widget.play_area, queen_diamonds_widget.parent)

    trick = PlayerPair(ace_spades, queen_diamonds)
    game_widget.on_trick_completed(trick, PlayerId.ONE)
    self.assertIs(game_widget.tricks_widgets.one, ace_spades_widget.parent)
    self.assertIs(game_widget.tricks_widgets.one, queen_diamonds_widget.parent)

  def test_on_trick_completed_player_two_wins(self):
    game_widget = GameWidget()
    game_widget.init_from_game_state(get_game_state_for_tests())

    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    queen_diamonds_widget = game_widget.cards[queen_diamonds]
    game_widget.on_action(PlayCardAction(PlayerId.TWO, queen_diamonds))
    self.assertIs(game_widget.play_area, queen_diamonds_widget.parent)

    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    ace_spades_widget = game_widget.cards[ace_spades]
    game_widget.on_action(PlayCardAction(PlayerId.ONE, ace_spades))
    self.assertIs(game_widget.play_area, ace_spades_widget.parent)

    trick = PlayerPair(ace_spades, queen_diamonds)
    game_widget.on_trick_completed(trick, PlayerId.TWO)
    self.assertIs(game_widget.tricks_widgets.two, ace_spades_widget.parent)
    self.assertIs(game_widget.tricks_widgets.two, queen_diamonds_widget.parent)

  def test_on_trick_completed_after_marriage_announced(self):
    game_widget = GameWidget()
    game_state = get_game_state_for_tests()
    game_widget.init_from_game_state(game_state)

    king_hearts = Card(Suit.HEARTS, CardValue.KING)
    king_hearts_widget = game_widget.cards[king_hearts]
    queen_hearts_widget = game_widget.cards[king_hearts.marriage_pair]
    action = AnnounceMarriageAction(PlayerId.ONE, king_hearts)
    action.execute(game_state)
    game_widget.on_action(action)
    self.assertIs(game_widget.play_area, king_hearts_widget.parent)
    self.assertIs(game_widget.play_area, queen_hearts_widget.parent)

    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    queen_diamonds_widget = game_widget.cards[queen_diamonds]
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    action.execute(game_state)
    game_widget.on_action(action)
    self.assertIs(game_widget.play_area, queen_diamonds_widget.parent)
    self.assertIs(game_widget.play_area, queen_hearts_widget.parent)

    trick = PlayerPair(king_hearts, queen_diamonds)
    game_widget.on_trick_completed(trick, PlayerId.TWO)
    self.assertIs(game_widget.tricks_widgets.two, king_hearts_widget.parent)
    self.assertIs(game_widget.player_card_widgets.one,
                  queen_hearts_widget.parent)
    self.assertIs(game_widget.tricks_widgets.two, queen_diamonds_widget.parent)

  def test_on_new_cards_drawn_last_talon_card_player_one_wins(self):
    game_widget = GameWidget()
    game_state = get_game_state_for_tests()
    game_widget.init_from_game_state(game_state)

    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    ace_spades_widget = game_widget.cards[ace_spades]
    action = PlayCardAction(PlayerId.ONE, ace_spades)
    action.execute(game_state)
    game_widget.on_action(action)
    self.assertIs(game_widget.play_area, ace_spades_widget.parent)

    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    queen_diamonds_widget = game_widget.cards[queen_diamonds]
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    action.execute(game_state)
    game_widget.on_action(action)
    self.assertIs(game_widget.play_area, queen_diamonds_widget.parent)

    trick = PlayerPair(ace_spades, queen_diamonds)
    game_widget.on_trick_completed(trick, PlayerId.TWO)
    self.assertIs(game_widget.tricks_widgets.two, ace_spades_widget.parent)
    self.assertIs(game_widget.tricks_widgets.two, queen_diamonds_widget.parent)

    last_talon_card = game_widget.talon_widget.top_card()
    self.assertIsNotNone(last_talon_card)
    trump_card = game_widget.talon_widget.trump_card
    self.assertIsNotNone(trump_card)
    game_widget.on_new_cards_drawn(game_state.cards_in_hand)
    self.assertIsNone(game_widget.talon_widget.top_card())
    self.assertIsNone(game_widget.talon_widget.trump_card)
    self.assertIs(game_widget.player_card_widgets.one, last_talon_card.parent)
    self.assertTrue(last_talon_card.visible)
    self.assertTrue(last_talon_card.grayed_out)
    self.assert_do_translation(False, last_talon_card)
    self.assertIs(game_widget.player_card_widgets.two, trump_card.parent)
    self.assertTrue(trump_card.visible)
    self.assertFalse(trump_card.grayed_out)
    self.assert_do_translation(False, trump_card)

  def test_on_new_cards_drawn_last_talon_card_player_two_wins(self):
    game_widget = GameWidget()
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    game_widget.init_from_game_state(game_state)

    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    queen_diamonds_widget = game_widget.cards[queen_diamonds]
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    action.execute(game_state)
    game_widget.on_action(action)
    self.assertIs(game_widget.play_area, queen_diamonds_widget.parent)

    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    ace_spades_widget = game_widget.cards[ace_spades]
    action = PlayCardAction(PlayerId.ONE, ace_spades)
    action.execute(game_state)
    game_widget.on_action(action)
    self.assertIs(game_widget.play_area, ace_spades_widget.parent)

    trick = PlayerPair(ace_spades, queen_diamonds)
    game_widget.on_trick_completed(trick, PlayerId.ONE)
    self.assertIs(game_widget.tricks_widgets.one, ace_spades_widget.parent)
    self.assertIs(game_widget.tricks_widgets.one, queen_diamonds_widget.parent)

    last_talon_card = game_widget.talon_widget.top_card()
    self.assertIsNotNone(last_talon_card)
    trump_card = game_widget.talon_widget.trump_card
    self.assertIsNotNone(trump_card)
    game_widget.on_new_cards_drawn(game_state.cards_in_hand)
    self.assertIsNone(game_widget.talon_widget.top_card())
    self.assertIsNone(game_widget.talon_widget.trump_card)
    self.assertIs(game_widget.player_card_widgets.two, last_talon_card.parent)
    self.assertFalse(last_talon_card.visible)
    self.assertFalse(last_talon_card.grayed_out)
    self.assert_do_translation(False, last_talon_card)
    self.assertIs(game_widget.player_card_widgets.one, trump_card.parent)
    self.assertTrue(trump_card.visible)
    self.assertTrue(trump_card.grayed_out)
    self.assert_do_translation(False, trump_card)

  def test_on_new_cards_drawn_talon_has_more_cards_player_one_wins(self):
    game_state = get_game_state_with_multiple_cards_in_the_talon_for_tests()
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)

    first_talon_card = game_widget.cards[game_state.talon[0]]
    second_talon_card = game_widget.cards[game_state.talon[1]]

    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    action = PlayCardAction(PlayerId.ONE, queen_hearts)
    action.execute(game_state)
    game_widget.on_action(action)
    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    action.execute(game_state)
    game_widget.on_action(action)
    trick = PlayerPair(queen_hearts, queen_diamonds)
    game_widget.on_trick_completed(trick, PlayerId.ONE)

    self.assertIs(first_talon_card, game_widget.talon_widget.top_card())
    self.assertIs(game_widget.talon_widget, second_talon_card.parent)
    game_widget.on_new_cards_drawn(game_state.cards_in_hand)
    self.assertIsNot(first_talon_card, game_widget.talon_widget.top_card())
    self.assertIs(game_widget.player_card_widgets.one, first_talon_card.parent)
    self.assertTrue(first_talon_card.visible)
    self.assertTrue(first_talon_card.grayed_out)
    self.assert_do_translation(False, first_talon_card)
    self.assertIs(game_widget.player_card_widgets.two, second_talon_card.parent)
    self.assertFalse(second_talon_card.visible)
    self.assertFalse(second_talon_card.grayed_out)
    self.assert_do_translation(False, second_talon_card)

  def test_on_new_cards_drawn_talon_has_more_cards_player_two_wins(self):
    game_state = get_game_state_with_multiple_cards_in_the_talon_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)

    first_talon_card = game_widget.cards[game_state.talon[0]]
    second_talon_card = game_widget.cards[game_state.talon[1]]

    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    action.execute(game_state)
    game_widget.on_action(action)
    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    action = PlayCardAction(PlayerId.ONE, queen_hearts)
    action.execute(game_state)
    game_widget.on_action(action)
    trick = PlayerPair(queen_hearts, queen_diamonds)
    game_widget.on_trick_completed(trick, PlayerId.TWO)

    self.assertIs(first_talon_card, game_widget.talon_widget.top_card())
    self.assertIs(game_widget.talon_widget, second_talon_card.parent)
    game_widget.on_new_cards_drawn(game_state.cards_in_hand)
    self.assertIsNot(first_talon_card, game_widget.talon_widget.top_card())
    self.assertIs(game_widget.player_card_widgets.two, first_talon_card.parent)
    self.assertFalse(first_talon_card.visible)
    self.assertFalse(first_talon_card.grayed_out)
    self.assert_do_translation(False, first_talon_card)
    self.assertIs(game_widget.player_card_widgets.one, second_talon_card.parent)
    self.assertTrue(second_talon_card.visible)
    self.assertTrue(second_talon_card.grayed_out)
    self.assert_do_translation(False, second_talon_card)


class GameWidgetGraphicTest(GraphicUnitTest):
  # pylint: disable=too-many-statements
  def test_do_layout(self):
    game_widget = GameWidget()
    self.render(game_widget)

    # The initial window size is 320 x 240.
    self.assertEqual([320, 240], game_widget.size)
    self.assertEqual([112, 60], game_widget.tricks_widgets.one.size)
    self.assertEqual([208, 24], game_widget.tricks_widgets.one.pos)
    self.assertEqual([112, 60], game_widget.tricks_widgets.two.size)
    self.assertEqual([208, 180], game_widget.tricks_widgets.two.pos)
    self.assertEqual([112, 72], game_widget.talon_widget.size)
    self.assertEqual([208, 108], game_widget.talon_widget.pos)
    self.assertEqual([208, 84], game_widget.player_card_widgets.one.size)
    self.assertEqual([0, 0], game_widget.player_card_widgets.one.pos)
    self.assertEqual([208, 84], game_widget.player_card_widgets.two.size)
    self.assert_list_almost_equal([0, 216],
                                  list(game_widget.player_card_widgets.two.pos))
    self.assert_list_almost_equal([166, 84], game_widget.play_area.size,
                                  places=0)
    self.assert_list_almost_equal([21, 108], game_widget.play_area.pos,
                                  places=0)

    # Stretch window horizontally to 640 x 240.
    EventLoop.window.size = 640, 240
    self.advance_frames(1)
    self.assertEqual([640, 240], game_widget.size)
    self.assertEqual([224, 60], game_widget.tricks_widgets.one.size)
    self.assertEqual([416, 24], game_widget.tricks_widgets.one.pos)
    self.assertEqual([224, 60], game_widget.tricks_widgets.two.size)
    self.assertEqual([416, 180], game_widget.tricks_widgets.two.pos)
    self.assertEqual([224, 72], game_widget.talon_widget.size)
    self.assertEqual([416, 108], game_widget.talon_widget.pos)
    self.assertEqual([416, 84], game_widget.player_card_widgets.one.size)
    self.assertEqual([0, 0], game_widget.player_card_widgets.one.pos)
    self.assertEqual([416, 84], game_widget.player_card_widgets.two.size)
    self.assert_list_almost_equal([0, 216],
                                  list(game_widget.player_card_widgets.two.pos))
    self.assert_list_almost_equal([333, 84], game_widget.play_area.size,
                                  places=0)
    self.assert_list_almost_equal([42, 108], game_widget.play_area.pos,
                                  places=0)

    # Stretch window vertically to 320 x 480.
    EventLoop.window.size = 320, 480
    self.advance_frames(1)
    self.assertEqual([320, 480], game_widget.size)
    self.assertEqual([112, 120], game_widget.tricks_widgets.one.size)
    self.assertEqual([208, 48], game_widget.tricks_widgets.one.pos)
    self.assertEqual([112, 120], game_widget.tricks_widgets.two.size)
    self.assertEqual([208, 360], game_widget.tricks_widgets.two.pos)
    self.assertEqual([112, 144], game_widget.talon_widget.size)
    self.assertEqual([208, 216], game_widget.talon_widget.pos)
    self.assertEqual([208, 168], game_widget.player_card_widgets.one.size)
    self.assertEqual([0, 0], game_widget.player_card_widgets.one.pos)
    self.assertEqual([208, 168], game_widget.player_card_widgets.two.size)
    self.assert_list_almost_equal([0, 432],
                                  list(game_widget.player_card_widgets.two.pos))
    self.assert_list_almost_equal([166, 168], game_widget.play_area.size,
                                  places=0)
    self.assert_list_almost_equal([21, 216], game_widget.play_area.pos,
                                  places=0)

    # Stretch window vertically and horizontally to 640 x 480.
    EventLoop.window.size = 640, 480
    self.advance_frames(1)
    self.assertEqual([640, 480], game_widget.size)
    self.assertEqual([224, 120], game_widget.tricks_widgets.one.size)
    self.assertEqual([416, 48], game_widget.tricks_widgets.one.pos)
    self.assertEqual([224, 120], game_widget.tricks_widgets.two.size)
    self.assertEqual([416, 360], game_widget.tricks_widgets.two.pos)
    self.assertEqual([224, 144], game_widget.talon_widget.size)
    self.assertEqual([416, 216], game_widget.talon_widget.pos)
    self.assertEqual([416, 168], game_widget.player_card_widgets.one.size)
    self.assertEqual([0, 0], game_widget.player_card_widgets.one.pos)
    self.assertEqual([416, 168], game_widget.player_card_widgets.two.size)
    self.assert_list_almost_equal([0, 432],
                                  list(game_widget.player_card_widgets.two.pos))
    self.assert_list_almost_equal([333, 168], game_widget.play_area.size,
                                  places=0)
    self.assert_list_almost_equal([42, 216], game_widget.play_area.pos,
                                  places=0)

  def test_on_action_play_card(self):
    game_widget = GameWidget()
    game_widget.init_from_game_state(get_game_state_for_tests())
    self.render(game_widget)

    with self.assertRaisesRegex(AssertionError, "Player ONE does not hold J♥"):
      game_widget.on_action(PlayCardAction(PlayerId.ONE,
                                           Card(Suit.HEARTS, CardValue.JACK)))

    ten_spades = Card(Suit.SPADES, CardValue.TEN)
    ten_spades_widget = game_widget.cards[ten_spades]
    self.assertIs(game_widget.player_card_widgets.one, ten_spades_widget.parent)
    game_widget.on_action(PlayCardAction(PlayerId.ONE, ten_spades))
    self.assertIs(game_widget.play_area, ten_spades_widget.parent)
    self.assertTrue(ten_spades_widget.visible)
    self.assertFalse(ten_spades_widget.grayed_out)
    self.assert_do_translation(False, ten_spades_widget)
    self.assertEqual([38, 59], ten_spades_widget.size)
    self.assertEqual((96.4, 138.2), ten_spades_widget.center)

    king_clubs = Card(Suit.CLUBS, CardValue.KING)
    king_clubs_widget = game_widget.cards[king_clubs]
    self.assertIs(game_widget.player_card_widgets.two, king_clubs_widget.parent)
    self.assertFalse(king_clubs_widget.visible)
    self.assertFalse(king_clubs_widget.grayed_out)
    self.assert_do_translation(False, king_clubs_widget)
    game_widget.on_action(PlayCardAction(PlayerId.TWO, king_clubs))
    self.assertIs(game_widget.play_area, king_clubs_widget.parent)
    self.assertTrue(king_clubs_widget.visible)
    self.assertFalse(king_clubs_widget.grayed_out)
    self.assert_do_translation(False, king_clubs_widget)
    self.assertEqual([38, 59], king_clubs_widget.size)
    self.assert_list_almost_equal([111.6, 161.8], king_clubs_widget.center)

  def test_on_action_play_card_by_dragging(self):
    game_state = get_game_state_for_tests()
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

    drag_pos = game_widget.play_area.x + 10, game_widget.play_area.y + 10
    self.assertNotEqual((96.4, 138.2), drag_pos)

    ten_spades = Card(Suit.SPADES, CardValue.TEN)
    ten_spades_widget = game_widget.cards[ten_spades]
    self.assertIs(game_widget.player_card_widgets.one, ten_spades_widget.parent)
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    _drag_card_to_pos(ten_spades_widget, drag_pos)
    self.advance_frames(1)
    callback.assert_called_once()
    game_widget.on_action(PlayCardAction(PlayerId.ONE, ten_spades))
    self.assertIs(game_widget.play_area, ten_spades_widget.parent)
    self.assertTrue(ten_spades_widget.visible)
    self.assertFalse(ten_spades_widget.grayed_out)
    self.assert_do_translation(False, ten_spades_widget)
    self.assertEqual([38, 59], ten_spades_widget.size)
    self.assertEqual(drag_pos, ten_spades_widget.center)

  def test_on_action_announce_marriage(self):
    game_widget = GameWidget()
    game_widget.init_from_game_state(get_game_state_for_tests())
    self.render(game_widget)

    with self.assertRaisesRegex(AssertionError, "Player ONE does not hold K♠"):
      game_widget.on_action(PlayCardAction(PlayerId.ONE,
                                           Card(Suit.SPADES, CardValue.KING)))

    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    queen_hearts_widget = game_widget.cards[queen_hearts]
    king_hearts = queen_hearts.marriage_pair
    king_hearts_widget = game_widget.cards[king_hearts]
    self.assertIs(game_widget.player_card_widgets.one,
                  queen_hearts_widget.parent)
    self.assertIs(game_widget.player_card_widgets.one,
                  king_hearts_widget.parent)
    game_widget.on_action(AnnounceMarriageAction(PlayerId.ONE, queen_hearts))
    self.assertIs(game_widget.play_area, queen_hearts_widget.parent)
    self.assertIs(game_widget.play_area, king_hearts_widget.parent)
    self.assertTrue(queen_hearts_widget.visible)
    self.assertFalse(queen_hearts_widget.grayed_out)
    self.assert_do_translation(False, queen_hearts_widget)
    self.assertTrue(king_hearts_widget.visible)
    self.assertFalse(king_hearts_widget.grayed_out)
    self.assert_do_translation(False, king_hearts_widget)
    self.assertEqual([38, 59], queen_hearts_widget.size)
    self.assertEqual([38, 59], king_hearts_widget.size)
    self.assertEqual((96.4, 138.2), queen_hearts_widget.center)
    self.assertEqual((80.4, 126.4), king_hearts_widget.center)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

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
    game_widget.on_action(AnnounceMarriageAction(PlayerId.TWO, king_clubs))
    self.assertIs(game_widget.play_area, king_clubs_widget.parent)
    self.assertIs(game_widget.play_area, queen_clubs_widget.parent)
    self.assertTrue(king_clubs_widget.visible)
    self.assertFalse(king_clubs_widget.grayed_out)
    self.assert_do_translation(False, king_clubs_widget)
    self.assertTrue(queen_clubs_widget.visible)
    self.assertFalse(queen_clubs_widget.grayed_out)
    self.assert_do_translation(False, queen_clubs_widget)
    self.assertEqual([38, 59], king_clubs_widget.size)
    self.assertEqual([38, 59], queen_clubs_widget.size)
    self.assert_list_almost_equal([111.6, 161.8], king_clubs_widget.center)
    self.assert_list_almost_equal([127.6, 173.6], queen_clubs_widget.center)
    self.assert_is_drawn_on_top(king_clubs_widget, queen_clubs_widget)

  def test_on_action_announce_marriage_by_dragging(self):
    game_state = get_game_state_for_tests()
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

    with self.assertRaisesRegex(AssertionError, "Player ONE does not hold K♠"):
      game_widget.on_action(PlayCardAction(PlayerId.ONE,
                                           Card(Suit.SPADES, CardValue.KING)))

    drag_pos = game_widget.play_area.center
    self.assertEqual([104.0, 150.0], drag_pos)

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

    self.assertEqual((104.0, 150.0), queen_hearts_widget.center)
    self.assertEqual((96.4, 138.2), king_hearts_widget.center)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

    game_widget.on_action(AnnounceMarriageAction(PlayerId.ONE, queen_hearts))

    self.assertIs(game_widget.play_area, queen_hearts_widget.parent)
    self.assertIs(game_widget.play_area, king_hearts_widget.parent)
    self.assertTrue(queen_hearts_widget.visible)
    self.assertFalse(queen_hearts_widget.grayed_out)
    self.assert_do_translation(False, queen_hearts_widget)
    self.assertTrue(king_hearts_widget.visible)
    self.assertFalse(king_hearts_widget.grayed_out)
    self.assert_do_translation(False, king_hearts_widget)
    self.assertEqual([38, 59], queen_hearts_widget.size)
    self.assertEqual([38, 59], king_hearts_widget.size)
    self.assertEqual((104.0, 150.0), queen_hearts_widget.center)
    self.assertEqual((96.4, 138.2), king_hearts_widget.center)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

  def test_cards_in_play_area_are_updated_on_window_resize(self):
    game_widget = GameWidget()
    game_widget.init_from_game_state(get_game_state_for_tests())
    self.render(game_widget)

    ten_spades = Card(Suit.SPADES, CardValue.TEN)
    ten_spades_widget = game_widget.cards[ten_spades]
    self.assertIs(game_widget.player_card_widgets.one, ten_spades_widget.parent)
    game_widget.on_action(PlayCardAction(PlayerId.ONE, ten_spades))
    self.assertIs(game_widget.play_area, ten_spades_widget.parent)
    self.assertTrue(ten_spades_widget.visible)
    self.assertFalse(ten_spades_widget.grayed_out)
    self.assert_do_translation(False, ten_spades_widget)
    self.assertEqual([38, 59], ten_spades_widget.size)
    self.assertEqual((96.4, 138.2), ten_spades_widget.center)
    EventLoop.window.size = 640, 480
    self.advance_frames(1)
    self.assertEqual([77, 118], ten_spades_widget.size)
    self.assertEqual((192.8, 276.4), ten_spades_widget.center)

  def test_cards_dragged_in_play_area_are_updated_on_window_resize(self):
    game_state = get_game_state_for_tests()
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

    drag_pos = game_widget.play_area.x + 10, game_widget.play_area.y + 10
    self.assertNotEqual((96.4, 138.2), drag_pos)

    ten_spades = Card(Suit.SPADES, CardValue.TEN)
    ten_spades_widget = game_widget.cards[ten_spades]
    self.assertIs(game_widget.player_card_widgets.one, ten_spades_widget.parent)
    callback = Mock()
    game_widget.request_next_action(game_state, callback)
    _drag_card_to_pos(ten_spades_widget, drag_pos)
    callback.assert_called_once()
    game_widget.on_action(PlayCardAction(PlayerId.ONE, ten_spades))
    self.assertIs(game_widget.play_area, ten_spades_widget.parent)
    self.assertTrue(ten_spades_widget.visible)
    self.assertFalse(ten_spades_widget.grayed_out)
    self.assert_do_translation(False, ten_spades_widget)
    self.assertEqual([38, 59], ten_spades_widget.size)
    self.assertEqual(drag_pos, ten_spades_widget.center)
    self.window.size = 640, 480
    self.advance_frames(1)
    self.assertEqual([77, 118], ten_spades_widget.size)
    self.assert_list_almost_equal([61.6, 236.0],
                                  list(ten_spades_widget.center), places=0)

  def test_marriage_dragged_in_play_area_is_updated_on_window_resize(self):
    game_state = get_game_state_for_tests()
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

    drag_pos = game_widget.play_area.x + 10, game_widget.play_area.y + 10
    self.assertTrue(game_widget.play_area.collide_point(*drag_pos))
    self.assert_list_almost_equal([30.8, 118.0], list(drag_pos))

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

    self.assert_list_almost_equal([30.799999999999997, 118.0],
                                  list(queen_hearts_widget.center), places=0)
    self.assert_list_almost_equal([23.2, 106.2],
                                  list(king_hearts_widget.center), places=0)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

    game_widget.on_action(AnnounceMarriageAction(PlayerId.ONE, queen_hearts))

    self.assertIs(game_widget.play_area, queen_hearts_widget.parent)
    self.assertIs(game_widget.play_area, king_hearts_widget.parent)
    self.assertTrue(queen_hearts_widget.visible)
    self.assertFalse(queen_hearts_widget.grayed_out)
    self.assert_do_translation(False, queen_hearts_widget)
    self.assertTrue(king_hearts_widget.visible)
    self.assertFalse(king_hearts_widget.grayed_out)
    self.assert_do_translation(False, king_hearts_widget)
    self.assertEqual([38, 59], queen_hearts_widget.size)
    self.assertEqual([38, 59], king_hearts_widget.size)
    self.assert_list_almost_equal([30.799999999999997, 118.0],
                                  list(queen_hearts_widget.center), places=0)
    self.assert_list_almost_equal([23.2, 106.2],
                                  list(king_hearts_widget.center), places=0)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

    # Resize the window.
    self.window.size = 640, 480
    self.advance_frames(1)
    self.assertEqual([77, 118], queen_hearts_widget.size)
    self.assertEqual([77, 118], king_hearts_widget.size)
    self.assert_list_almost_equal([61.6, 236.0],
                                  list(queen_hearts_widget.center), places=0)
    self.assert_list_almost_equal([46.4, 212.4],
                                  list(king_hearts_widget.center), places=0)


class GameWidgetPlayerGraphicTest(GraphicUnitTest):
  def test_exchange_trump_card_with_double_click(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      trump_jack = game_state.cards_in_hand.two.pop(2)
      ten_hearts = game_state.cards_in_hand.one.pop(2)
      game_state.cards_in_hand.two.append(ten_hearts)
      game_state.cards_in_hand.one.append(trump_jack)

    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

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

  def test_double_click_trump_card_when_cannot_exchange_trump_card(self):
    game_state = get_game_state_for_tests()
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

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
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

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

    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

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
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

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
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

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
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

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
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

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
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

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
    game_widget = GameWidget()
    game_widget.init_from_game_state(game_state)
    self.render(game_widget)

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
    self.assertEqual((41, 25), king_hearts_widget.pos)
    self.assertEqual((0, 25), queen_hearts_widget.pos)

    # Announce the marriage using the card that is drawn at the bottom, to make
    # sure we test the scenario where it is moved to the top.
    self.assert_is_drawn_on_top(king_hearts_widget, queen_hearts_widget)

    # Dragging a marriage card should move the marriage pair as well.
    touch = UnitTestTouch(*queen_hearts_widget.center)
    touch.touch_down()
    touch.touch_move(*game_widget.tricks_widgets.two.pos)
    self.assertEqual((189.0, 150.5), queen_hearts_widget.pos)
    self.assertEqual((181.4, 138.7), king_hearts_widget.pos)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)
    callback.assert_not_called()

    # Stopping the drag outside the playing area should move the cards back to
    # their initial position.
    touch.touch_up()
    callback.assert_not_called()
    self.advance_frames(1)
    self.assertEqual((41, 25), king_hearts_widget.pos)
    self.assertEqual((0, 25), queen_hearts_widget.pos)

    # Dragging the card to the playing area should announce the marriage.
    _drag_card_to_pos(queen_hearts_widget, play_area_pos)
    callback.assert_called_once()
    self.assertEqual(1, len(callback.call_args.args))
    self.assertEqual({}, callback.call_args.kwargs)
    action = callback.call_args.args[0]
    self.assertIsInstance(action, AnnounceMarriageAction)
    self.assertEqual(PlayerId.ONE, action.player_id)
    self.assertEqual(queen_hearts, action.card)
    self.assertEqual((85.0, 120.5), queen_hearts_widget.pos)
    self.assertEqual((77.4, 108.7), king_hearts_widget.pos)
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
    self.assertEqual((85.0, 120.5), queen_hearts_widget.pos)
    self.assertEqual((77.4, 108.7), king_hearts_widget.pos)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

    # Dragging the marriage pair should have no effect.
    _drag_card_to_pos(king_hearts_widget, new_drag_pos)
    self.advance_frames(1)
    callback.assert_not_called()
    self.assertEqual((85.0, 120.5), queen_hearts_widget.pos)
    self.assertEqual((77.4, 108.7), king_hearts_widget.pos)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)

    # Dragging other player card should have no effect.
    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    ace_spades_widget = game_widget.cards[ace_spades]
    _drag_card_to_pos(ace_spades_widget, new_drag_pos)
    callback.assert_not_called()
    self.assertEqual((85.0, 120.5), queen_hearts_widget.pos)
    self.assertEqual((77.4, 108.7), king_hearts_widget.pos)
    self.assert_is_drawn_on_top(queen_hearts_widget, king_hearts_widget)
