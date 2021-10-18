#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from typing import Dict

from ai.merge_scoring_infos_func import ScoringInfo, best_action_frequency, \
  average_ucb, count_visits, merge_ucbs_using_simple_average, \
  merge_ucbs_using_weighted_average, merge_ucbs_using_lower_ci_bound, \
  lower_ci_bound_on_raw_rewards, average_score_with_tiebreakers
from model.card import Card
from model.card_value import CardValue
from model.player_action import PlayCardAction, PlayerAction, \
  CloseTheTalonAction, AnnounceMarriageAction, ExchangeTrumpCardAction
from model.player_id import PlayerId
from model.suit import Suit


class BestActionFrequencyTest(unittest.TestCase):
  def test(self):
    actions_and_scores_list = [
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=6, n=6, score=-0.33, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=False,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=20, score=15 / 20, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=20, n=20, score=20 / 20, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=20, score=5 / 20, fully_simulated=False,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=15, score=0.66, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=12, n=20, score=12 / 20, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)):
          ScoringInfo(q=3, n=10, score=3 / 10, fully_simulated=False,
                      terminal=False),
      },
    ]
    actions_and_scores = best_action_frequency(actions_and_scores_list)
    self.assertEqual({
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)), 2),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)), 1),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)), 1),
    }, set(actions_and_scores))


class AverageUcbTest(unittest.TestCase):
  def test(self):
    actions_and_scores_list = [
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=6, n=6, score=-0.33, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=False,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=20, score=15 / 20, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=20, n=20, score=20 / 20, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=20, score=5 / 20, fully_simulated=False,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=15, score=0.66, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=12, n=20, score=12 / 20, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)):
          ScoringInfo(q=3, n=10, score=3 / 10, fully_simulated=False,
                      terminal=False),
      },
    ]
    actions_and_scores = average_ucb(actions_and_scores_list)
    self.assertEqual({
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)), 0.7478),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)), 0.4233),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)), 0.5417),
      (PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)), 0.3),
    }, {(action, round(score, 4)) for action, score in actions_and_scores})


class AverageScoreWithTiebreakersTest(unittest.TestCase):
  def test(self):
    action_1 = AnnounceMarriageAction(PlayerId.ONE,
                                      Card(Suit.SPADES, CardValue.QUEEN))
    action_2 = ExchangeTrumpCardAction(PlayerId.ONE)
    action_3 = CloseTheTalonAction(PlayerId.ONE)
    action_4 = PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING))
    actions_and_scores_list = [
      {
        action_1: ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=False,
                              terminal=False),
        action_2: ScoringInfo(q=6, n=6, score=-0.33, fully_simulated=True,
                              terminal=False),
        action_3: ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=False,
                              terminal=False),
      },
      {
        action_1: ScoringInfo(q=15, n=20, score=15 / 20, fully_simulated=False,
                              terminal=False),
        action_2: ScoringInfo(q=20, n=20, score=20 / 20, fully_simulated=False,
                              terminal=False),
        action_3: ScoringInfo(q=5, n=20, score=5 / 20, fully_simulated=False,
                              terminal=False),
      },
      {
        action_1: ScoringInfo(q=15, n=15, score=0.66, fully_simulated=True,
                              terminal=False),
        action_2: ScoringInfo(q=12, n=20, score=12 / 20, fully_simulated=False,
                              terminal=False),
        action_4: ScoringInfo(q=-3, n=10, score=-3 / 10, fully_simulated=False,
                              terminal=False),
      },
    ]
    actions_and_scores = average_score_with_tiebreakers(actions_and_scores_list)
    self.assertEqual({
      (action_1, 0.7478),
      (action_2, 0.4233),
      (action_3, 0.5417),
      (action_4, -0.3),
    }, {(action, round(score[0], 4)) for action, score in actions_and_scores})
    self.assertEqual({
      (action_1, 0.8611),
      (action_2, 0.8667),
      (action_3, 0.5417),
      (action_4, -0.3),
    }, {(action, round(score[1], 4)) for action, score in actions_and_scores})
    self.assertEqual({
      (action_1, 50),
      (action_2, 100),
      (action_3, -100),
      (action_4, -4),
    }, {(action, score[2]) for action, score in actions_and_scores})


