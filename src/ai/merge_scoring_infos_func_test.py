#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from ai.merge_scoring_infos_func import ScoringInfo, best_action_frequency
from model.card import Card
from model.card_value import CardValue
from model.player_action import PlayCardAction
from model.player_id import PlayerId
from model.suit import Suit


class BestActionFrequencyTestCase(unittest.TestCase):
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
