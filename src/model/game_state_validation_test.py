#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import copy
import os
import subprocess
import sys
import unittest

from model.game_state import InvalidGameStateError, GameState
from model.game_state_test_utils import get_game_state_for_tests, \
  get_game_state_with_empty_talon_for_tests
from model.game_state_validation import validate, GameStateValidator, \
  validate_game_states
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit


class ValidateTest(unittest.TestCase):
  """Tests for validate(). They should call validate() directly."""

  def setUp(self):
    self.game_state = get_game_state_for_tests()

  def test_trump_cannot_be_none(self):
    self.game_state.trump = None
    with self.assertRaisesRegex(InvalidGameStateError,
                                "Trump suit cannot be None"):
      validate(self.game_state)

  def test_trump_and_trump_card_match(self):
    self.game_state.trump = Suit.HEARTS
    with self.assertRaisesRegex(InvalidGameStateError,
                                "trump and trump_card.suit do not match"):
      validate(self.game_state)

  def test_trump_card_is_present(self):
    self.game_state.talon.append(self.game_state.trump_card)
    self.game_state.trump_card = None
    with self.assertRaisesRegex(InvalidGameStateError,
                                "trump_card is missing"):
      validate(self.game_state)

  def test_total_number_of_cards_is_20(self):
    self.assertEqual(1, len(self.game_state.talon))
    self.game_state.talon = []
    with self.assertRaisesRegex(InvalidGameStateError,
                                "Total number of cards must be 20, not 19"):
      validate(self.game_state)
    self.game_state.talon = [None]
    with self.assertRaisesRegex(InvalidGameStateError,
                                "Total number of cards must be 20, not 19"):
      validate(self.game_state)

  def test_duplicated_cards(self):
    dup_trump_card = copy.deepcopy(self.game_state)
    dup_trump_card.cards_in_hand.one[3] = dup_trump_card.trump_card
    with self.assertRaisesRegex(InvalidGameStateError, "Duplicated cards: A♣"):
      validate(dup_trump_card)

    dup_in_hands = copy.deepcopy(self.game_state)
    dup_in_hands.cards_in_hand.one[3] = dup_in_hands.cards_in_hand.two[1]
    with self.assertRaisesRegex(InvalidGameStateError, "Duplicated cards: K♣"):
      validate(dup_in_hands)

    dup_in_hand = copy.deepcopy(self.game_state)
    dup_in_hand.cards_in_hand.one[2] = dup_in_hand.cards_in_hand.one[1]
    with self.assertRaisesRegex(InvalidGameStateError, "Duplicated cards: K♥"):
      validate(dup_in_hand)

    dup_in_talon = copy.deepcopy(self.game_state)
    dup_in_talon.cards_in_hand.one[1] = dup_in_talon.talon[0]
    with self.assertRaisesRegex(InvalidGameStateError, "Duplicated cards: J♦"):
      validate(dup_in_talon)

    dup_in_trick = copy.deepcopy(self.game_state)
    dup_in_trick.cards_in_hand.one[1] = dup_in_trick.won_tricks.two[0].one
    with self.assertRaisesRegex(InvalidGameStateError, "Duplicated cards: J♥"):
      validate(dup_in_trick)

  def test_same_number_of_cards_in_hand(self):
    card = self.game_state.cards_in_hand.one.pop()
    self.game_state.talon.append(card)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "equal number of cards .* 4 vs 5"):
      validate(self.game_state)

    self.game_state = get_game_state_with_empty_talon_for_tests()
    trick = PlayerPair(one=self.game_state.cards_in_hand.one.pop(),
                       two=self.game_state.cards_in_hand.one.pop())
    self.game_state.won_tricks.one.append(trick)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "equal number of cards .* 2 vs 4"):
      validate(self.game_state)

  def test_five_cards_in_hand(self):
    self.game_state.talon.append(self.game_state.cards_in_hand.one.pop())
    self.game_state.talon.append(self.game_state.cards_in_hand.two.pop())
    with self.assertRaisesRegex(InvalidGameStateError,
                                "The players should have 5 cards in hand: 4"):
      validate(self.game_state)
    self.game_state.close_talon()
    validate(self.game_state)

  def test_at_most_five_cards_in_hand(self):
    trick = self.game_state.won_tricks.one.pop()
    self.game_state.cards_in_hand.one.append(trick.one)
    self.game_state.cards_in_hand.two.append(trick.two)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "more than 5 cards in hand: 6"):
      validate(self.game_state)
    self.game_state.close_talon()
    with self.assertRaisesRegex(InvalidGameStateError,
                                "more than 5 cards in hand: 6"):
      validate(self.game_state)

  def test_next_player_did_not_already_play_a_card(self):
    self.game_state.current_trick.one = self.game_state.cards_in_hand.one[0]
    with self.assertRaisesRegex(InvalidGameStateError,
                                "current_trick already contains a card"):
      validate(self.game_state)
    self.game_state.next_player = PlayerId.TWO
    validate(self.game_state)
    self.game_state.current_trick.two = self.game_state.cards_in_hand.two[0]
    with self.assertRaisesRegex(InvalidGameStateError,
                                "current_trick already contains a card"):
      validate(self.game_state)

  def test_valid_game_points_values(self):
    self.game_state.game_points.one = -1
    with self.assertRaisesRegex(InvalidGameStateError,
                                "between 0 and 6: ONE has -1"):
      validate(self.game_state)
    for points_one in range(7):
      for points_two in range(7):
        self.game_state.game_points.one = points_one
        self.game_state.game_points.two = points_two
        validate(self.game_state)
    self.game_state.game_points.two = 7
    with self.assertRaisesRegex(InvalidGameStateError,
                                "between 0 and 6: TWO has 7"):
      validate(self.game_state)

  def test_empty_talon_cannot_be_closed(self):
    self.game_state = get_game_state_with_empty_talon_for_tests()
    with self.assertRaisesRegex(InvalidGameStateError,
                                "An empty talon cannot be closed"):
      self.game_state.close_talon()
    # Bypass the checks above by manually setting the fields (not recommended).
    self.game_state.player_that_closed_the_talon = self.game_state.next_player
    self.game_state.opponent_points_when_talon_was_closed = 10
    with self.assertRaisesRegex(InvalidGameStateError,
                                "An empty talon cannot be closed"):
      validate(self.game_state)

  def test_cannot_close_the_talon_twice(self):
    self.game_state.close_talon()
    with self.assertRaisesRegex(InvalidGameStateError,
                                "The talon is already closed"):
      self.game_state.close_talon()

  def test_can_only_close_talon_before_a_new_trick_is_played(self):
    next_player = self.game_state.next_player
    self.assertTrue(self.game_state.is_to_lead(next_player))
    self.game_state.current_trick[next_player] = \
      self.game_state.cards_in_hand[next_player][0]
    self.game_state.next_player = next_player.opponent()
    with self.assertRaisesRegex(InvalidGameStateError,
                                "only be closed by the player that is to lead"):
      self.game_state.close_talon()

  def test_if_talon_is_closed_opponents_points_must_be_set(self):
    self.game_state.player_that_closed_the_talon = self.game_state.next_player
    with self.assertRaisesRegex(InvalidGameStateError,
                                "must be either both set or both None"):
      validate(self.game_state)
    self.game_state.player_that_closed_the_talon = None
    self.game_state.opponent_points_when_talon_was_closed = 10
    with self.assertRaisesRegex(InvalidGameStateError,
                                "must be either both set or both None"):
      validate(self.game_state)
    self.game_state.player_that_closed_the_talon = self.game_state.next_player
    self.game_state.opponent_points_when_talon_was_closed = \
      self.game_state.trick_points[self.game_state.next_player.opponent()] + 1
    with self.assertRaisesRegex(InvalidGameStateError,
                                "greater than the current value"):
      validate(self.game_state)

  def test_duplicated_marriage_suits(self):
    self.game_state.marriage_suits.two.append(Suit.DIAMONDS)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "Duplicated marriage suits: ♦"):
      validate(self.game_state)
    self.game_state.marriage_suits.two.pop()
    validate(self.game_state)
    self.game_state.marriage_suits.one.append(Suit.DIAMONDS)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "Duplicated marriage suits: ♦"):
      validate(self.game_state)

  def test_marriage_card_not_played(self):
    # One card is in the talon, one card is in the player's hand.
    card = self.game_state.won_tricks.one[-1].two
    self.game_state.won_tricks.one[-1].two = self.game_state.talon[0]
    self.game_state.talon[0] = card
    with self.assertRaisesRegex(InvalidGameStateError,
                                "♦ was announced, but no card was played"):
      validate(self.game_state)

    # Both cards are still in the player's hand.
    self.game_state = get_game_state_for_tests()
    self.game_state.marriage_suits.one.append(Suit.HEARTS)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "♥ was announced, but no card was played"):
      validate(self.game_state)

    # Both cards are still in the player's hand, but they just announced it and
    # played one card.
    self.game_state = get_game_state_for_tests()
    king_hearts = self.game_state.cards_in_hand.one[1]
    self.game_state.current_trick.one = king_hearts
    self.game_state.marriage_suits.one.append(Suit.HEARTS)
    self.game_state.trick_points.one += 20
    self.game_state.next_player = PlayerId.TWO
    validate(self.game_state)

    # Both cards were played, but by different players.
    self.game_state = get_game_state_for_tests()
    self.game_state.marriage_suits.one.append(Suit.SPADES)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "ONE announced .* ♠ and played one card"):
      validate(self.game_state)

    # The other player announced the marriage.
    self.game_state = get_game_state_for_tests()
    self.game_state.marriage_suits.one.append(
      self.game_state.marriage_suits.two.pop())
    with self.assertRaisesRegex(InvalidGameStateError,
                                "♦ was announced, but no card was played"):
      validate(self.game_state)

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
          validate(self.game_state)

  def test_marriages_with_no_tricks_won(self):
    # Move won tricks to the talon and subtract their value.
    while len(self.game_state.won_tricks.two) > 0:
      trick = self.game_state.won_tricks.two.pop()
      self.game_state.trick_points.two -= trick.one.card_value
      self.game_state.trick_points.two -= trick.two.card_value
      self.game_state.talon.extend([trick.one, trick.two])
    with self.assertRaisesRegex(InvalidGameStateError,
                                "Invalid trick points.*two=0.*two=20"):
      validate(self.game_state)

  def test_won_tricks(self):
    # Cannot win with the same suit, but smaller card.
    trick = self.game_state.won_tricks.one[0]  # K♠, Q♠
    swapped_trick = PlayerPair(one=trick.two, two=trick.one)
    self.game_state.won_tricks.one[0] = swapped_trick
    with self.assertRaisesRegex(InvalidGameStateError,
                                "ONE cannot win this trick: Q♠, K♠"):
      validate(self.game_state)

    # Cannot win with non-trump card against a trump card.
    self.game_state = get_game_state_for_tests()
    self.game_state.won_tricks.one.append(self.game_state.won_tricks.two.pop())
    self.game_state.trick_points = PlayerPair(42, 33)
    with self.assertRaisesRegex(InvalidGameStateError,
                                "ONE cannot win this trick: X♦, X♣"):
      validate(self.game_state)

    # Different suits, no trump. Could be valid wins for both players, since we
    # don't know who played the first card.
    self.game_state = get_game_state_for_tests()
    card = self.game_state.won_tricks.two[-1].two
    self.game_state.won_tricks.two[-1].two = \
      self.game_state.cards_in_hand.one[3]
    self.game_state.cards_in_hand.one[3] = card
    validate(self.game_state)
    self.game_state.won_tricks.one.append(self.game_state.won_tricks.two.pop())
    self.game_state.trick_points = PlayerPair(42, 33)
    validate(self.game_state)


