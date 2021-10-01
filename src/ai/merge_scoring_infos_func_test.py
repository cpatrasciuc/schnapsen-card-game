#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from ai.merge_scoring_infos_func import ScoringInfo, best_action_frequency, \
  average_ucb, count_visits, merge_ucbs_using_simple_average, \
  merge_ucbs_using_weighted_average
from model.card import Card
from model.card_value import CardValue
from model.player_action import PlayCardAction
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
    actions_and_scores = merge_ucbs_using_simple_average(
      actions_and_scores_list)
    self.assertEqual({
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)), 0.8537),
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
    actions_and_scores = merge_ucbs_using_weighted_average(
      actions_and_scores_list)
    self.assertEqual({
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)), 13.5366),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)), 14.6957),
      (PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING)), 5),
      (PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)), 3),
    }, {(action, round(score, 4)) for action, score in actions_and_scores})
