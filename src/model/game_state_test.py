#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import copy
import unittest

from model.game_state import InvalidGameStateError
from model.game_state_test_utils import get_game_state_for_tests, \
  get_game_state_with_empty_talon_for_tests
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit


class GameStateValidationTest(unittest.TestCase):
  """Tests for GameState.validate()"""

  def setUp(self):
    self.game_state = get_game_state_for_tests()

  def test_trump_cannot_be_none(self):
    self.game_state.trump = None
    with self.assertRaisesRegex(InvalidGameStateError,
                                "Trump suit cannot be None"):
      self.game_state.validate()

  def test_trump_and_trump_card_match(self):
    self.game_state.trump = Suit.HEARTS
    with self.assertRaisesRegex(InvalidGameStateError,
                                "trump and trump_card.suit do not match"):
      self.game_state.validate()

  def test_trump_card_is_present(self):
    self.game_state.talon.append(self.game_state.trump_card)
    self.game_state.trump_card = None
    with self.assertRaisesRegex(InvalidGameStateError,
                                "trump_card is missing"):
      self.game_state.validate()

  def test_total_number_of_cards_is_20(self):
    self.assertEqual(1, len(self.game_state.talon))
    self.game_state.talon = []
    with self.assertRaisesRegex(InvalidGameStateError,
                                "Total number of cards must be 20, not 19"):
      self.game_state.validate()
    self.game_state.talon = [None]
    with self.assertRaisesRegex(InvalidGameStateError,
                                "Total number of cards must be 20, not 19"):
      self.game_state.validate()

  def test_duplicated_cards(self):
    dup_trump_card = copy.deepcopy(self.game_state)
    dup_trump_card.cards_in_hand.one[3] = dup_trump_card.trump_card
    with self.assertRaisesRegex(InvalidGameStateError, "Duplicated cards: A♣"):
      dup_trump_card.validate()

    dup_in_hands = copy.deepcopy(self.game_state)
    dup_in_hands.cards_in_hand.one[3] = dup_in_hands.cards_in_hand.two[1]
    with self.assertRaisesRegex(InvalidGameStateError, "Duplicated cards: K♣"):
      dup_in_hands.validate()

    dup_in_hand = copy.deepcopy(self.game_state)
    dup_in_hand.cards_in_hand.one[2] = dup_in_hand.cards_in_hand.one[1]
    with self.assertRaisesRegex(InvalidGameStateError, "Duplicated cards: K♥"):
      dup_in_hand.validate()

    dup_in_talon = copy.deepcopy(self.game_state)
    dup_in_talon.cards_in_hand.one[1] = dup_in_talon.talon[0]
    with self.assertRaisesRegex(InvalidGameStateError, "Duplicated cards: J♦"):
      dup_in_talon.validate()

    dup_in_trick = copy.deepcopy(self.game_state)
    dup_in_trick.cards_in_hand.one[1] = dup_in_trick.won_tricks.two[0].one
    with self.assertRaisesRegex(InvalidGameStateError, "Duplicated cards: J♥"):
      dup_in_trick.validate()

  def test_same_number_of_cards_in_hand(self):
    card = self.game_state.cards_in_hand.one.pop()
    self.game_state.talon.append(card)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "equal number of cards .* 4 vs 5"):
      self.game_state.validate()

    self.game_state = get_game_state_with_empty_talon_for_tests()
    trick = PlayerPair(one=self.game_state.cards_in_hand.one.pop(),
                       two=self.game_state.cards_in_hand.one.pop())
    self.game_state.won_tricks.one.append(trick)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "equal number of cards .* 2 vs 4"):
      self.game_state.validate()

  def test_five_cards_in_hand(self):
    self.game_state.talon.append(self.game_state.cards_in_hand.one.pop())
    self.game_state.talon.append(self.game_state.cards_in_hand.two.pop())
    with self.assertRaisesRegex(InvalidGameStateError,
                                "The players should have 5 cards in hand: 4"):
      self.game_state.validate()
    self.game_state.is_talon_closed = True
    self.game_state.validate()

  def test_at_most_five_cards_in_hand(self):
    trick = self.game_state.won_tricks.one.pop()
    self.game_state.cards_in_hand.one.append(trick.one)
    self.game_state.cards_in_hand.two.append(trick.two)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "more than 5 cards in hand: 6"):
      self.game_state.validate()
    self.game_state.is_talon_closed = True
    with self.assertRaisesRegex(InvalidGameStateError,
                                "more than 5 cards in hand: 6"):
      self.game_state.validate()

  def test_next_player_did_not_already_play_a_card(self):
    self.game_state.current_trick.one = self.game_state.cards_in_hand.one[0]
    with self.assertRaisesRegex(InvalidGameStateError,
                                "current_trick already contains a card"):
      self.game_state.validate()
    self.game_state.next_player = PlayerId.TWO
    self.game_state.validate()
    self.game_state.current_trick.two = self.game_state.cards_in_hand.two[0]
    with self.assertRaisesRegex(InvalidGameStateError,
                                "current_trick already contains a card"):
      self.game_state.validate()

  def test_valid_game_points_values(self):
    self.game_state.game_points.one = -1
    with self.assertRaisesRegex(InvalidGameStateError,
                                "between 0 and 6: PlayerId.ONE has -1"):
      self.game_state.validate()
    for points_one in range(7):
      for points_two in range(7):
        self.game_state.game_points.one = points_one
        self.game_state.game_points.two = points_two
        self.game_state.validate()
    self.game_state.game_points.two = 7
    with self.assertRaisesRegex(InvalidGameStateError,
                                "between 0 and 6: PlayerId.TWO has 7"):
      self.game_state.validate()

  def test_empty_talon_cannot_be_closed(self):
    self.game_state = get_game_state_with_empty_talon_for_tests()
    self.game_state.is_talon_closed = True
    with self.assertRaisesRegex(InvalidGameStateError,
                                "An empty talon cannot be closed"):
      self.game_state.validate()

  def test_duplicated_marriage_suits(self):
    self.game_state.marriage_suits.two.append(Suit.DIAMONDS)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "Duplicated marriage suits: ♦"):
      self.game_state.validate()
    self.game_state.marriage_suits.two.pop()
    self.game_state.validate()
    self.game_state.marriage_suits.one.append(Suit.DIAMONDS)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "Duplicated marriage suits: ♦"):
      self.game_state.validate()

  def test_marriage_card_not_played(self):
    # One card is in the talon, one card is in the player's hand.
    card = self.game_state.won_tricks.one[-1].two
    self.game_state.won_tricks.one[-1].two = self.game_state.talon[0]
    self.game_state.talon[0] = card
    with self.assertRaisesRegex(InvalidGameStateError,
                                "♦ was announced, but no card was played"):
      self.game_state.validate()

    # Both cards are still in the players hand.
    self.game_state = get_game_state_for_tests()
    self.game_state.marriage_suits.one.append(Suit.HEARTS)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "♥ was announced, but no card was played"):
      self.game_state.validate()

    # Both cards were played, but by different players.
    self.game_state = get_game_state_for_tests()
    self.game_state.marriage_suits.one.append(Suit.SPADES)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "ONE announced .* ♠ and played one card"):
      self.game_state.validate()

    # The other player announced the marriage.
    self.game_state = get_game_state_for_tests()
    self.game_state.marriage_suits.one.append(
      self.game_state.marriage_suits.two.pop())
    with self.assertRaisesRegex(InvalidGameStateError,
                                "♦ was announced, but no card was played"):
      self.game_state.validate()