class GameStateValidatorTest(unittest.TestCase):
  """Tests for the GameStateValidator context manager."""

  @staticmethod
  def test_no_changes():
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      pass

  @staticmethod
  def test_valid_changes():
    game_state = get_game_state_for_tests()
    with GameStateValidator(game_state):
      game_state.next_player = game_state.next_player.opponent()

  def test_invalid_when_entering(self):
    game_state = get_game_state_for_tests()
    game_state.trick_points = PlayerPair(0, 0)
    with self.assertRaisesRegex(InvalidGameStateError, "Invalid trick points"):
      with GameStateValidator(game_state):
        pass
    with self.assertRaisesRegex(InvalidGameStateError, "Invalid trick points"):
      with GameStateValidator(game_state):
        # This would make the game_state valid.
        game_state.trick_points = PlayerPair(22, 53)

  def test_invalid_when_exiting(self):
    game_state = get_game_state_for_tests()
    with self.assertRaisesRegex(InvalidGameStateError, "Invalid trick points"):
      with GameStateValidator(game_state):
        game_state.trick_points = PlayerPair(0, 0)

  def test_valid_when_exiting_other_exception_is_raised(self):
    game_state = get_game_state_for_tests()
    with self.assertRaisesRegex(ValueError, "This should be reraised"):
      with GameStateValidator(game_state):
        game_state.next_player = game_state.next_player.opponent()
        raise ValueError("This should be reraised")

  def test_invalid_when_exiting_other_exception_is_raised(self):
    game_state = get_game_state_for_tests()
    with self.assertRaisesRegex(InvalidGameStateError, "Invalid trick points"):
      with GameStateValidator(game_state):
        game_state.trick_points = PlayerPair(0, 0)
        raise ValueError("This will be replaced by InvalidGameStateError")


