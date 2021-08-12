#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import itertools
import unittest
from typing import List

from ai.test_utils import card_list_from_string
from ai.utils import card_win_probabilities, prob_opp_has_more_trumps, \
  get_best_marriage, get_unseen_cards, populate_game_view
from model.card import Card
from model.card_value import CardValue
from model.game_state_test_utils import get_game_state_for_tests
from model.player_action import PlayCardAction, AnnounceMarriageAction
from model.player_id import PlayerId
from model.suit import Suit


class CardWinProbabilitiesTest(unittest.TestCase):
  def test_default(self):
    test_cases = [
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        [None, None, None, None, None],
        Suit.CLUBS,
        False,
        [0, 0, 0, 0, 0]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        ["js", None, None, None, None],
        Suit.SPADES,
        False,
        [0, 0, 0, 1, 1]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        [None, None, None, None, None],
        Suit.SPADES,
        False,
        # The only case when the hearts are winning is when the only remaining
        # trump, the jack of spades, is not in the opponent's hand.
        [1 / 6, 1 / 6, 1 / 6, 1, 1]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        [None, None, None, None, None],
        Suit.HEARTS,
        False,
        [1, 1, 1, 1, 1]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        [None, None, None, None, None],
        Suit.CLUBS,
        True,
        [0, 0, 0, 5 / 6, 5 / 6]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        ["qd", "kc", "jc", "qc", "jd"],
        Suit.CLUBS,
        True,
        [0, 0, 0, 0, 0]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        ["qd", "kc", "js", "qc", None],
        Suit.CLUBS,
        True,
        [0, 0, 0, 1, 1]
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        ["qd", "kc", "jc", "qc", None],
        Suit.CLUBS,
        True,
        [0, 0, 0, 0.5, 0.5]
      ),
    ]
    for num_test_case, test_case in enumerate(test_cases):
      cards_in_hand = card_list_from_string(test_case[0])
      remaining_cards = card_list_from_string(test_case[1])
      opp_cards = card_list_from_string(test_case[2])
      trump = test_case[3]
      must_follow_suit = test_case[4]
      expected_probabilities: List[float] = test_case[5]
      actual_probabilities = card_win_probabilities(cards_in_hand,
                                                    remaining_cards, opp_cards,
                                                    trump, must_follow_suit)
      for i, card in enumerate(cards_in_hand):
        self.assertAlmostEqual(expected_probabilities[i],
                               actual_probabilities[card],
                               msg=f"TestCase {num_test_case}, Card: {card}",
                               places=2)