class CountVisitsTest(unittest.TestCase):
  def test_fully_simulated_trees(self):
    actions_and_scores_list = [
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=6, n=6, score=-0.33, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=20, score=15 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=20, n=20, score=20 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=20, score=5 / 20, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=15, score=0.66, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=12, n=20, score=12 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)):
          ScoringInfo(q=3, n=10, score=3 / 10, fully_simulated=True,
                      terminal=False),
      },
    ]
    actions_and_scores = count_visits(actions_and_scores_list)
    self.assertEqual({
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)), 0.7478),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)), 0.4233),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)), 0.5417),
      (PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)), 0.3),
    }, {(action, round(score, 4)) for action, score in actions_and_scores})

  def test_not_fully_simulated_trees(self):
    actions_and_scores_list = [
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=6, n=6, score=-0.33, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=20, score=15 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=20, n=20, score=20 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=20, score=5 / 20, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=15, score=0.66, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=12, n=20, score=12 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)):
          ScoringInfo(q=3, n=10, score=3 / 10, fully_simulated=False,
                      terminal=False),
      },
    ]
    actions_and_scores = count_visits(actions_and_scores_list)
    self.assertEqual({
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)), 41),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)), 46),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)), 26),
      (PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)), 10),
    }, set(actions_and_scores))


class MergeUcbsUsingSimpleAverageTest(unittest.TestCase):
  def test_fully_simulated_trees(self):
    actions_and_scores_list = [
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=6, n=6, score=-0.33, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=20, score=15 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=20, n=20, score=20 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=20, score=5 / 20, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=15, score=0.66, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=12, n=20, score=12 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)):
          ScoringInfo(q=3, n=10, score=3 / 10, fully_simulated=True,
                      terminal=False),
      },
    ]
    actions_and_scores = merge_ucbs_using_simple_average(
      actions_and_scores_list)
    self.assertEqual({
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)), 0.7478),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)), 0.4233),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)), 0.5417),
      (PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)), 0.3),
    }, {(action, round(score, 4)) for action, score in actions_and_scores})

  def test_not_fully_simulated_trees(self):
    actions_and_scores_list = [
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=6, n=6, score=-0.33, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=20, score=15 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=20, n=20, score=20 / 20, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=20, score=5 / 20, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=15, score=0.66, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=12, n=20, score=12 / 20, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)):
          ScoringInfo(q=3, n=10, score=3 / 10, fully_simulated=False,
                      terminal=False),
      },
    ]
    actions_and_scores = merge_ucbs_using_simple_average(
      actions_and_scores_list)
    self.assertEqual({
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)), 0.7293),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)), 0.8261),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)), 0.3846),
      (PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)), 0.3),
    }, {(action, round(score, 4)) for action, score in actions_and_scores})


class MergeUcbsUsingWeightedAverageTest(unittest.TestCase):
  def test_fully_simulated_trees(self):
    actions_and_scores_list = [
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=6, n=6, score=-0.33, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=20, score=15 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=20, n=20, score=20 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=20, score=5 / 20, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=15, score=0.66, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=12, n=20, score=12 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)):
          ScoringInfo(q=3, n=10, score=3 / 10, fully_simulated=True,
                      terminal=False),
      },
    ]
    actions_and_scores = merge_ucbs_using_weighted_average(
      actions_and_scores_list)
    self.assertEqual({
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)), 0.7478),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)), 0.4233),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)), 0.5417),
      (PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)), 0.3),
    }, {(action, round(score, 4)) for action, score in actions_and_scores})

  def test_not_fully_simulated_trees(self):
    actions_and_scores_list = [
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=6, n=6, score=-0.33, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=20, score=15 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=20, n=20, score=20 / 20, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=20, score=5 / 20, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=15, score=0.66, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=12, n=20, score=12 / 20, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)):
          ScoringInfo(q=3, n=10, score=3 / 10, fully_simulated=False,
                      terminal=False),
      },
    ]
    actions_and_scores = merge_ucbs_using_weighted_average(
      actions_and_scores_list)
    self.assertEqual({
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)), 11.6707),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)), 14.6957),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)), 5),
      (PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)), 3),
    }, {(action, round(score, 4)) for action, score in actions_and_scores})


