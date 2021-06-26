#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import logging
import pprint
import unittest
from typing import Any, Dict, Tuple, List

from ai.heuristic_player import HeuristicPlayer, HeuristicPlayerOptions
from ai.test_utils import card_list_from_string
from model.card import Card
from model.game_state import GameState, Trick
from model.player_action import ExchangeTrumpCardAction, PlayCardAction, \
  PlayerAction, AnnounceMarriageAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit

logging.basicConfig(level="DEBUG")


def _trick_from_string_tuple(string_tuple: Tuple[str, str]) -> Trick:
  return PlayerPair(Card.from_string(string_tuple[0]),
                    Card.from_string(string_tuple[1]))


def _game_view_from_dict(fields: Dict[str, Any]) -> GameState:
  cards_in_hand = fields["cards_in_hand"]
  fields["cards_in_hand"] = PlayerPair(card_list_from_string(cards_in_hand[0]),
                                       card_list_from_string(cards_in_hand[1]))
  trump_card = fields.get("trump_card", None)
  fields["trump_card"] = \
    Card.from_string(trump_card) if trump_card is not None else None
  fields["talon"] = card_list_from_string(fields.get("talon", []))
  won_tricks = fields.get("won_tricks", ([], []))
  fields["won_tricks"] = PlayerPair(
    [_trick_from_string_tuple(str_tuple) for str_tuple in won_tricks[0]],
    [_trick_from_string_tuple(str_tuple) for str_tuple in won_tricks[1]])
  marriage_suits = fields.get("marriage_suits", None)
  if marriage_suits is not None:
    fields["marriage_suits"] = PlayerPair(*marriage_suits)
  trick_points = fields.get("trick_points", None)
  if trick_points is not None:
    fields["trick_points"] = PlayerPair(*trick_points)
  else:
    trick_points = PlayerPair(0, 0)
    for player in PlayerId:
      if len(fields["won_tricks"][player]) > 0 and \
          fields.get("marriage_suits", None) is not None:
        for suit in fields["marriage_suits"][player]:
          trick_points[player] += 40 if suit == fields["trump"] else 20
      for trick in fields["won_tricks"][player]:
        trick_points[player] += trick.one.card_value + trick.two.card_value
    fields["trick_points"] = trick_points
  trick = fields.get("current_trick", None)
  if trick is not None:
    fields["current_trick"] = PlayerPair(
      Card.from_string(trick[0]) if trick[0] is not None else None,
      Card.from_string(trick[0]) if trick[1] is not None else None)
  game_view = GameState(**fields)
  logging.debug("HeuristicPlayerTest: Using game view: %s",
                pprint.pformat(str(game_view)))
  return game_view


def _is_valid_game_view(game_view: GameState) -> bool:
  if len(game_view.cards_in_hand.one) != len(game_view.cards_in_hand.two):
    return False
  cards_set = game_view.cards_in_hand.one + game_view.cards_in_hand.two + \
              game_view.talon + [game_view.trump_card] + \
              [trick.one for trick in game_view.won_tricks.one] + \
              [trick.two for trick in game_view.won_tricks.one] + \
              [trick.one for trick in game_view.won_tricks.two] + \
              [trick.two for trick in game_view.won_tricks.two]
  cards_set = {card for card in cards_set if card is not None}
  num_missing_cards = 20 - len(cards_set)
  hidden_cards = len([card for card in game_view.talon if card is None]) + \
                 len([card for card in game_view.cards_in_hand.two if
                      card is None])
  return num_missing_cards == hidden_cards