# Reference table for probabilities in this test:
# http://schnapsenstrategy.blogspot.com/2010/10/probabilities.html
class OpponentTrumpProbabilitiesTest(unittest.TestCase):
  def test_default(self):
    test_cases = [
      (
        ["qh", "kh", "th", "ts", "as"],
        [None, None, None, None, None],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        Suit.CLUBS,
        False,
        1.0
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        [None, None, None, None, None],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        Suit.CLUBS,
        True,
        1.0
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        [None, None, None, None, None],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        Suit.HEARTS,
        False,
        0.0
      ),
      (
        ["qh", "kh", "th", "ts", "as"],
        [None, None, None, None, None],
        ["qd", "kc", "jc", "js", "qc", "jd"],
        Suit.HEARTS,
        True,
        0.0
      ),
      (
        ["ts", "qc", "tc", "td", "ad"],
        [None, None, None, None, None],
        ["jh", "qh", "kh", "th", "ah", "qs", "ks", "as", "jc", "kc", "ac", "jd",
         "qd", "kd"],
        Suit.SPADES,
        False,
        0.27
      ),
      (
        ["ts", "qc", "tc", "td", "ad"],
        ["th", None, None, None, None],
        ["jh", "qh", "kh", "th", "ah", "qs", "ks", "as", "jc", "kc", "ac", "jd",
         "qd", "kd"],
        Suit.SPADES,
        False,
        0.20
      ),
      (
        ["ts", "qc", "tc", "td", "ad"],
        ["qs", None, None, None, None],
        ["qs", "as", "jc", "kc", "ac", "jd"],
        Suit.SPADES,
        False,
        4 / 5
      ),
      (
        ["ts", "qc", "tc", "td", "ad"],
        [None, None, None, None, None],
        ["js", "qh", "kh", "th", "ah", "qs", "ks", "as", "jc", "kc", "ac", "jd",
         "qd", "kd"],
        Suit.HEARTS,
        False,
        0.87
      ),
      (
        ["ts", "qc", "tc", "td", "ad"],
        [None, None, None, None, None],
        ["js", "qh", "kh", "th", "ah", "qs", "ks", "as", "jc", "kc", "ac",
         "jd"],
        Suit.HEARTS,
        False,
        1 - 0.071
      ),
      (
        ["ts", "qc", "tc", "td", "ad"],
        [None, None, None, None, None],
        ["js", "qh", "th", "ah", "qs", "ks", "as", "jc", "kc", "ac", "qd",
         "jd"],
        Suit.HEARTS,
        False,
        1 - 0.159
      ),
      (
        ["ts", "qc", "tc", "td", "ad"],
        [None, None, None, None, None],
        ["js", "qh", "kh", "th", "ah", "qs", "ks", "as", "kc", "ac", "jh", "qd",
         "kd"],
        Suit.CLUBS,
        False,
        0.0
      ),
      (
        ["ts", "qc", "tc"],
        [None, None, None],
        [],
        Suit.DIAMONDS,
        False,
        0.0
      ),
      (
        ["ts", "qc", "tc"],
        ["qd", None, None],
        ["qh", "kh", "qd"],
        Suit.DIAMONDS,
        False,
        1.0
      ),
      (
        ["ts", "qc", "tc"],
        ["jh", "qh", "kh"],
        ["jh", "qh", "kh", "ad"],
        Suit.DIAMONDS,
        False,
        0.0
      ),
    ]
    for num_test_case, test_case in enumerate(test_cases):
      cards_in_hand = card_list_from_string(test_case[0])
      opp_cards = card_list_from_string(test_case[1])
      remaining_cards = card_list_from_string(test_case[2])
      trump = test_case[3]
      is_forth_trick_with_opened_talon = test_case[4]
      expected_probability: float = test_case[5]
      actual_probability = prob_opp_has_more_trumps(
        cards_in_hand, opp_cards, remaining_cards, trump,
        is_forth_trick_with_opened_talon)
      self.assertAlmostEqual(expected_probability, actual_probability,
                             msg=f"TestCase {num_test_case}", places=2)


class GetBestMarriageTest(unittest.TestCase):
  def test_trump_marriage_is_preferred(self):
    self.assertIn(get_best_marriage(
      [
        PlayCardAction(PlayerId.ONE, Card.from_string("jh")),
        PlayCardAction(PlayerId.ONE, Card.from_string("ad")),
        PlayCardAction(PlayerId.ONE, Card.from_string("js")),
        PlayCardAction(PlayerId.ONE, Card.from_string("ts")),
        PlayCardAction(PlayerId.ONE, Card.from_string("qc")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("kh")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("qh")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("ks")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("qs")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("kc")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("qc")),
      ], Suit.SPADES),
      {
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("ks")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("qs")),
      })

  def test_non_trump_marriages_are_preferred_randomly(self):
    self.assertIn(get_best_marriage(
      [
        PlayCardAction(PlayerId.ONE, Card.from_string("jh")),
        PlayCardAction(PlayerId.ONE, Card.from_string("ad")),
        PlayCardAction(PlayerId.ONE, Card.from_string("js")),
        PlayCardAction(PlayerId.ONE, Card.from_string("ts")),
        PlayCardAction(PlayerId.ONE, Card.from_string("qc")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("kh")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("qh")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("ks")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("qs")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("kc")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("qc")),
      ], Suit.DIAMONDS),
      {
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("kh")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("qh")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("ks")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("qs")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("kc")),
        AnnounceMarriageAction(PlayerId.ONE, Card.from_string("qc")),
      })

  def test_no_marriage_available(self):
    self.assertIsNone(get_best_marriage(
      [
        PlayCardAction(PlayerId.ONE, Card.from_string("jh")),
        PlayCardAction(PlayerId.ONE, Card.from_string("ad")),
        PlayCardAction(PlayerId.ONE, Card.from_string("js")),
        PlayCardAction(PlayerId.ONE, Card.from_string("ts")),
        PlayCardAction(PlayerId.ONE, Card.from_string("qc")),
      ], Suit.SPADES))


