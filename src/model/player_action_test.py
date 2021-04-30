#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from model.card import Card
from model.card_value import CardValue
from model.game_state_test_utils import \
  get_game_state_with_empty_talon_for_tests, get_game_state_for_tests
from model.player_action import CloseTheTalonAction, ExchangeTrumpCardAction, \
  AnnounceMarriageAction
from model.player_id import PlayerId
from model.suit import Suit


class CloseTheTalonActionTest(unittest.TestCase):
  """Tests for the CloseTheTalonAction class."""

  def test_empty_talon_cannot_be_closed(self):
    game_state = get_game_state_with_empty_talon_for_tests()
    action = CloseTheTalonAction(game_state.next_player)
    self.assertFalse(action.can_execute_on(game_state))

  def test_cannot_close_the_talon_twice(self):
    game_state = get_game_state_for_tests()
    game_state.close_talon()
    action = CloseTheTalonAction(game_state.next_player)
    self.assertFalse(action.can_execute_on(game_state))

  def test_can_only_close_talon_before_a_new_trick_is_played(self):
    game_state = get_game_state_for_tests()
    action = CloseTheTalonAction(game_state.next_player)
    self.assertTrue(action.can_execute_on(game_state))
    action = CloseTheTalonAction(game_state.next_player.opponent())
    self.assertFalse(action.can_execute_on(game_state))

    game_state.current_trick[game_state.next_player] = \
      game_state.cards_in_hand[game_state.next_player][0]
    action = CloseTheTalonAction(game_state.next_player)
    self.assertFalse(action.can_execute_on(game_state))
    action = CloseTheTalonAction(game_state.next_player.opponent())
    self.assertFalse(action.can_execute_on(game_state))
    game_state.next_player = game_state.next_player.opponent()
    action = CloseTheTalonAction(game_state.next_player.opponent())
    self.assertFalse(action.can_execute_on(game_state))

  def test_execute(self):
    game_state = get_game_state_for_tests()
    next_player = game_state.next_player
    action = CloseTheTalonAction(next_player)
    self.assertTrue(action.can_execute_on(game_state))
    action.execute(game_state)
    self.assertEqual(next_player, game_state.next_player)
    self.assertTrue(game_state.is_talon_closed)
    self.assertEqual(next_player, game_state.player_that_closed_the_talon)
    self.assertEqual(53, game_state.opponent_points_when_talon_was_closed)

  def test_cannot_execute_illegal_action(self):
    game_state = get_game_state_with_empty_talon_for_tests()
    action = CloseTheTalonAction(game_state.next_player)
    self.assertFalse(action.can_execute_on(game_state))
    with self.assertRaises(AssertionError):
      action.execute(game_state)


class ExchangeTrumpCardActionTest(unittest.TestCase):
  """Tests for the ExchangeTrumpCardAction class."""

  def test_can_only_execute_before_leading_a_trick(self):
    # Other player is to lead, cannot exchange trump.
    game_state = get_game_state_for_tests()
    self.assertTrue(game_state.on_lead(PlayerId.ONE))
    action = ExchangeTrumpCardAction(PlayerId.TWO)
    self.assertFalse(action.can_execute_on(game_state))

    # PlayerId.TWO is to lead, can exchange trump.
    game_state.next_player = PlayerId.TWO
    self.assertTrue(action.can_execute_on(game_state))

  def test_cannot_exchange_trump_when_talon_is_closed(self):
    game_state = get_game_state_for_tests()
    action = ExchangeTrumpCardAction(PlayerId.TWO)
    game_state.next_player = PlayerId.TWO
    self.assertTrue(action.can_execute_on(game_state))
    game_state.close_talon()
    self.assertFalse(action.can_execute_on(game_state))

  def test_cannot_exchange_trump_when_the_talon_is_empty(self):
    game_state = get_game_state_with_empty_talon_for_tests()
    game_state.next_player = PlayerId.TWO
    self.assertTrue(game_state.on_lead(PlayerId.TWO))
    trump_jack = Card(suit=game_state.trump, card_value=CardValue.JACK)
    self.assertTrue(trump_jack in game_state.cards_in_hand[PlayerId.TWO])
    self.assertFalse(game_state.is_talon_closed)
    action = ExchangeTrumpCardAction(PlayerId.TWO)
    self.assertFalse(action.can_execute_on(game_state))

  def test_cannot_exchange_trump_if_not_in_players_hand(self):
    game_state = get_game_state_for_tests()
    trump_jack = Card(suit=game_state.trump, card_value=CardValue.JACK)
    self.assertFalse(trump_jack in game_state.cards_in_hand[PlayerId.ONE])
    self.assertTrue(game_state.on_lead(PlayerId.ONE))
    self.assertFalse(game_state.is_talon_closed)
    action = ExchangeTrumpCardAction(PlayerId.ONE)
    self.assertFalse(action.can_execute_on(game_state))

  def test_execute(self):
    game_state = get_game_state_for_tests()
    action = ExchangeTrumpCardAction(PlayerId.TWO)
    game_state.next_player = PlayerId.TWO
    self.assertTrue(action.can_execute_on(game_state))
    trump_card = game_state.trump_card
    trump_jack = Card(suit=game_state.trump, card_value=CardValue.JACK)
    action.execute(game_state)
    self.assertEqual(game_state.trump_card, trump_jack)
    self.assertTrue(trump_card in game_state.cards_in_hand[PlayerId.TWO])
    self.assertEqual(PlayerId.TWO, game_state.next_player)

  def test_cannot_execute_illegal_action(self):
    game_state = get_game_state_for_tests()
    action = ExchangeTrumpCardAction(PlayerId.TWO)
    self.assertFalse(action.can_execute_on(game_state))
    with self.assertRaises(AssertionError):
      action.execute(game_state)


