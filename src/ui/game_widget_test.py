#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from typing import List

from kivy.base import EventLoop
from kivy.tests.common import GraphicUnitTest

from model.card import Card
from model.card_value import CardValue
from model.game_state_test_utils import get_game_state_for_tests
from model.player_action import ExchangeTrumpCardAction, CloseTheTalonAction, \
  PlayCardAction, AnnounceMarriageAction, PlayerAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit
from ui.game_widget import GameWidget


class GameWidgetTest(unittest.TestCase):
  def test_create_empty_widget(self):
    game_widget = GameWidget()

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

    # Cards for already played tricks are in the right widgets.
    tricks_widgets = game_widget.tricks_widgets
    for player in PlayerId:
      for trick in game_state.won_tricks[player]:
        self.assertIs(tricks_widgets[player], card_widgets[trick.one].parent)
        self.assertTrue(card_widgets[trick.one].visible)
        self.assertIs(tricks_widgets[player], card_widgets[trick.two].parent)
        self.assertTrue(card_widgets[trick.two].visible)

    # Trump card is correctly set.
    self.assertIs(game_widget.talon_widget.trump_card,
                  card_widgets[game_state.trump_card])
    self.assertTrue(card_widgets[game_state.trump_card].visible)

    # Remaining cards are in the talon.
    for card in game_state.talon:
      card_widget = game_widget.talon_widget.pop_card()
      self.assertEqual(card, card_widget.card)
      self.assertFalse(card_widget.visible)
    self.assertIsNone(game_widget.talon_widget.pop_card())

    # The trick points are correctly displayed.
    self.assertEqual("Trick points: 22",
                     game_widget.ids.human_trick_score_label.text)
    self.assertEqual("Trick points: 53",
                     game_widget.ids.computer_trick_score_label.text)

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


class GameWidgetGraphicTest(GraphicUnitTest):
  # pylint: disable=invalid-name
  def assertListAlmostEqual(self, first: List, second: List,
                            places: int = 7, msg: str = ""):
    self.assertEqual(len(first), len(second), msg=msg + "\nDifferent lengths.")
    for i, item in enumerate(first):
      self.assertAlmostEqual(item, second[i],
                             msg=msg + f"\nFirst diff at index {i}.",
                             places=places)

  # pylint: disable=too-many-statements
  def test_do_layout(self):
    EventLoop.ensure_window()
    game_widget = GameWidget()
    self.render(game_widget)

    # The default window size for tests is 320 x 240.
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
    self.assertListAlmostEqual([0, 216],
                               list(game_widget.player_card_widgets.two.pos))
    self.assertListAlmostEqual([166, 84], game_widget.play_area.size, places=0)
    self.assertListAlmostEqual([21, 108], game_widget.play_area.pos, places=0)

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
    self.assertListAlmostEqual([0, 216],
                               list(game_widget.player_card_widgets.two.pos))
    self.assertListAlmostEqual([333, 84], game_widget.play_area.size, places=0)
    self.assertListAlmostEqual([42, 108], game_widget.play_area.pos, places=0)

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
    self.assertListAlmostEqual([0, 432],
                               list(game_widget.player_card_widgets.two.pos))
    self.assertListAlmostEqual([166, 168], game_widget.play_area.size, places=0)
    self.assertListAlmostEqual([21, 216], game_widget.play_area.pos, places=0)

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
    self.assertListAlmostEqual([0, 432],
                               list(game_widget.player_card_widgets.two.pos))
    self.assertListAlmostEqual([333, 168], game_widget.play_area.size, places=0)
    self.assertListAlmostEqual([42, 216], game_widget.play_area.pos, places=0)

  def test_on_action_play_card(self):
    EventLoop.ensure_window()
    EventLoop.window.size = 320, 240

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
    self.assertEqual([38, 59], ten_spades_widget.size)
    self.assertEqual((96.4, 138.2), ten_spades_widget.center)

    king_clubs = Card(Suit.CLUBS, CardValue.KING)
    king_clubs_widget = game_widget.cards[king_clubs]
    self.assertIs(game_widget.player_card_widgets.two, king_clubs_widget.parent)
    self.assertFalse(king_clubs_widget.visible)
    game_widget.on_action(PlayCardAction(PlayerId.TWO, king_clubs))
    self.assertIs(game_widget.play_area, king_clubs_widget.parent)
    self.assertTrue(king_clubs_widget.visible)
    self.assertEqual([38, 59], king_clubs_widget.size)
    self.assertListAlmostEqual([111.6, 161.8], king_clubs_widget.center)

  def test_on_action_announce_marriage(self):
    EventLoop.ensure_window()
    EventLoop.window.size = 320, 240

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
    self.assertTrue(king_hearts_widget.visible)
    self.assertEqual([38, 59], queen_hearts_widget.size)
    self.assertEqual([38, 59], king_hearts_widget.size)
    self.assertEqual((96.4, 138.2), queen_hearts_widget.center)
    self.assertEqual((80.4, 126.4), king_hearts_widget.center)

    king_clubs = Card(Suit.CLUBS, CardValue.KING)
    king_clubs_widget = game_widget.cards[king_clubs]
    queen_clubs = king_clubs.marriage_pair
    queen_clubs_widget = game_widget.cards[queen_clubs]
    self.assertIs(game_widget.player_card_widgets.two, king_clubs_widget.parent)
    self.assertIs(game_widget.player_card_widgets.two,
                  queen_clubs_widget.parent)
    self.assertFalse(king_clubs_widget.visible)
    self.assertFalse(queen_clubs_widget.visible)
    game_widget.on_action(AnnounceMarriageAction(PlayerId.TWO, king_clubs))
    self.assertIs(game_widget.play_area, king_clubs_widget.parent)
    self.assertIs(game_widget.play_area, queen_clubs_widget.parent)
    self.assertTrue(king_clubs_widget.visible)
    self.assertTrue(queen_clubs_widget.visible)
    self.assertEqual([38, 59], king_clubs_widget.size)
    self.assertEqual([38, 59], queen_clubs_widget.size)
    self.assertListAlmostEqual([111.6, 161.8], king_clubs_widget.center)
    self.assertListAlmostEqual([127.6, 173.6], queen_clubs_widget.center)
