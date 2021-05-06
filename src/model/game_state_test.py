#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import copy
import dataclasses
import enum
import inspect
import pprint
import unittest
from typing import List, Tuple, Optional

from model.card import Card
from model.game_state import GameState, Trick, get_game_points
from model.game_state_test_utils import get_game_state_for_tests, \
  get_game_state_with_empty_talon_for_tests, \
  get_game_state_with_all_tricks_played
from model.game_state_validation import validate, GameStateValidator
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit


class GameStateNewGameTest(unittest.TestCase):
  def test_new_game_is_valid(self):
    game_state = GameState.new_game(dealer=PlayerId.ONE, random_seed=321)
    validate(game_state)
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
    self.assertEqual(PlayerPair(None, None), game_state.current_trick)

  def test_init_default_arguments(self):
    """
    Make sure that default arguments use factories instead of mutable instances.
    """
    fields = dataclasses.fields(GameState)
    args_with_default = [
      field.name for field in fields
      if field.default != dataclasses.MISSING
         or field.default_factory != dataclasses.MISSING]
    self.assertEqual(7, len(args_with_default))
    args_with_default_values = [
      (field.name, field.default) for field in fields
      if field.default != dataclasses.MISSING
         and field.default is not None
         and inspect.isclass(type(field.default))
         and not issubclass(type(field.default), enum.Enum)]
    self.assertEqual([], args_with_default_values)

    deck = Card.get_all_cards()
    cards_in_hand = PlayerPair(one=deck[:5], two=deck[5:10])
    trump_card = deck[10]
    init_args = {
      "cards_in_hand": cards_in_hand,
      "trump": trump_card.suit,
      "trump_card": trump_card,
      "talon": deck[11:],
    }
    # Make sure we are only passing mandatory arguments with no defaults.
    mandatory_args = [
      field.name for field in fields
      if field.default == dataclasses.MISSING
         and field.default_factory == dataclasses.MISSING]
    for arg in init_args:
      self.assertIn(arg, mandatory_args)

    game_state = GameState(**copy.deepcopy(init_args))
    expected_game_state = copy.deepcopy(game_state)

    # Modify the fields with default values.
    with GameStateValidator(game_state):
      king_hearts = game_state.cards_in_hand.one.pop(2)
      king_spades = game_state.cards_in_hand.two.pop(2)
      game_state.won_tricks.one.append(PlayerPair(king_hearts, king_spades))
      game_state.trick_points.one += 28
      game_state.marriage_suits.one.append(Suit.HEARTS)
      game_state.cards_in_hand.one.append(game_state.talon.pop(0))
      game_state.cards_in_hand.two.append(game_state.talon.pop(0))
      game_state.current_trick.one = game_state.cards_in_hand.one[0]
      game_state.next_player = game_state.next_player.opponent()

    # Create a new game state and check that the defaults did not change.
    self.assertEqual(expected_game_state, GameState(**copy.deepcopy(init_args)))

  def test_first_player_is_not_the_dealer(self):
    game_state = GameState.new_game(dealer=PlayerId.ONE, random_seed=321)
    self.assertEqual(PlayerId.TWO, game_state.next_player)
    game_state = GameState.new_game(dealer=PlayerId.TWO, random_seed=321)
    self.assertEqual(PlayerId.ONE, game_state.next_player)

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
        else:
          self.assertEqual(0.0, num[i][j])
    self.assertLess(total_diff, 0.5)