class MergeUcbsUsingLowerCiBoundTest(unittest.TestCase):
  def test_fully_simulated_trees(self):
    actions_and_scores_list = [
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=6, n=6, score=-0.33, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=20, score=15 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=20, n=20, score=20 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=20, score=5 / 20, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=15, score=0.66, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=12, n=20, score=12 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)):
          ScoringInfo(q=3, n=10, score=3 / 10, fully_simulated=True,
                      terminal=False),
      },
    ]
    actions_and_scores = merge_ucbs_using_lower_ci_bound(
      actions_and_scores_list)
    self.assertEqual({
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)), 0.7478),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)), 0.4233),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)), 0.5417),
      (PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)), 0.3),
    }, {(action, round(score, 4)) for action, score in actions_and_scores})

  def test_not_fully_simulated_trees(self):
    actions_and_scores_list = [
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=6, n=6, score=-0.33, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=20, score=15 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=20, n=20, score=20 / 20, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=20, score=5 / 20, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=15, score=0.66, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=12, n=20, score=12 / 20, fully_simulated=False,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)):
          ScoringInfo(q=3, n=10, score=3 / 10, fully_simulated=False,
                      terminal=False),
      },
    ]
    actions_and_scores = merge_ucbs_using_lower_ci_bound(
      actions_and_scores_list)
    self.assertEqual({
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)), 0.66),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)), 0.6),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)), 0.25),
      (PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)), 0.3),
    }, {(action, round(score, 4)) for action, score in actions_and_scores})


class LowerCiBoundOnRawRewardsTest(unittest.TestCase):
  def test_fully_simulated_trees(self):
    actions_and_scores_list = [
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=6, n=6, score=-0.33, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=20, score=15 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=20, n=20, score=20 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=20, score=5 / 20, fully_simulated=True,
                      terminal=False),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=15, score=0.66, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=12, n=20, score=12 / 20, fully_simulated=True,
                      terminal=False),
        PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)):
          ScoringInfo(q=3, n=10, score=3 / 10, fully_simulated=True,
                      terminal=False),
      },
    ]
    actions_and_scores = lower_ci_bound_on_raw_rewards(actions_and_scores_list)
    self.assertEqual({
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)), 0.7478),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)), 0.4233),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)), 0.5417),
      (PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)), 0.3),
    }, {(action, round(score, 4)) for action, score in actions_and_scores})

  def test_not_fully_simulated_trees(self):
    actions_and_scores_list = [
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=False,
                      terminal=False, rewards=[1, 1, 1, 1, 1, 0]),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=6, n=6, score=-0.33, fully_simulated=True,
                      terminal=False, rewards=[-0.33, 0.33, 2, 2, 2, 0]),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=6, score=5 / 6, fully_simulated=False,
                      terminal=False, rewards=[1, 1, 1, 1, 1, 0]),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=20, score=15 / 20, fully_simulated=False,
                      terminal=False,
                      rewards=[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0,
                               0, 0, 0, 0]),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=20, n=20, score=20 / 20, fully_simulated=False,
                      terminal=False,
                      rewards=[2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1,
                               -1, -1, -1, -1, -1]),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)):
          ScoringInfo(q=5, n=20, score=5 / 20, fully_simulated=False,
                      terminal=False,
                      rewards=[1, 1, 1, 1, 1, 0, -0.33, 0.33, -0.33, 0.33,
                               -0.33, 0.33, -0.33, 0.33, -0.33, 0.33, -0.33,
                               0.33, -0.33, 0.33]),
      },
      {
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)):
          ScoringInfo(q=15, n=15, score=0.66, fully_simulated=True,
                      terminal=False,
                      rewards=[0.66, 0.33, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                               1]),
        PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)):
          ScoringInfo(q=12, n=20, score=12 / 20, fully_simulated=False,
                      terminal=False,
                      rewards=[1, 1, 1, 1, 2, 0, 1, 1, 1, 2, 0, 2, -1, 0, 0, 0,
                               0, 0, 0, 0]),
        PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)):
          ScoringInfo(q=3, n=10, score=3 / 10, fully_simulated=False,
                      terminal=False,
                      rewards=[1, 1, 1, 0, 1, -1, 1, -1, 1, -1]),
      },
    ]
    for action_with_scores in actions_and_scores_list:
      for action, score in action_with_scores.items():
        self.assertEqual(score.n, len(score.rewards))
        self.assertAlmostEqual(score.q, sum(score.rewards), places=1)
        if score.fully_simulated:
          self.assertIn(score.score, score.rewards)
        else:
          self.assertEqual(score.score, sum(score.rewards) / len(score.rewards))
    actions_and_scores = lower_ci_bound_on_raw_rewards(actions_and_scores_list)
    expected_scores: Dict[PlayerAction, float] = {
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)): 0.62,
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)): 0.35,
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)): 0.16,
      PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)): -0.3,
    }
    for action, score in actions_and_scores:
      self.assertAlmostEqual(expected_scores[action], score, delta=0.05)
