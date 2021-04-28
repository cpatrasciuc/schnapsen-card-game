#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import copy
import pprint
import unittest

from model.game_state import InvalidGameStateError, GameState
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

  def test_invalid_trick_points(self):
    correct_trick_points = self.game_state.trick_points
    for points_one in range(100):
      for points_two in range(100):
        self.game_state.trick_points = PlayerPair(points_one, points_two)
        if self.game_state.trick_points == correct_trick_points:
          continue
        with self.assertRaisesRegex(InvalidGameStateError,
                                    "Invalid trick points",
                                    msg=f"{points_one} {points_two}"):
          self.game_state.validate()

  def test_marriages_with_no_tricks_won(self):
    # Move won tricks to the talon and subtract their value.
    while len(self.game_state.won_tricks.two) > 0:
      trick = self.game_state.won_tricks.two.pop()
      self.game_state.trick_points.two -= trick.one.card_value
      self.game_state.trick_points.two -= trick.two.card_value
      self.game_state.talon.extend([trick.one, trick.two])
    with self.assertRaisesRegex(InvalidGameStateError,
                                "Invalid trick points.*two=0.*two=20"):
      self.game_state.validate()

  def test_won_tricks(self):
    # Cannot win with the same suit, but smaller card.
    trick = self.game_state.won_tricks.one[0]  # K♠, Q♠
    swapped_trick = PlayerPair(one=trick.two, two=trick.one)
    self.game_state.won_tricks.one[0] = swapped_trick
    with self.assertRaisesRegex(InvalidGameStateError,
                                "ONE cannot win this trick: Q♠, K♠"):
      self.game_state.validate()

    # Cannot win with non-trump card against a trump card.
    self.game_state = get_game_state_for_tests()
    self.game_state.won_tricks.one.append(self.game_state.won_tricks.two.pop())
    self.game_state.trick_points = PlayerPair(42, 33)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "ONE cannot win this trick: X♦, X♣"):
      self.game_state.validate()

    # Different suits, no trump. Could be valid wins for both players, since we
    # don't know who played the first card.
    self.game_state = get_game_state_for_tests()
    card = self.game_state.won_tricks.two[-1].two
    self.game_state.won_tricks.two[-1].two = \
      self.game_state.cards_in_hand.one[3]
    self.game_state.cards_in_hand.one[3] = card
    self.game_state.validate()
    self.game_state.won_tricks.one.append(self.game_state.won_tricks.two.pop())
    self.game_state.trick_points = PlayerPair(42, 33)
    self.game_state.validate()


class GameStateNewGameTest(unittest.TestCase):
  def test_new_game_is_valid(self):
    game_state = GameState.new_game(dealer=PlayerId.ONE, random_seed=321)
    game_state.validate()
    self.assertEqual(PlayerId.TWO, game_state.next_player)
    self.assertEqual(5, len(game_state.cards_in_hand.one))
    self.assertEqual(5, len(game_state.cards_in_hand.two))
    self.assertEqual(9, len(game_state.talon))
    self.assertFalse(game_state.is_talon_closed)
    self.assertEqual(0, len(game_state.won_tricks.one))
    self.assertEqual(0, len(game_state.won_tricks.two))
    self.assertEqual(0, len(game_state.marriage_suits.one))
    self.assertEqual(0, len(game_state.marriage_suits.two))
    self.assertEqual(PlayerPair(0, 0), game_state.trick_points)
    self.assertEqual(PlayerPair(0, 0), game_state.game_points)
    self.assertEqual(PlayerPair(None, None), game_state.current_trick)

  def test_same_seed_returns_same_state(self):
    game_state_1 = GameState.new_game(dealer=PlayerId.ONE, random_seed=321)
    game_state_2 = GameState.new_game(dealer=PlayerId.ONE, random_seed=321)
    self.assertEqual(game_state_1, game_state_2)
    game_state_3 = GameState.new_game(dealer=PlayerId.TWO, random_seed=321)
    self.assertNotEqual(game_state_1, game_state_3)
    self.assertEqual(game_state_1.cards_in_hand.one,
                     game_state_3.cards_in_hand.two)
    self.assertEqual(game_state_1.cards_in_hand.two,
                     game_state_3.cards_in_hand.one)
    self.assertEqual(game_state_1.trump_card, game_state_3.trump_card)
    self.assertEqual(game_state_1.talon, game_state_3.talon)

  def test_random_dealing_trumps_distribution(self):
    """
    Test that by generating multiple new games we have this distribution of
    trump cards.
    http://schnapsenstrategy.blogspot.com/2010/10/probabilities.html
    """
    num = [[0 for _ in range(5)] for _ in range(5)]
    denom = [0 for _ in range(5)]
    num_games = 10000
    for _ in range(num_games):
      game_state = GameState.new_game()

      def count_trumps(hand):
        return len([card for card in hand if card.suit == game_state.trump])

      trumps_p1 = count_trumps(game_state.cards_in_hand.one)
      trumps_p2 = count_trumps(game_state.cards_in_hand.two)

      num[trumps_p1][trumps_p2] += 1
      denom[trumps_p2] += 1
      num[trumps_p2][trumps_p1] += 1
      denom[trumps_p1] += 1

    for i in range(5):
      self.assertNotEqual(0, denom[i])
      for j in range(5):
        num[j][i] /= denom[i]
        num[j][i] = round(100 * num[j][i], 2)
    pprint.pprint(num)

    expected = [
      [12.6, 23.1, 39.6, 64.3, 100.0],
      [42.0, 49.5, 49.5, 35.7, 0.0],
      [36.0, 24.7, 11.0, 0.0, 0.0],
      [9.0, 2.7, 0.0, 0.0, 0.0],
      [0.5, 0.0, 0.0, 0.0, 0.0]
    ]

    total_diff = 0.0
    for i in range(5):
      for j in range(5):
        if expected[i][j] != 0.0:
          total_diff += expected[i][j] - num[i][j]
    self.assertLess(total_diff, 0.5)