class GameStateTest(unittest.TestCase):
  def test_is_to_lead(self):
    game_state = get_game_state_for_tests()
    self.assertTrue(game_state.is_to_lead(PlayerId.ONE))
    self.assertFalse(game_state.is_to_lead(PlayerId.TWO))

    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    self.assertTrue(game_state.is_to_lead(PlayerId.TWO))
    self.assertFalse(game_state.is_to_lead(PlayerId.ONE))

    with GameStateValidator(game_state):
      game_state.current_trick.one = game_state.cards_in_hand.one[0]
    self.assertFalse(game_state.is_to_lead(PlayerId.TWO))
    self.assertFalse(game_state.is_to_lead(PlayerId.ONE))

    with GameStateValidator(game_state):
      game_state.current_trick.one = None
      game_state.current_trick.two = game_state.cards_in_hand.two[0]
      game_state.next_player = PlayerId.ONE
    self.assertFalse(game_state.is_to_lead(PlayerId.TWO))
    self.assertFalse(game_state.is_to_lead(PlayerId.ONE))

  def test_must_follow_suit(self):
    game_state = get_game_state_for_tests()
    self.assertFalse(game_state.must_follow_suit())
    game_state.close_talon()
    self.assertTrue(game_state.must_follow_suit())
    game_state = get_game_state_with_empty_talon_for_tests()
    self.assertTrue(game_state.must_follow_suit())

  def test_is_game_over_player_two_reaches_exactly_66(self):
    game_state = get_game_state_for_tests()
    self.assertFalse(game_state.is_game_over())

    with GameStateValidator(game_state):
      jack_clubs = game_state.cards_in_hand[PlayerId.TWO].pop(3)
      ace_spades = game_state.cards_in_hand[PlayerId.ONE].pop(4)
      trick = Trick(jack_clubs, ace_spades)
      game_state.won_tricks[PlayerId.TWO].append(trick)
      game_state.trick_points[PlayerId.TWO] += jack_clubs.card_value
      game_state.trick_points[PlayerId.TWO] += ace_spades.card_value
      game_state.next_player = PlayerId.TWO
      game_state.cards_in_hand[PlayerId.TWO].append(game_state.talon.pop(0))
      game_state.cards_in_hand[PlayerId.ONE].append(game_state.trump_card)
      game_state.trump_card = None

    self.assertEqual(66, game_state.trick_points[PlayerId.TWO])
    self.assertTrue(game_state.is_game_over())
    self.assertEqual(PlayerPair(0, 2), game_state.score())

  def test_is_game_over_player_one_goes_beyond_66(self):
    game_state = get_game_state_for_tests()
    self.assertFalse(game_state.is_game_over())

    with GameStateValidator(game_state):
      while len(game_state.won_tricks[PlayerId.TWO]) > 0:
        trick = game_state.won_tricks[PlayerId.TWO].pop()
        game_state.won_tricks[PlayerId.ONE].append(Trick(trick.two, trick.one))
        game_state.trick_points[PlayerId.ONE] += trick.one.card_value
        game_state.trick_points[PlayerId.ONE] += trick.two.card_value
      game_state.trick_points[PlayerId.TWO] = 0

      jack_clubs = game_state.cards_in_hand[PlayerId.TWO].pop(3)
      ace_spades = game_state.cards_in_hand[PlayerId.ONE].pop(4)
      trick = Trick(ace_spades, jack_clubs)
      game_state.won_tricks[PlayerId.ONE].append(trick)
      game_state.trick_points[PlayerId.ONE] += jack_clubs.card_value
      game_state.trick_points[PlayerId.ONE] += ace_spades.card_value
      game_state.next_player = PlayerId.TWO
      game_state.cards_in_hand[PlayerId.TWO].append(game_state.talon.pop(0))
      game_state.cards_in_hand[PlayerId.ONE].append(game_state.trump_card)
      game_state.trump_card = None

    self.assertEqual(68, game_state.trick_points[PlayerId.ONE])
    self.assertTrue(game_state.is_game_over())
    self.assertEqual(PlayerPair(3, 0), game_state.score())

  def test_is_game_over_no_more_cards_to_play_talon_is_closed(self):
    game_state = get_game_state_for_tests()

    with GameStateValidator(game_state):
      jack_clubs = game_state.cards_in_hand[PlayerId.TWO].pop(3)
      queen_hearts = game_state.cards_in_hand[PlayerId.ONE].pop(0)
      trick = Trick(jack_clubs, queen_hearts)
      game_state.won_tricks[PlayerId.TWO].append(trick)
      game_state.trick_points[PlayerId.TWO] += jack_clubs.card_value
      game_state.trick_points[PlayerId.TWO] += queen_hearts.card_value
      game_state.talon.extend(game_state.cards_in_hand.one)
      game_state.talon.extend(game_state.cards_in_hand.two)
      game_state.cards_in_hand = PlayerPair([], [])
      game_state.marriage_suits.two = []
      game_state.trick_points = PlayerPair(22, 38)
      game_state.close_talon()

    self.assertTrue(game_state.is_game_over())
    self.assertEqual(PlayerPair(0, 2), game_state.score())

  def test_is_game_over_no_more_cards_to_play(self):
    game_state = get_game_state_with_all_tricks_played()
    self.assertTrue(game_state.is_game_over())
    self.assertEqual(PlayerPair(1, 0), game_state.score())
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    self.assertEqual(PlayerPair(0, 1), game_state.score())


