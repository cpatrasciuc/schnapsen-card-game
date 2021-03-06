#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from model.card import Card
from model.card_value import CardValue
from model.game_state_test_utils import \
  get_game_state_with_empty_talon_for_tests, get_game_state_for_tests, \
  get_game_state_with_all_tricks_played, \
  get_game_state_with_multiple_cards_in_the_talon_for_tests
from model.game_state_validation import GameStateValidator
from model.player_action import CloseTheTalonAction, ExchangeTrumpCardAction, \
  AnnounceMarriageAction, PlayCardAction, get_available_actions
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit


class CloseTheTalonActionTest(unittest.TestCase):
  """Tests for the CloseTheTalonAction class."""

  def test_equality(self):
    self.assertEqual(CloseTheTalonAction(PlayerId.ONE),
                     CloseTheTalonAction(PlayerId.ONE))
    self.assertEqual(CloseTheTalonAction(PlayerId.TWO),
                     CloseTheTalonAction(PlayerId.TWO))
    self.assertNotEqual(CloseTheTalonAction(PlayerId.ONE),
                        CloseTheTalonAction(PlayerId.TWO))
    self.assertNotEqual(CloseTheTalonAction(PlayerId.TWO),
                        CloseTheTalonAction(PlayerId.ONE))
    self.assertNotEqual(CloseTheTalonAction(PlayerId.TWO),
                        ExchangeTrumpCardAction(PlayerId.TWO))

  def test_empty_talon_cannot_be_closed(self):
    game_state = get_game_state_with_empty_talon_for_tests()
    action = CloseTheTalonAction(game_state.next_player)
    self.assertFalse(action.can_execute_on(game_state))
    self.assertFalse(action.can_execute_on(game_state.next_player_view()))

  def test_cannot_close_the_talon_twice(self):
    game_state = get_game_state_for_tests()
    game_state.close_talon()
    action = CloseTheTalonAction(game_state.next_player)
    self.assertFalse(action.can_execute_on(game_state))
    self.assertFalse(action.can_execute_on(game_state.next_player_view()))

  def test_can_only_close_talon_before_a_new_trick_is_played(self):
    game_state = get_game_state_for_tests()
    action = CloseTheTalonAction(game_state.next_player)
    self.assertTrue(action.can_execute_on(game_state))
    self.assertTrue(action.can_execute_on(game_state.next_player_view()))
    action = CloseTheTalonAction(game_state.next_player.opponent())
    self.assertFalse(action.can_execute_on(game_state))
    self.assertFalse(action.can_execute_on(game_state.next_player_view()))

    game_state.current_trick[game_state.next_player] = \
      game_state.cards_in_hand[game_state.next_player][0]
    action = CloseTheTalonAction(game_state.next_player)
    self.assertFalse(action.can_execute_on(game_state))
    self.assertFalse(action.can_execute_on(game_state.next_player_view()))
    action = CloseTheTalonAction(game_state.next_player.opponent())
    self.assertFalse(action.can_execute_on(game_state))
    self.assertFalse(action.can_execute_on(game_state.next_player_view()))
    game_state.next_player = game_state.next_player.opponent()
    action = CloseTheTalonAction(game_state.next_player.opponent())
    self.assertFalse(action.can_execute_on(game_state))
    self.assertFalse(action.can_execute_on(game_state.next_player_view()))

  def test_execute(self):
    game_state = get_game_state_for_tests()
    next_player = game_state.next_player
    action = CloseTheTalonAction(next_player)
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
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

  def test_equality(self):
    self.assertEqual(ExchangeTrumpCardAction(PlayerId.ONE),
                     ExchangeTrumpCardAction(PlayerId.ONE))
    self.assertEqual(ExchangeTrumpCardAction(PlayerId.TWO),
                     ExchangeTrumpCardAction(PlayerId.TWO))
    self.assertNotEqual(ExchangeTrumpCardAction(PlayerId.ONE),
                        ExchangeTrumpCardAction(PlayerId.TWO))
    self.assertNotEqual(ExchangeTrumpCardAction(PlayerId.TWO),
                        ExchangeTrumpCardAction(PlayerId.ONE))
    self.assertNotEqual(ExchangeTrumpCardAction(PlayerId.TWO),
                        CloseTheTalonAction(PlayerId.TWO))

  def test_can_only_execute_before_leading_a_trick(self):
    # Other player is to lead, cannot exchange trump.
    game_state = get_game_state_for_tests()
    self.assertTrue(game_state.is_to_lead(PlayerId.ONE))
    action = ExchangeTrumpCardAction(PlayerId.TWO)
    self.assertFalse(action.can_execute_on(game_state))
    self.assertFalse(action.can_execute_on(game_state.next_player_view()))

    # PlayerId.TWO is to lead, can exchange trump.
    game_state.next_player = PlayerId.TWO
    self.assertTrue(action.can_execute_on(game_state))
    self.assertTrue(action.can_execute_on(game_state.next_player_view()))

  def test_cannot_exchange_trump_when_talon_is_closed(self):
    game_state = get_game_state_for_tests()
    action = ExchangeTrumpCardAction(PlayerId.TWO)
    game_state.next_player = PlayerId.TWO
    self.assertTrue(action.can_execute_on(game_state))
    self.assertTrue(action.can_execute_on(game_state.next_player_view()))
    game_state.close_talon()
    self.assertFalse(action.can_execute_on(game_state))
    self.assertFalse(action.can_execute_on(game_state.next_player_view()))

  def test_cannot_exchange_trump_when_the_talon_is_empty(self):
    game_state = get_game_state_with_empty_talon_for_tests()
    game_state.next_player = PlayerId.TWO
    self.assertTrue(game_state.is_to_lead(PlayerId.TWO))
    trump_jack = Card(suit=game_state.trump, card_value=CardValue.JACK)
    self.assertTrue(trump_jack in game_state.cards_in_hand.two)
    self.assertFalse(game_state.is_talon_closed)
    action = ExchangeTrumpCardAction(PlayerId.TWO)
    self.assertFalse(action.can_execute_on(game_state))
    self.assertFalse(action.can_execute_on(game_state.next_player_view()))

  def test_cannot_exchange_trump_if_not_in_players_hand(self):
    game_state = get_game_state_for_tests()
    trump_jack = Card(suit=game_state.trump, card_value=CardValue.JACK)
    self.assertFalse(trump_jack in game_state.cards_in_hand.one)
    self.assertTrue(game_state.is_to_lead(PlayerId.ONE))
    self.assertFalse(game_state.is_talon_closed)
    action = ExchangeTrumpCardAction(PlayerId.ONE)
    self.assertFalse(action.can_execute_on(game_state))
    self.assertFalse(action.can_execute_on(game_state.next_player_view()))

  def test_execute(self):
    game_state = get_game_state_for_tests()
    action = ExchangeTrumpCardAction(PlayerId.TWO)
    game_state.next_player = PlayerId.TWO
    self.assertTrue(action.can_execute_on(game_state))
    trump_card = game_state.trump_card
    trump_jack = Card(suit=game_state.trump, card_value=CardValue.JACK)
    game_state = action.execute(game_state)
    self.assertEqual(game_state.trump_card, trump_jack)
    self.assertTrue(trump_card in game_state.cards_in_hand.two)
    index = game_state.cards_in_hand.two.index(trump_card)
    self.assertTrue(game_state.cards_in_hand.two[index].public)
    self.assertEqual(PlayerId.TWO, game_state.next_player)

  def test_cannot_execute_illegal_action(self):
    game_state = get_game_state_for_tests()
    action = ExchangeTrumpCardAction(PlayerId.TWO)
    self.assertFalse(action.can_execute_on(game_state))
    with self.assertRaises(AssertionError):
      action.execute(game_state)