class HeuristicPlayerTest(unittest.TestCase):
  """Test for HeuristicPlayer with all options set to False."""

  @staticmethod
  def _get_player():
    options = HeuristicPlayerOptions(smart_discard=False, can_close_talon=False,
                                     save_marriages=False,
                                     trump_for_marriage=False,
                                     avoid_direct_loss=False,
                                     trump_control=False)
    player = HeuristicPlayer(PlayerId.ONE, options)
    return player

  def _run_test_cases(self, test_cases: List[Dict[str, Any]]) -> None:
    player = self._get_player()
    for i, test_case in enumerate(test_cases):
      expected_action = test_case["expected_action"]
      test_case.pop("expected_action")
      game_view = _game_view_from_dict(test_case)
      self.assertTrue(_is_valid_game_view(game_view),
                      msg=f"TestCase {i}: {test_case}")
      actual_action = player.request_next_action(game_view)
      if isinstance(expected_action, PlayerAction):
        self.assertEqual(expected_action, actual_action,
                         msg=f"TestCase {i}: {test_case}")
      else:
        self.assertIn(actual_action, expected_action,
                      msg=f"TestCase {i}: {test_case}")

  def test_generic_on_lead_do_not_follow_suit(self):
    self._run_test_cases([
      # Exchanges trump when possible.
      {
        "cards_in_hand": (["qd", "kc", "jc", "js", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "expected_action": ExchangeTrumpCardAction(PlayerId.ONE)
      },
      # Play a high trump card if it will secure the lead.
      {
        "cards_in_hand": (["tc", "kc", "ac", "jh", "ad"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "jc",
        "talon": [None, None, None, None, None, None, None],
        "won_tricks": ([("qc", "ah")], []),
        "marriage_suits": ([Suit.CLUBS], []),
        "expected_action": {
          PlayCardAction(PlayerId.ONE, Card.from_string("ac")),
          PlayCardAction(PlayerId.ONE, Card.from_string("tc")),
        }
      },
      # Play a high non trump card if it will secure the lead.
      {
        "cards_in_hand": (["ks", "qd", "td", "jh", "ad"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "jc",
        "talon": [None, None, None],
        "won_tricks": ([("qc", "ah"), ("kc", "jd")], [("tc", "ac")]),
        "marriage_suits": ([Suit.CLUBS], []),
        "expected_action": {
          PlayCardAction(PlayerId.ONE, Card.from_string("ad")),
          PlayCardAction(PlayerId.ONE, Card.from_string("td")),
        }
      },
      # Play a high trump card if it will secure the lead. Take into account the
      # marriage in hand.
      {
        "cards_in_hand": (["kd", "qd", "ah", "jd", "ad"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "jh",
        "talon": [None, None, None, None, None],
        "won_tricks": ([("qc", "as")], [("kc", "tc")]),
        "marriage_suits": ([Suit.CLUBS], []),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("ah"))
      },
      # Announce the marriage with queen.
      {
        "cards_in_hand": (["qd", "kc", "jc", "js", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.DIAMONDS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "expected_action": AnnounceMarriageAction(PlayerId.ONE,
                                                  Card.from_string("qc"))
      },
      # Announce the marriage with king.
      {
        "cards_in_hand": (["qd", "kc", "jc", "ac", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.DIAMONDS,
        "trump_card": "ad",
        "talon": [None, None, None, None, None, None, None],
        "won_tricks": ([("tc", "js")], []),
        "expected_action": AnnounceMarriageAction(PlayerId.ONE,
                                                  Card.from_string("kc"))
      },
      # Discard the smallest non-trump card.
      {
        "cards_in_hand": (["qh", "qd", "ac", "qs", "tc"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "ah",
        "talon": [None, None, None, None, None, None, None, None, None],
        "expected_action": {
          PlayCardAction(PlayerId.ONE, Card.from_string("qd")),
          PlayCardAction(PlayerId.ONE, Card.from_string("qs")),
        }
      },
      # Discard the smallest trump card.
      {
        "cards_in_hand": (["ts", "qs"],
                          [None, None]),
        "trump": Suit.SPADES,
        "trump_card": "ks",
        "talon": [None, None, None, None, None, None, None, None, None],
        "won_tricks": ([("qh", "qd")], [("tc", "ac"), ("jh", "jc")]),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("qs")),
      },
    ])