class AnnounceMarriageActionTest(unittest.TestCase):
  """Tests for the AnnounceMarriageAction class."""

  def test_can_only_instantiate_with_queen_or_king(self):
    for card in Card.get_all_cards():
      if card.card_value not in [CardValue.QUEEN, CardValue.KING]:
        with self.assertRaises(AssertionError):
          AnnounceMarriageAction(PlayerId.ONE, card)
      else:
        AnnounceMarriageAction(PlayerId.ONE, card)

  def test_can_only_execute_before_leading_a_trick(self):
    game_state = get_game_state_for_tests()
    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    action = AnnounceMarriageAction(PlayerId.ONE, queen_hearts)
    self.assertTrue(action.can_execute_on(game_state))
    king_clubs = Card(Suit.CLUBS, CardValue.KING)
    action = AnnounceMarriageAction(PlayerId.TWO, king_clubs)
    self.assertFalse(action.can_execute_on(game_state))
    game_state.next_player = PlayerId.TWO
    self.assertTrue(action.can_execute_on(game_state))

  def test_both_cards_must_be_in_hand(self):
    game_state = get_game_state_for_tests()
    game_state.next_player = PlayerId.TWO
    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    action = AnnounceMarriageAction(PlayerId.TWO, queen_diamonds)
    self.assertFalse(action.can_execute_on(game_state))
    # Swap the queen of spades with the trump card
    queen_spades = game_state.cards_in_hand[PlayerId.TWO].pop()
    game_state.cards_in_hand[PlayerId.TWO].append(game_state.trump_card)
    game_state.trump_card = queen_spades
    game_state.validate()
    action = AnnounceMarriageAction(PlayerId.TWO, queen_spades)
    self.assertFalse(action.can_execute_on(game_state))

  def test_announce_non_trump_marriage(self):
    game_state = get_game_state_for_tests()
    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    action = AnnounceMarriageAction(PlayerId.ONE, queen_hearts)
    self.assertTrue(action.can_execute_on(game_state))
    action.execute(game_state)
    self.assertEqual(42, game_state.trick_points[PlayerId.ONE])
    self.assertEqual(queen_hearts, game_state.current_trick[PlayerId.ONE])
    self.assertEqual([Suit.HEARTS], game_state.marriage_suits[PlayerId.ONE])
    self.assertEqual(PlayerId.TWO, game_state.next_player)

  def test_announce_trump_marriage(self):
    game_state = get_game_state_for_tests()
    game_state.next_player = PlayerId.TWO
    queen_clubs = Card(Suit.CLUBS, CardValue.QUEEN)
    action = AnnounceMarriageAction(PlayerId.TWO, queen_clubs)
    self.assertTrue(action.can_execute_on(game_state))
    action.execute(game_state)
    self.assertEqual(93, game_state.trick_points[PlayerId.TWO])
    self.assertEqual(queen_clubs, game_state.current_trick[PlayerId.TWO])
    self.assertEqual([Suit.DIAMONDS, Suit.CLUBS],
                     game_state.marriage_suits[PlayerId.TWO])
    self.assertEqual(PlayerId.ONE, game_state.next_player)

  def test_announce_marriage_without_scoring_any_trick(self):
    game_state = get_game_state_for_tests()
    won_tricks = game_state.won_tricks[PlayerId.ONE]
    for trick in won_tricks:
      game_state.talon.extend([trick.one, trick.two])
    game_state.won_tricks[PlayerId.ONE] = []
    game_state.trick_points[PlayerId.ONE] = 0
    game_state.marriage_suits[PlayerId.TWO] = []
    game_state.trick_points[PlayerId.TWO] = 33
    game_state.validate()

    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    action = AnnounceMarriageAction(PlayerId.ONE, queen_hearts)
    self.assertTrue(action.can_execute_on(game_state))
    action.execute(game_state)
    self.assertEqual(0, game_state.trick_points[PlayerId.ONE])
    self.assertEqual(queen_hearts, game_state.current_trick[PlayerId.ONE])
    self.assertEqual([Suit.HEARTS], game_state.marriage_suits[PlayerId.ONE])
    self.assertEqual(PlayerId.TWO, game_state.next_player)

  def test_cannot_execute_illegal_action(self):
    game_state = get_game_state_for_tests()
    queen_clubs = Card(Suit.CLUBS, CardValue.QUEEN)
    action = AnnounceMarriageAction(PlayerId.TWO, queen_clubs)
    self.assertFalse(action.can_execute_on(game_state))
    with self.assertRaises(AssertionError):
      action.execute(game_state)