class GetUnseenCardsTest(unittest.TestCase):
  def test_game_view(self):
    game_state = get_game_state_for_tests()
    game_view = game_state.next_player_view()
    unseen_cards = get_unseen_cards(game_view)
    self.assertEqual([Card(Suit.SPADES, CardValue.JACK),
                      Card(Suit.DIAMONDS, CardValue.JACK),
                      Card(Suit.CLUBS, CardValue.JACK),
                      Card(Suit.CLUBS, CardValue.QUEEN),
                      Card(Suit.CLUBS, CardValue.KING)],
                     unseen_cards)

  def test_game_state(self):
    self.assertEqual([], get_unseen_cards(get_game_state_for_tests()))


class PopulateGameViewTest(unittest.TestCase):
  def test_game_view(self):
    game_state = get_game_state_for_tests()
    game_view = game_state.next_player_view()
    permutation = [Card(Suit.SPADES, CardValue.JACK),
                   Card(Suit.DIAMONDS, CardValue.JACK),
                   Card(Suit.CLUBS, CardValue.JACK),
                   Card(Suit.CLUBS, CardValue.QUEEN),
                   Card(Suit.CLUBS, CardValue.KING)]
    new_game_state = populate_game_view(game_view, permutation)
    self.assertEqual([Card(Suit.DIAMONDS, CardValue.QUEEN),
                      Card(Suit.SPADES, CardValue.JACK),
                      Card(Suit.DIAMONDS, CardValue.JACK),
                      Card(Suit.CLUBS, CardValue.JACK),
                      Card(Suit.CLUBS, CardValue.QUEEN)],
                     new_game_state.cards_in_hand[PlayerId.TWO])
    self.assertEqual([Card(Suit.CLUBS, CardValue.KING)], new_game_state.talon)
    self.assertNotEqual(game_state, new_game_state)

  def test_generate_all_permutations(self):
    game_state = get_game_state_for_tests()
    game_view = game_state.next_player_view()
    unseen_cards = get_unseen_cards(game_view)
    all_game_states = [populate_game_view(game_view, list(permutation)) for
                       permutation in itertools.permutations(unseen_cards)]
    all_game_states = set(all_game_states)
    self.assertEqual(120,  # factorial(5)
                     len(all_game_states))
    self.assertIn(game_state, all_game_states)

  def test_game_state(self):
    game_state = get_game_state_for_tests()
    new_game_state = populate_game_view(game_state, [])
    self.assertEqual(game_state, new_game_state)

  def test_cards_missing_in_both_hands(self):
    game_state = get_game_state_for_tests()
    game_view = game_state.next_player_view()
    game_view.cards_in_hand[PlayerId.ONE][0] = None
    unseen_cards = get_unseen_cards(game_view)
    with self.assertRaisesRegex(AssertionError, "Cards missing in both hands"):
      populate_game_view(game_view, unseen_cards)

  def test_too_many_cards_in_permutation(self):
    game_state = get_game_state_for_tests()
    game_view = game_state.next_player_view()
    permutation = [Card(Suit.SPADES, CardValue.JACK),
                   Card(Suit.DIAMONDS, CardValue.JACK),
                   Card(Suit.CLUBS, CardValue.JACK),
                   Card(Suit.CLUBS, CardValue.QUEEN),
                   Card(Suit.CLUBS, CardValue.KING),
                   Card(Suit.DIAMONDS, CardValue.QUEEN)]
    with self.assertRaisesRegex(AssertionError,
                                "Too many cards in permutation"):
      populate_game_view(game_view, permutation)