class AnnounceMarriageActionTest(unittest.TestCase):
  """Tests for the AnnounceMarriageAction class."""

  def test_card_property(self):
    action = AnnounceMarriageAction(PlayerId.ONE,
                                    Card(Suit.DIAMONDS, CardValue.KING))
    self.assertEqual(Card(Suit.DIAMONDS, CardValue.KING), action.card)

  def test_equality(self):
    self.assertEqual(
      AnnounceMarriageAction(PlayerId.ONE, Card(Suit.DIAMONDS, CardValue.KING)),
      AnnounceMarriageAction(PlayerId.ONE, Card(Suit.DIAMONDS, CardValue.KING)))
    self.assertNotEqual(
      AnnounceMarriageAction(PlayerId.ONE, Card(Suit.DIAMONDS, CardValue.KING)),
      AnnounceMarriageAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.KING)))
    self.assertNotEqual(
      AnnounceMarriageAction(PlayerId.ONE, Card(Suit.DIAMONDS, CardValue.KING)),
      AnnounceMarriageAction(PlayerId.ONE,
                             Card(Suit.DIAMONDS, CardValue.QUEEN)))
    self.assertNotEqual(
      AnnounceMarriageAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.KING)),
      AnnounceMarriageAction(PlayerId.ONE,
                             Card(Suit.DIAMONDS, CardValue.QUEEN)))
    self.assertNotEqual(
      AnnounceMarriageAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.KING)),
      PlayCardAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.KING)))

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
    self.assertTrue(action.can_execute_on(game_state.next_player_view()))
    king_clubs = Card(Suit.CLUBS, CardValue.KING)
    action = AnnounceMarriageAction(PlayerId.TWO, king_clubs)
    self.assertFalse(action.can_execute_on(game_state))
    self.assertFalse(action.can_execute_on(game_state.next_player_view()))
    game_state.next_player = PlayerId.TWO
    self.assertTrue(action.can_execute_on(game_state))
    self.assertTrue(action.can_execute_on(game_state.next_player_view()))

  def test_both_cards_must_be_in_hand(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    queen_diamonds = Card(Suit.DIAMONDS, CardValue.QUEEN)
    action = AnnounceMarriageAction(PlayerId.TWO, queen_diamonds)
    self.assertFalse(action.can_execute_on(game_state))
    self.assertFalse(action.can_execute_on(game_state.next_player_view()))
    # Swap the queen of spades with the trump card
    with GameStateValidator(game_state):
      queen_spades = game_state.cards_in_hand.two.pop()
      game_state.cards_in_hand.two.append(game_state.trump_card)
      game_state.trump_card = queen_spades
      game_state.trump_card.public = True
    action = AnnounceMarriageAction(PlayerId.TWO, queen_spades)
    self.assertFalse(action.can_execute_on(game_state))
    self.assertFalse(action.can_execute_on(game_state.next_player_view()))

  def test_announce_non_trump_marriage(self):
    game_state = get_game_state_for_tests()
    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    action = AnnounceMarriageAction(PlayerId.ONE, queen_hearts)
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
    self.assertEqual(42, game_state.trick_points[PlayerId.ONE])
    self.assertEqual(queen_hearts, game_state.current_trick[PlayerId.ONE])
    self.assertEqual([Suit.HEARTS], game_state.marriage_suits[PlayerId.ONE])
    self.assertEqual(PlayerId.TWO, game_state.next_player)
    king_hearts = game_state.cards_in_hand.one[1]
    self.assertTrue(king_hearts.public)

  def test_announce_trump_marriage(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    queen_clubs = Card(Suit.CLUBS, CardValue.QUEEN)
    action = AnnounceMarriageAction(PlayerId.TWO, queen_clubs)
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
    self.assertEqual(93, game_state.trick_points[PlayerId.TWO])
    self.assertEqual(queen_clubs, game_state.current_trick[PlayerId.TWO])
    self.assertEqual([Suit.DIAMONDS, Suit.CLUBS],
                     game_state.marriage_suits[PlayerId.TWO])
    self.assertEqual(PlayerId.ONE, game_state.next_player)
    king_clubs = game_state.cards_in_hand.two[1]
    self.assertTrue(king_clubs.public)

  def test_announce_marriage_without_scoring_any_trick(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      for trick in game_state.won_tricks.one:
        game_state.talon.extend([trick.one, trick.two])
      for trick in game_state.won_tricks.two:
        game_state.talon.extend([trick.one, trick.two])
      game_state.won_tricks = PlayerPair([], [])
      game_state.trick_points = PlayerPair(0, 0)
      game_state.marriage_suits[PlayerId.TWO] = []

    queen_hearts = Card(Suit.HEARTS, CardValue.QUEEN)
    action = AnnounceMarriageAction(PlayerId.ONE, queen_hearts)
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
    self.assertEqual(0, game_state.trick_points[PlayerId.ONE])
    self.assertEqual(queen_hearts, game_state.current_trick[PlayerId.ONE])
    self.assertEqual([Suit.HEARTS], game_state.marriage_suits[PlayerId.ONE])
    self.assertEqual(PlayerId.TWO, game_state.next_player)
    king_hearts = game_state.cards_in_hand.one[1]
    self.assertTrue(king_hearts.public)

  def test_announcing_marriage_is_enough_to_win_the_game(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    king_clubs = Card(Suit.CLUBS, CardValue.KING)
    action = AnnounceMarriageAction(PlayerId.TWO, king_clubs)
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
    queen_clubs = game_state.cards_in_hand.two[4]
    self.assertTrue(queen_clubs.public)
    self.assertEqual(93, game_state.trick_points[PlayerId.TWO])
    self.assertTrue(game_state.is_game_over)

  def test_cannot_execute_illegal_action(self):
    game_state = get_game_state_for_tests()
    queen_clubs = Card(Suit.CLUBS, CardValue.QUEEN)
    action = AnnounceMarriageAction(PlayerId.TWO, queen_clubs)
    self.assertFalse(action.can_execute_on(game_state))
    with self.assertRaises(AssertionError):
      action.execute(game_state)


class PlayCardActionTest(unittest.TestCase):
  """Tests for the PlayCardAction class."""

  def test_card_property(self):
    action = PlayCardAction(PlayerId.ONE, Card(Suit.DIAMONDS, CardValue.ACE))
    self.assertEqual(Card(Suit.DIAMONDS, CardValue.ACE), action.card)

  def test_equality(self):
    self.assertEqual(
      PlayCardAction(PlayerId.ONE, Card(Suit.DIAMONDS, CardValue.ACE)),
      PlayCardAction(PlayerId.ONE, Card(Suit.DIAMONDS, CardValue.ACE)))
    self.assertNotEqual(
      PlayCardAction(PlayerId.ONE, Card(Suit.DIAMONDS, CardValue.ACE)),
      PlayCardAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.ACE)))
    self.assertNotEqual(
      PlayCardAction(PlayerId.ONE, Card(Suit.DIAMONDS, CardValue.KING)),
      PlayCardAction(PlayerId.ONE, Card(Suit.DIAMONDS, CardValue.ACE)))
    self.assertNotEqual(
      PlayCardAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.KING)),
      PlayCardAction(PlayerId.ONE, Card(Suit.DIAMONDS, CardValue.ACE)))
    self.assertNotEqual(
      PlayCardAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.KING)),
      AnnounceMarriageAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.KING)))

  def test_can_only_execute_on_players_turn(self):
    game_state = get_game_state_for_tests()
    card = game_state.cards_in_hand.one[0]
    action_one = PlayCardAction(PlayerId.ONE, card)
    self.assertTrue(action_one.can_execute_on(game_state))
    self.assertTrue(action_one.can_execute_on(game_state.next_player_view()))
    action_two = PlayCardAction(PlayerId.TWO,
                                game_state.cards_in_hand.two[0])
    self.assertFalse(action_two.can_execute_on(game_state))
    self.assertFalse(action_two.can_execute_on(game_state.next_player_view()))
    game_state = action_one.execute(game_state)
    self.assertFalse(action_one.can_execute_on(game_state))
    self.assertFalse(action_one.can_execute_on(game_state.next_player_view()))
    self.assertTrue(action_two.can_execute_on(game_state))
    self.assertTrue(action_two.can_execute_on(game_state.next_player_view()))

  def test_cannot_play_cards_not_in_hand(self):
    game_state = get_game_state_for_tests()
    for card in Card.get_all_cards():
      action = PlayCardAction(PlayerId.ONE, card)
      self.assertEqual(card in game_state.cards_in_hand.one,
                       action.can_execute_on(game_state))
      self.assertEqual(card in game_state.cards_in_hand.one,
                       action.can_execute_on(game_state.next_player_view()))
    action = PlayCardAction(PlayerId.ONE,
                            game_state.cards_in_hand.one[0])
    self.assertTrue(action.can_execute_on(game_state))
    self.assertTrue(action.can_execute_on(game_state.next_player_view()))
    game_state = action.execute(game_state)
    for card in Card.get_all_cards():
      action = PlayCardAction(PlayerId.TWO, card)
      self.assertEqual(card in game_state.cards_in_hand.two,
                       action.can_execute_on(game_state))
      self.assertEqual(card in game_state.cards_in_hand.two,
                       action.can_execute_on(game_state.next_player_view()))

  def test_must_follow_suit_cannot_play_lower_card_same_suit(self):
    """
    Player.ONE has two cards of the same suit as the card played by Player.TWO,
    one lower and one higher. Player.ONE also has a trump card. The only valid
    card is the higher card having the same suit as the card played by
    Player.TWO.
    """
    game_state = get_game_state_for_tests()

    with GameStateValidator(game_state):
      ten_spades = game_state.cards_in_hand.one[3]
      jack_spades = game_state.cards_in_hand.two[3]
      game_state.cards_in_hand.two[3] = ten_spades
      game_state.cards_in_hand.one[3] = jack_spades

      queen_hearts = game_state.cards_in_hand.one[0]
      queen_clubs = game_state.cards_in_hand.two[4]
      game_state.cards_in_hand.two[4] = queen_hearts
      game_state.cards_in_hand.one[0] = queen_clubs

      game_state.close_talon()
      game_state.next_player = PlayerId.TWO

    self.assertTrue(game_state.must_follow_suit())
    action = PlayCardAction(PlayerId.TWO, ten_spades)
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
    ace_spades = Card(Suit.SPADES, CardValue.ACE)
    num_legal_cards = 0
    for card in game_state.cards_in_hand.one:
      action = PlayCardAction(PlayerId.ONE, card)
      is_legal_card = action.can_execute_on(game_state)
      self.assertEqual(card == ace_spades, is_legal_card, msg=f"{card}")
      self.assertEqual(is_legal_card,
                       action.can_execute_on(game_state.next_player_view()))
      if is_legal_card:
        num_legal_cards += 1
    self.assertEqual(1, num_legal_cards)

  def test_must_follow_suit_can_play_any_higher_card_same_suit(self):
    """
    Player.ONE has two cards of the same suit as the card played by Player.TWO,
    both higher. Player.ONE also has a trump card. Any of the two cards from the
    same suit as the card played by Player.TWO are valid.
    """
    game_state = get_game_state_for_tests()

    with GameStateValidator(game_state):
      queen_hearts = game_state.cards_in_hand.one[0]
      queen_clubs = game_state.cards_in_hand.two[4]
      game_state.cards_in_hand.two[4] = queen_hearts
      game_state.cards_in_hand.one[0] = queen_clubs
      game_state.close_talon()
      game_state.next_player = PlayerId.TWO

    self.assertTrue(game_state.must_follow_suit())
    jack_spades = Card(Suit.SPADES, CardValue.JACK)
    action = PlayCardAction(PlayerId.TWO, jack_spades)
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
    num_legal_cards = 0
    for card in game_state.cards_in_hand.one:
      action = PlayCardAction(PlayerId.ONE, card)
      is_legal_card = action.can_execute_on(game_state)
      self.assertEqual(card.suit == Suit.SPADES, is_legal_card, msg=f"{card}")
      self.assertEqual(is_legal_card,
                       action.can_execute_on(game_state.next_player_view()))
      if is_legal_card:
        num_legal_cards += 1
    self.assertEqual(2, num_legal_cards)

  def test_must_follow_suit_only_lower_card_same_suit(self):
    """
    Player.ONE has two cards of the same suit as the card played by Player.TWO,
    both lower. Player.ONE also has a trump card. Any of the two cards from the
    same suit as the card played by Player.TWO are valid.
    """
    game_state = get_game_state_for_tests()

    with GameStateValidator(game_state):
      ace_spades = game_state.cards_in_hand.one[4]
      jack_spades = game_state.cards_in_hand.two[3]
      game_state.cards_in_hand.two[3] = ace_spades
      game_state.cards_in_hand.one[4] = jack_spades

      queen_hearts = game_state.cards_in_hand.one[0]
      queen_clubs = game_state.cards_in_hand.two[4]
      game_state.cards_in_hand.two[4] = queen_hearts
      game_state.cards_in_hand.one[0] = queen_clubs

      game_state.close_talon()
      game_state.next_player = PlayerId.TWO

    self.assertTrue(game_state.must_follow_suit())
    action = PlayCardAction(PlayerId.TWO, ace_spades)
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
    num_legal_cards = 0
    for card in game_state.cards_in_hand.one:
      action = PlayCardAction(PlayerId.ONE, card)
      is_legal_card = action.can_execute_on(game_state)
      self.assertEqual(card.suit == Suit.SPADES, is_legal_card, msg=f"{card}")
      self.assertEqual(is_legal_card,
                       action.can_execute_on(game_state.next_player_view()))
      if is_legal_card:
        num_legal_cards += 1
    self.assertEqual(2, num_legal_cards)

  def test_must_follow_suit_must_use_trump(self):
    """Player.TWO has no hearts, so they must use one of the trump cards."""
    game_state = get_game_state_for_tests()
    game_state.close_talon()
    self.assertTrue(game_state.must_follow_suit())
    action = PlayCardAction(PlayerId.ONE,
                            game_state.cards_in_hand.one[0])
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
    num_legal_cards = 0
    for card in game_state.cards_in_hand.two:
      action = PlayCardAction(PlayerId.TWO, card)
      is_legal_card = action.can_execute_on(game_state)
      self.assertEqual(card.suit == game_state.trump, is_legal_card,
                       msg=f"{card}")
      self.assertEqual(is_legal_card,
                       action.can_execute_on(game_state.next_player_view()))
      if is_legal_card:
        num_legal_cards += 1
    self.assertEqual(3, num_legal_cards)

  def test_must_follow_suit_must_use_higher_trump(self):
    """
    Player.ONE plays the trump Queen. Player.TWO has three trump cards.
    The valid cards are only the trump King and Ace.
    """
    game_state = get_game_state_with_empty_talon_for_tests()

    with GameStateValidator(game_state):
      ace_clubs = game_state.cards_in_hand.one[0]
      queen_clubs = game_state.cards_in_hand.two[3]
      game_state.cards_in_hand.two[3] = ace_clubs
      game_state.cards_in_hand.one[0] = queen_clubs

    action = PlayCardAction(PlayerId.ONE, queen_clubs)
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
    num_legal_cards = 0
    valid_cards = [Card(Suit.CLUBS, CardValue.KING),
                   Card(Suit.CLUBS, CardValue.ACE)]
    for card in game_state.cards_in_hand.two:
      action = PlayCardAction(PlayerId.TWO, card)
      is_legal_card = action.can_execute_on(game_state)
      self.assertEqual(card in valid_cards, is_legal_card, msg=f"{card}")
      self.assertEqual(is_legal_card,
                       action.can_execute_on(game_state.next_player_view()))
      if is_legal_card:
        num_legal_cards += 1
    self.assertEqual(2, num_legal_cards)

  def test_must_follow_trump_can_discard_any_card(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
      game_state.close_talon()
    action = PlayCardAction(PlayerId.TWO,
                            game_state.cards_in_hand.two[0])
    game_state = action.execute(game_state)
    for card in game_state.cards_in_hand.one:
      action = PlayCardAction(PlayerId.ONE, card)
      self.assertTrue(action.can_execute_on(game_state))
      self.assertTrue(action.can_execute_on(game_state.next_player_view()))

  def test_play_trick_player_one_wins(self):
    game_state = get_game_state_for_tests()
    trump_card = game_state.trump_card
    last_talon_card = game_state.talon[0]
    queen_hearts = game_state.cards_in_hand.one[0]
    action = PlayCardAction(PlayerId.ONE, queen_hearts)
    game_state = action.execute(game_state)
    self.assertEqual(queen_hearts, game_state.current_trick[PlayerId.ONE])
    self.assertEqual(PlayerId.TWO, game_state.next_player)

    queen_diamonds = game_state.cards_in_hand.two[0]
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    game_state = action.execute(game_state)
    self.assertEqual(PlayerPair(None, None), game_state.current_trick)
    self.assertEqual(PlayerPair(28, 53), game_state.trick_points)
    self.assertEqual(PlayerPair(queen_hearts, queen_diamonds),
                     game_state.won_tricks[PlayerId.ONE][-1])
    self.assertFalse(queen_hearts in game_state.cards_in_hand.one)
    self.assertFalse(queen_diamonds in game_state.cards_in_hand.two)
    self.assertTrue(last_talon_card in game_state.cards_in_hand.one)
    self.assertTrue(trump_card in game_state.cards_in_hand.two)
    self.assertEqual([], game_state.talon)
    self.assertIsNone(game_state.trump_card)
    self.assertEqual(PlayerId.ONE, game_state.next_player)

  def test_play_trick_player_two_wins(self):
    game_state = get_game_state_for_tests()
    trump_card = game_state.trump_card
    last_talon_card = game_state.talon[0]
    queen_hearts = game_state.cards_in_hand.one[0]
    action = PlayCardAction(PlayerId.ONE, queen_hearts)
    game_state = action.execute(game_state)
    self.assertEqual(queen_hearts, game_state.current_trick[PlayerId.ONE])
    self.assertEqual(PlayerId.TWO, game_state.next_player)

    jack_clubs = game_state.cards_in_hand.two[2]
    action = PlayCardAction(PlayerId.TWO, jack_clubs)
    game_state = action.execute(game_state)
    self.assertEqual(PlayerPair(None, None), game_state.current_trick)
    self.assertEqual(PlayerPair(22, 58), game_state.trick_points)
    self.assertEqual(PlayerPair(queen_hearts, jack_clubs),
                     game_state.won_tricks[PlayerId.TWO][-1])
    self.assertFalse(queen_hearts in game_state.cards_in_hand.one)
    self.assertFalse(jack_clubs in game_state.cards_in_hand.two)
    self.assertTrue(trump_card in game_state.cards_in_hand.one)
    self.assertTrue(last_talon_card in game_state.cards_in_hand.two)
    self.assertEqual([], game_state.talon)
    self.assertIsNone(game_state.trump_card)
    self.assertEqual(PlayerId.TWO, game_state.next_player)

  def test_play_trick_talon_has_more_than_one_card(self):
    game_state = get_game_state_with_multiple_cards_in_the_talon_for_tests()

    first_talon_card = game_state.talon[0]
    second_talon_card = game_state.talon[1]

    queen_hearts = game_state.cards_in_hand.one[0]
    action = PlayCardAction(PlayerId.ONE, queen_hearts)
    game_state = action.execute(game_state)
    self.assertEqual(queen_hearts, game_state.current_trick[PlayerId.ONE])
    self.assertEqual(PlayerId.TWO, game_state.next_player)

    queen_diamonds = game_state.cards_in_hand.two[0]
    action = PlayCardAction(PlayerId.TWO, queen_diamonds)
    game_state = action.execute(game_state)
    self.assertEqual(PlayerPair(None, None), game_state.current_trick)
    self.assertEqual(PlayerPair(28, 33), game_state.trick_points)
    self.assertEqual(PlayerPair(queen_hearts, queen_diamonds),
                     game_state.won_tricks[PlayerId.ONE][-1])
    self.assertFalse(queen_hearts in game_state.cards_in_hand.one)
    self.assertFalse(queen_diamonds in game_state.cards_in_hand.two)
    self.assertTrue(first_talon_card in game_state.cards_in_hand.one)
    self.assertTrue(second_talon_card in game_state.cards_in_hand.two)
    self.assertEqual([Card(Suit.CLUBS, CardValue.TEN)], game_state.talon)
    self.assertEqual(PlayerId.ONE, game_state.next_player)

  def test_play_trick_talon_is_closed(self):
    game_state = get_game_state_for_tests()
    game_state.close_talon()

    queen_hearts = game_state.cards_in_hand.one[0]
    action = PlayCardAction(PlayerId.ONE, queen_hearts)
    game_state = action.execute(game_state)
    self.assertEqual(queen_hearts, game_state.current_trick[PlayerId.ONE])
    self.assertEqual(PlayerId.TWO, game_state.next_player)

    queen_clubs = game_state.cards_in_hand.two[4]
    action = PlayCardAction(PlayerId.TWO, queen_clubs)
    game_state = action.execute(game_state)
    self.assertEqual(PlayerPair(None, None), game_state.current_trick)
    self.assertEqual(PlayerPair(22, 59), game_state.trick_points)
    self.assertEqual(PlayerPair(queen_hearts, queen_clubs),
                     game_state.won_tricks[PlayerId.TWO][-1])
    self.assertFalse(queen_hearts in game_state.cards_in_hand.one)
    self.assertFalse(queen_clubs in game_state.cards_in_hand.two)
    self.assertEqual(4, len(game_state.cards_in_hand.one))
    self.assertEqual(4, len(game_state.cards_in_hand.two))
    self.assertEqual(PlayerId.TWO, game_state.next_player)

  def test_play_trick_talon_is_empty(self):
    game_state = get_game_state_with_empty_talon_for_tests()

    ace_clubs = game_state.cards_in_hand.one[0]
    action = PlayCardAction(PlayerId.ONE, ace_clubs)
    game_state = action.execute(game_state)
    self.assertEqual(ace_clubs, game_state.current_trick[PlayerId.ONE])
    self.assertEqual(PlayerId.TWO, game_state.next_player)

    jack_clubs = game_state.cards_in_hand.two[2]
    action = PlayCardAction(PlayerId.TWO, jack_clubs)
    game_state = action.execute(game_state)
    self.assertEqual(PlayerPair(None, None), game_state.current_trick)
    self.assertEqual(PlayerPair(48, 59), game_state.trick_points)
    self.assertEqual(PlayerPair(ace_clubs, jack_clubs),
                     game_state.won_tricks[PlayerId.ONE][-1])
    self.assertFalse(ace_clubs in game_state.cards_in_hand.one)
    self.assertFalse(jack_clubs in game_state.cards_in_hand.two)
    self.assertEqual(3, len(game_state.cards_in_hand.one))
    self.assertEqual(3, len(game_state.cards_in_hand.two))
    self.assertEqual(PlayerId.ONE, game_state.next_player)

  def test_play_trick_winner_has_pending_marriage_points(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      for trick in game_state.won_tricks.two:
        game_state.trick_points[PlayerId.TWO] -= trick.one.card_value
        game_state.trick_points[PlayerId.TWO] -= trick.two.card_value
        game_state.talon.extend([trick.one, trick.two])
      game_state.trick_points = PlayerPair(22, 0)
      game_state.won_tricks[PlayerId.TWO] = []

    first_talon_card = game_state.talon[0]
    second_talon_card = game_state.talon[1]

    queen_hearts = game_state.cards_in_hand.one[0]
    action = PlayCardAction(PlayerId.ONE, queen_hearts)
    game_state = action.execute(game_state)
    self.assertEqual(queen_hearts, game_state.current_trick[PlayerId.ONE])
    self.assertEqual(PlayerId.TWO, game_state.next_player)
    self.assertEqual([Suit.DIAMONDS], game_state.marriage_suits[PlayerId.TWO])
    self.assertEqual(0, game_state.trick_points[PlayerId.TWO])

    queen_clubs = game_state.cards_in_hand.two[4]
    action = PlayCardAction(PlayerId.TWO, queen_clubs)
    game_state = action.execute(game_state)
    self.assertEqual(PlayerPair(None, None), game_state.current_trick)
    self.assertEqual(PlayerPair(22, 26), game_state.trick_points)
    self.assertEqual(PlayerPair(queen_hearts, queen_clubs),
                     game_state.won_tricks[PlayerId.TWO][-1])
    self.assertFalse(queen_hearts in game_state.cards_in_hand.one)
    self.assertFalse(queen_clubs in game_state.cards_in_hand.two)
    self.assertTrue(second_talon_card in game_state.cards_in_hand.one)
    self.assertTrue(first_talon_card in game_state.cards_in_hand.two)
    self.assertEqual(PlayerId.TWO, game_state.next_player)

  def test_play_trick_talon_closed_opponent_cannot_follow_suit(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      trick = game_state.won_tricks.two.pop(0)
      game_state.talon.append(trick.one)
      game_state.talon.append(trick.two)
      trick = game_state.won_tricks.two.pop(0)
      game_state.talon.append(trick.one)
      game_state.talon.append(trick.two)
      game_state.trick_points.two = 0
    game_state.close_talon()
    self.assertEqual([False, False, False, False, False],
                     [card.public for card in game_state.talon])
    action = PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.TEN))
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
    self.assertEqual([False, False, False, False, False],
                     [card.public for card in game_state.talon])
    action = PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.JACK))
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
    self.assertEqual([False, True, True, False, False],
                     [card.public for card in game_state.talon])

  def test_play_trick_talon_closed_opponent_cannot_follow_suit_or_trump(self):
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      trick = game_state.won_tricks.one.pop(0)
      game_state.talon.append(trick.one)
      game_state.talon.append(trick.two)
      game_state.trick_points.one -= trick.one.card_value
      game_state.trick_points.one -= trick.two.card_value
      trick = game_state.won_tricks.two.pop(-1)
      game_state.talon.append(trick.one)
      game_state.talon.append(trick.two)
      game_state.trick_points.two -= trick.one.card_value
      game_state.trick_points.two -= trick.two.card_value
      game_state.next_player = PlayerId.TWO
    game_state.close_talon()
    self.assertEqual([False, False, False, False, False],
                     [card.public for card in game_state.talon])
    action = PlayCardAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.QUEEN))
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
    self.assertEqual([False, False, False, False, False],
                     [card.public for card in game_state.talon])
    action = PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.QUEEN))
    self.assertTrue(action.can_execute_on(game_state))
    game_state = action.execute(game_state)
    self.assertEqual([True, False, False, True, True],
                     [card.public for card in game_state.talon])