class ValidateGameStatesDecoratorTest(unittest.TestCase):
  """Tests for the @validate_game_states decorator."""

  def test_function_with_valid_changes(self):
    @validate_game_states
    def func(game_state: GameState) -> int:
      game_state.next_player = game_state.next_player.opponent()
      return 42

    self.assertEqual(42, func(get_game_state_for_tests()))

  def test_function_with_invalid_changes(self):
    @validate_game_states
    def func(game_state: GameState) -> int:
      game_state.trick_points = PlayerPair(0, 0)
      return 42

    self.assertEqual(42, func(GameState.new_game(PlayerId.ONE)))
    with self.assertRaisesRegex(InvalidGameStateError, "Invalid trick points"):
      func(get_game_state_for_tests())

  def test_function_with_invalid_changes_on_multiple_game_states(self):
    @validate_game_states
    def func(unmodified_game_state: GameState,
             integer_arg: int,
             str_arg: str,
             modified_game_state: GameState) -> None:
      print(unmodified_game_state, integer_arg, str_arg)
      modified_game_state.trick_points = PlayerPair(0, 0)

    func(get_game_state_for_tests(), 100, "test",
         GameState.new_game(PlayerId.ONE))
    with self.assertRaisesRegex(InvalidGameStateError, "Invalid trick points"):
      func(GameState.new_game(PlayerId.ONE), 100, "test",
           get_game_state_for_tests())

    func(integer_arg=123, modified_game_state=GameState.new_game(PlayerId.ONE),
         str_arg="test", unmodified_game_state=get_game_state_for_tests())
    with self.assertRaisesRegex(InvalidGameStateError, "Invalid trick points"):
      func(integer_arg=123, modified_game_state=get_game_state_for_tests(),
           str_arg="test",
           unmodified_game_state=GameState.new_game(PlayerId.ONE))

  def test_decorator_has_no_effect_in_non_debug_mode(self):
    # pylint: disable=subprocess-run-check
    file_name = os.path.join(
      os.path.dirname(__file__), "game_state_validation_test_module.py")

    # Run in debug mode. It should raise InvalidGameStateError and crash.
    completed_process = subprocess.run([sys.executable, file_name],
                                       capture_output=True)
    print(str(completed_process.stdout))
    print(str(completed_process.stderr))
    self.assertNotEqual(0, completed_process.returncode, msg=completed_process)
    self.assertRegex(str(completed_process.stderr), "InvalidGameStateError")
    self.assertNotRegex(str(completed_process.stdout), "Success")

    # Run in non-debug mode. It should not raise InvalidGameStateError.
    completed_process = subprocess.run([sys.executable, "-O", file_name],
                                       capture_output=True)
    print(str(completed_process.stdout))
    print(str(completed_process.stderr))
    self.assertEqual(0, completed_process.returncode)
    self.assertRegex(str(completed_process.stdout), "Success")