class GetGamePointsTest(unittest.TestCase):
  """Tests for the get_game_points() function."""

  def test_one_player_reaches_66_talon_not_closed(self):
    test_cases: List[Tuple[Tuple[PlayerPair[int], Optional[PlayerId], Optional[
      PlayerId], Optional[int]], PlayerPair[int]]] = [
      # Player.ONE wins, talon is not closed
      ((PlayerPair(66, 33), PlayerId.ONE, None, None), PlayerPair(1, 0)),
      ((PlayerPair(68, 40), PlayerId.ONE, None, None), PlayerPair(1, 0)),
      ((PlayerPair(66, 32), PlayerId.ONE, None, None), PlayerPair(2, 0)),
      ((PlayerPair(70, 12), PlayerId.ONE, None, None), PlayerPair(2, 0)),
      ((PlayerPair(66, 0), PlayerId.ONE, None, None), PlayerPair(3, 0)),
      ((PlayerPair(70, 0), PlayerId.ONE, None, None), PlayerPair(3, 0)),
      ((PlayerPair(62, 58), PlayerId.ONE, None, None), PlayerPair(1, 0)),
      ((PlayerPair(58, 62), PlayerId.ONE, None, None), PlayerPair(1, 0)),

      # Player.ONE closed the talon
      ((PlayerPair(66, 33), None, PlayerId.ONE, 33), PlayerPair(1, 0)),
      ((PlayerPair(68, 50), None, PlayerId.ONE, 40), PlayerPair(1, 0)),
      ((PlayerPair(58, 45), None, PlayerId.ONE, 40), PlayerPair(0, 2)),
      ((PlayerPair(66, 42), None, PlayerId.ONE, 32), PlayerPair(2, 0)),
      ((PlayerPair(70, 12), None, PlayerId.ONE, 12), PlayerPair(2, 0)),
      ((PlayerPair(60, 22), None, PlayerId.ONE, 12), PlayerPair(0, 2)),
      ((PlayerPair(66, 33), None, PlayerId.ONE, 0), PlayerPair(3, 0)),
      ((PlayerPair(70, 10), None, PlayerId.ONE, 0), PlayerPair(3, 0)),
      ((PlayerPair(50, 0), None, PlayerId.ONE, 0), PlayerPair(0, 3)),
    ]
    for inputs, expected_result in test_cases:
      self.assertEqual(expected_result, get_game_points(*inputs),
                       msg=f"{inputs}")
      # Swap Player.ONE with Player.TWO in the inputs and expectations
      swapped_inputs = (PlayerPair(inputs[0].two, inputs[0].one),
                        inputs[1].opponent() if inputs[1] is not None else None,
                        inputs[2].opponent() if inputs[2] is not None else None,
                        inputs[3])
      swapped_expected_result = PlayerPair(expected_result.two,
                                           expected_result.one)
      self.assertEqual(swapped_expected_result,
                       get_game_points(*swapped_inputs),
                       msg=f"{swapped_inputs}")