class AvailableActionsTest(unittest.TestCase):
  """Tests for the get_available_actions() functions."""

  def test_actions_when_player_is_to_lead(self):
    game_state = get_game_state_for_tests()

    actions = get_available_actions(game_state)
    self.assertEqual(set(actions),
                     set(get_available_actions(game_state.next_player_view())))
    expected_actions = [
      AnnounceMarriageAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.QUEEN)),
      AnnounceMarriageAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.KING)),
      PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.TEN)),
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)),
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)),
      CloseTheTalonAction(PlayerId.ONE),
    ]
    self.assertSetEqual(set(expected_actions), set(actions))

    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO

    actions = get_available_actions(game_state)
    self.assertEqual(set(actions),
                     set(get_available_actions(game_state.next_player_view())))
    expected_actions = [
      PlayCardAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.QUEEN)),
      AnnounceMarriageAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.KING)),
      PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.JACK)),
      AnnounceMarriageAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.QUEEN)),
      PlayCardAction(PlayerId.TWO, Card(Suit.SPADES, CardValue.JACK)),
      ExchangeTrumpCardAction(PlayerId.TWO),
      CloseTheTalonAction(PlayerId.TWO),
    ]
    self.assertSetEqual(set(expected_actions), set(actions))

  def test_actions_after_the_opponent_played_one_card(self):
    game_state = get_game_state_for_tests()
    action = PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN))
    game_state = action.execute(game_state)

    actions = get_available_actions(game_state)
    self.assertEqual(set(actions),
                     set(get_available_actions(game_state.next_player_view())))
    expected_actions = [
      PlayCardAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.QUEEN)),
      PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.KING)),
      PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.JACK)),
      PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.QUEEN)),
      PlayCardAction(PlayerId.TWO, Card(Suit.SPADES, CardValue.JACK)),
    ]
    self.assertSetEqual(set(expected_actions), set(actions))

    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    action = PlayCardAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.QUEEN))
    game_state = action.execute(game_state)

    actions = get_available_actions(game_state)
    self.assertEqual(set(actions),
                     set(get_available_actions(game_state.next_player_view())))
    expected_actions = [
      PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.QUEEN)),
      PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.KING)),
      PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.TEN)),
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)),
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)),
    ]
    self.assertSetEqual(set(expected_actions), set(actions))

  def test_actions_when_player_is_to_lead_talon_is_closed(self):
    game_state = get_game_state_for_tests()
    game_state = CloseTheTalonAction(PlayerId.ONE).execute(game_state)

    actions = get_available_actions(game_state)
    self.assertEqual(set(actions),
                     set(get_available_actions(game_state.next_player_view())))
    expected_actions = [
      AnnounceMarriageAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.QUEEN)),
      AnnounceMarriageAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.KING)),
      PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.TEN)),
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)),
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)),
    ]
    self.assertSetEqual(set(expected_actions), set(actions))

    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    game_state = CloseTheTalonAction(PlayerId.TWO).execute(game_state)

    actions = get_available_actions(game_state)
    self.assertEqual(set(actions),
                     set(get_available_actions(game_state.next_player_view())))
    expected_actions = [
      PlayCardAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.QUEEN)),
      AnnounceMarriageAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.KING)),
      PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.JACK)),
      AnnounceMarriageAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.QUEEN)),
      PlayCardAction(PlayerId.TWO, Card(Suit.SPADES, CardValue.JACK)),
    ]
    self.assertSetEqual(set(expected_actions), set(actions))

  def test_actions_after_the_opponent_played_one_card_talon_is_closed(self):
    game_state = get_game_state_for_tests()
    game_state = CloseTheTalonAction(PlayerId.ONE).execute(game_state)
    action = PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN))
    game_state = action.execute(game_state)

    actions = get_available_actions(game_state)
    self.assertEqual(set(actions),
                     set(get_available_actions(game_state.next_player_view())))
    expected_actions = [
      PlayCardAction(PlayerId.TWO, Card(Suit.SPADES, CardValue.JACK)),
    ]
    self.assertSetEqual(set(expected_actions), set(actions))

    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    game_state = CloseTheTalonAction(PlayerId.TWO).execute(game_state)
    action = PlayCardAction(PlayerId.TWO, Card(Suit.SPADES, CardValue.JACK))
    game_state = action.execute(game_state)

    actions = get_available_actions(game_state)
    self.assertEqual(set(actions),
                     set(get_available_actions(game_state.next_player_view())))
    expected_actions = [
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)),
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)),
    ]
    self.assertSetEqual(set(expected_actions), set(actions))

  def test_actions_when_player_is_to_lead_talon_is_empty(self):
    game_state = get_game_state_with_empty_talon_for_tests()

    actions = get_available_actions(game_state)
    self.assertEqual(set(actions),
                     set(get_available_actions(game_state.next_player_view())))
    expected_actions = [
      PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.ACE)),
      PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.KING)),
      PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.TEN)),
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)),
    ]
    self.assertSetEqual(set(expected_actions), set(actions))

    game_state = get_game_state_with_empty_talon_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO

    actions = get_available_actions(game_state)
    self.assertEqual(set(actions),
                     set(get_available_actions(game_state.next_player_view())))
    expected_actions = [
      PlayCardAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.JACK)),
      AnnounceMarriageAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.KING)),
      PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.JACK)),
      AnnounceMarriageAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.QUEEN)),
    ]
    self.assertSetEqual(set(expected_actions), set(actions))

  def test_actions_after_the_opponent_played_one_card_talon_is_empty(self):
    game_state = get_game_state_with_empty_talon_for_tests()
    action = PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN))
    game_state = action.execute(game_state)

    actions = get_available_actions(game_state)
    self.assertEqual(set(actions),
                     set(get_available_actions(game_state.next_player_view())))
    expected_actions = [
      PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.KING)),
      PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.JACK)),
      PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.QUEEN)),
    ]
    self.assertSetEqual(set(expected_actions), set(actions))

    game_state = get_game_state_with_empty_talon_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    action = PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.JACK))
    game_state = action.execute(game_state)

    actions = get_available_actions(game_state)
    self.assertEqual(set(actions),
                     set(get_available_actions(game_state.next_player_view())))
    expected_actions = [
      PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.ACE)),
    ]
    self.assertSetEqual(set(expected_actions), set(actions))

  def test_no_actions_available_when_game_is_over(self):
    game_state = get_game_state_with_all_tricks_played()
    self.assertEqual([], get_available_actions(game_state))
    self.assertEqual([], get_available_actions(game_state.next_player_view()))
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    self.assertEqual([], get_available_actions(game_state))
    self.assertEqual([], get_available_actions(game_state.next_player_view()))
