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
from model.player_action import ExchangeTrumpCardAction, CloseTheTalonAction
from model.player_id import PlayerId
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
