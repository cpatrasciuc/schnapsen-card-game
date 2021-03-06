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
  PlayerAction, AnnounceMarriageAction, CloseTheTalonAction
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
      Card.from_string(trick[1]) if trick[1] is not None else None)
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


def _get_player(**kwargs):
  params = {
    "priority_discard": False,
    "can_close_talon": False,
    "save_marriages": False,
    "trump_for_marriage": False,
    "avoid_direct_loss": False,
    "trump_control": False
  }
  params.update(**kwargs)
  options = HeuristicPlayerOptions(**params)
  player = HeuristicPlayer(PlayerId.ONE, options)
  return player


class HeuristicPlayerTest(unittest.TestCase):
  """Test for HeuristicPlayer with all options set to False."""

  def _run_test_cases(self, test_cases: List[Dict[str, Any]]) -> None:
    player = _get_player()
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
      # Play a high trump card if it will secure the win.
      {
        "cards_in_hand": (["tc", "ks", "ac", "jh", "ad"],
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
    ])

  def test_generic_on_lead_follow_suit(self):
    self._run_test_cases([
      # Play a non-trump card with the maximum win probability.
      {
        "cards_in_hand": (["qd", "qs", "kh", "ah"], [None, None, None, "th"]),
        "trump": Suit.SPADES,
        "trump_card": "ks",
        "talon": [None, None, None, None, None, None, None, None, None],
        "won_tricks": ([("qh", "qc")], []),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("ah")),
      },
      # Play a trump card with the maximum win probability.
      {
        "cards_in_hand": (["qd", "qs", "ks", "th"], [None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "jh",
        "talon": [None, None, None, None, None, None, None, None, None],
        "won_tricks": ([("qh", "qc")], []),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("th")),
      },
      # If we have a marriage pair among the cards with the max winning
      # probability, announce it with the king.
      {
        "cards_in_hand": (["qd", "qs", "ks", "ts"], [None, None, None, None]),
        "trump": Suit.SPADES,
        "trump_card": "js",
        "talon": [None, None, None, None, None, None, None, None, None],
        "won_tricks": ([("qh", "qc")], []),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": AnnounceMarriageAction(PlayerId.ONE,
                                                  Card.from_string("ks")),
      },
      # If we don't have any chance to win the next trick and we have a
      # marriage, announce it.
      {
        "cards_in_hand": (["qd", "qs", "ks", "ts"], ["as", "ad", None, None]),
        "trump": Suit.SPADES,
        "trump_card": "js",
        "talon": [None, None, None, None, None, None, None, None, None],
        "won_tricks": ([("qh", "qc")], []),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": AnnounceMarriageAction(PlayerId.ONE,
                                                  Card.from_string("ks")),
      },
      # Discard the smallest non-trump card.
      {
        "cards_in_hand": (["ts", "qs", "th", "jd"], ["as", "ah", "ad", None]),
        "trump": Suit.SPADES,
        "trump_card": "ks",
        "talon": [None, None, None, None, None, None, None, None, None],
        "won_tricks": ([("qh", "qd")], []),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("jd")),
      },
      # Discard the smallest trump card.
      {
        "cards_in_hand": (["ts", "qs"], ["as", None]),
        "trump": Suit.SPADES,
        "trump_card": "ks",
        "talon": [None, None, None, None, None, None, None, None, None],
        "won_tricks": ([("qh", "qd")], [("tc", "ac"), ("jh", "jc")]),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("qs")),
      },
    ])

  def test_generic_not_on_lead_do_not_follow_suit(self):
    self._run_test_cases([
      # Win with the Queen, keep the Ace for the not-yet-played Ten.
      {
        "cards_in_hand": (["qd", "ad", "jc", "js", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jd"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("qd"))
      },
      # If the Ten and King are already played, win with the Ace.
      {
        "cards_in_hand": (["qd", "ad", "jc", "js", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None],
        "won_tricks": ([], [("kd", "td")]),
        "current_trick": (None, "jd"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("ad"))
      },
      # Win with the Ten, even if the King is not yet played.
      {
        "cards_in_hand": (["qd", "td", "jc", "js", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jd"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("td"))
      },
      # Don't give up the Ten even if it's the only same-suit card we have.
      {
        "cards_in_hand": (["qh", "td", "jh", "js", "qs"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "ad"),
        "expected_action": {
          PlayCardAction(PlayerId.ONE, Card.from_string("jh")),
          PlayCardAction(PlayerId.ONE, Card.from_string("js")),
        }
      },
      # Break a marriage to win a Jack (options.save_marriage is False).
      {
        "cards_in_hand": (["qd", "kd", "ad", "js", "qs"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jd"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("kd"))
      },
      # Opponent played a trump card that cannot be won; discard the smallest
      # card.
      {
        "cards_in_hand": (["qd", "kd", "ad", "js", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "tc"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("js"))
      },
      # Win a Ten with the same suit Ace.
      {
        "cards_in_hand": (["qd", "ks", "ah", "js", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "th"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("ah"))
      },
      # Win a Ten with a trump-card if we don't have the same-suit Ace, even if
      # that means breaking the marriage.
      {
        "cards_in_hand": (["qd", "ks", "kc", "js", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "th"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("kc"))
      },
      # Win a Ten with the trump Queen. Save the trump Ace for the trump Ten.
      {
        "cards_in_hand": (["qd", "jc", "qc", "js", "ac"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "tc",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "th"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("qc"))
      },
      # Win a Ten with the trump Ace if we don't have the same-suit Ace; don't
      # save the trump Ace for the trump Ten, if that means breaking the trump
      # marriage.
      {
        "cards_in_hand": (["qd", "ks", "kc", "ac", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "jc",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "th"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("ac"))
      },
      # Win a Ten with the trump Jack if we don't have the same-suit Ace; don't
      # use the highest adjacent card if that means breaking the trump marriage.
      {
        "cards_in_hand": (["qd", "ks", "kc", "jc", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "th"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("jc"))
      },
      # Win a Ten with the trump Ace. Don't save the trump Ace for the trump Ten
      # if we can exchange the trump card to get the trump marriage.
      {
        "cards_in_hand": (["qd", "jc", "qc", "jd", "ac"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "kc",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "th"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("ac"))
      },
      {
        "cards_in_hand": (["qd", "jc", "kc", "jd", "ac"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "qc",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "th"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("ac"))
      },
      # If this is the last chance to win a trick and be on-lead to exchange the
      # trump card and announce the trump marriage, use a trump regardless of
      # what the opponent played.
      {
        "cards_in_hand": (["qd", "jc", "qc", "ad", "ac"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "kc",
        "talon": [None, None, None],
        "won_tricks": ([("kd", "jd")], [("jh", "qh"), ("kh", "ah")]),
        "current_trick": (None, "js"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("ac"))
      },
      # If it's not the last chance to win a trick and be on-lead to exchange
      # the trump card and announce the trump marriage, do not use a trump yet.
      {
        "cards_in_hand": (["qd", "jc", "qc", "jd", "ac"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "kc",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "js"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("jd"))
      },
      # Trump if that gets us the win right now.
      {
        "cards_in_hand": (["qd", "jh", "qh", "jd", "ac"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "jc",
        "talon": [None, None, None, None, None],
        "won_tricks": ([("qc", "ad")], [("kc", "tc")]),
        "marriage_suits": ([Suit.CLUBS], []),
        "current_trick": (None, "js"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("ac"))
      },
      # Trump if that gets us the win after one more trick.
      {
        "cards_in_hand": (["qd", "jh", "qh", "tc", "ac"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "jc",
        "talon": [None, None, None, None, None, None, None],
        "won_tricks": ([("qc", "jd")], []),
        "marriage_suits": ([Suit.CLUBS], []),
        "current_trick": (None, "js"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("tc"))
      },
      # Discard the smallest card.
      {
        "cards_in_hand": (["qd", "jh", "qh", "tc", "ac"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "jc",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "js"),
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("jh"))
      },
    ])

  def test_generic_not_on_lead_follow_suit(self):
    self._run_test_cases([
      # Win with the Queen, keep the Ace for the not-yet-played Ten.
      {
        "cards_in_hand": (["qd", "ad", "jc", "js", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jd"),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("qd"))
      },
      # If the Ten and King are already played, win with the Ace.
      {
        "cards_in_hand": (["qd", "ad", "jc", "js", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None],
        "won_tricks": ([], [("kd", "td")]),
        "current_trick": (None, "jd"),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("ad"))
      },
      # Win with the Ten, even if the King is not yet played.
      {
        "cards_in_hand": (["qd", "td", "jc", "js", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jd"),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("td"))
      },
      # Give up the Ten if it's the only same-suit card we have and we must
      # follow suit.
      {
        "cards_in_hand": (["qh", "td", "jh", "js", "qs"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "ad"),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("td"))
      },
      # Avoid breaking the marriage to win a Jack.
      {
        "cards_in_hand": (["qd", "kd", "ad", "js", "qs"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jd"),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("ad"))
      },
      # Discard the smallest card.
      {
        "cards_in_hand": (["qd", "jh", "qh", "th", "ah"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "jc",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "js"),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("jh"))
      },
      # Use a trump-card even if that means breaking the marriage.
      {
        "cards_in_hand": (["qd", "ks", "kc", "js", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jh"),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("kc"))
      },
      # Use the trump Queen. Save the trump Ace for the trump Ten.
      {
        "cards_in_hand": (["qd", "jc", "qc", "js", "ac"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "tc",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jh"),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("qc"))
      },
      # Use the trump Ace; don't save the trump Ace for the trump Ten, if that
      # means breaking the trump marriage.
      {
        "cards_in_hand": (["qd", "ks", "kc", "ac", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "jc",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jh"),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("ac"))
      },
      # Use the trump Jack; don't use the highest adjacent card if that means
      # breaking the trump marriage.
      {
        "cards_in_hand": (["qd", "ks", "kc", "jc", "qc"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jh"),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("jc"))
      },
      # The talon is closed so we cannot exchange the trump card to get the
      # trump marriage. Use the trump Queen and save the Ace for the trump Ten.
      {
        "cards_in_hand": (["qd", "jc", "qc", "jd", "ac"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "kc",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "th"),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": PlayCardAction(PlayerId.ONE, Card.from_string("qc"))
      },
    ])


class HeuristicPlayerOptionsTest(unittest.TestCase):
  """Tests for the HeuristicPlayer options."""

  def _run_test_cases_with_option(self, option_name: str,
                                  option_values: List[Any],
                                  test_cases: List[Dict[str, Any]]) -> None:
    players = []
    for option_value in option_values:
      kwargs = {option_name: option_value}
      if option_name == "avoid_direct_loss":
        kwargs["priority_discard"] = True
      players.append(_get_player(**kwargs))
    for i, test_case in enumerate(test_cases):
      expected_actions = test_case["expected_action"]
      test_case.pop("expected_action")
      game_view = _game_view_from_dict(test_case)
      self.assertTrue(_is_valid_game_view(game_view),
                      msg=f"TestCase {i}: {test_case}")
      for player, expected_action in zip(players, expected_actions):
        actual_action = player.request_next_action(game_view)
        if isinstance(expected_action, PlayerAction):
          self.assertEqual(expected_action, actual_action,
                           msg=f"TestCase {i}: {test_case}")
        else:
          self.assertIn(actual_action, expected_action,
                        msg=f"TestCase {i}: {test_case}")

  def test_can_close_talon(self):
    self._run_test_cases_with_option("can_close_talon", [False, True], [
      # The talon is already closed. Discard the smallest trump card.
      {
        "cards_in_hand": (["ts", "qs"], ["as", None]),
        "trump": Suit.SPADES,
        "trump_card": "ks",
        "talon": [None, None, None, None, None, None, None, None, None],
        "won_tricks": ([("qh", "qd")], [("tc", "ac"), ("jh", "jc")]),
        "player_that_closed_the_talon": PlayerId.ONE,
        "opponent_points_when_talon_was_closed": 0,
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("qs")),
          PlayCardAction(PlayerId.ONE, Card.from_string("qs")),
        ]
      },
      # There is a high chance the opponent has a Heart or a Club.
      {
        "cards_in_hand": (["qh", "ah", "ad", "kc", "kd"],
                          [None, None, None, None, None]),
        "trump": Suit.SPADES,
        "trump_card": "as",
        "talon": [None],
        "won_tricks": ([("qs", "ac"), ("ks", "jd")],
                       [("tc", "js"), ("jh", "jc")]),
        "marriage_suits": ([Suit.SPADES], []),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("qh")),
          CloseTheTalonAction(PlayerId.ONE),
        ]
      },
      # There is a small chance to win if we close the talon.
      {
        "cards_in_hand": (["qh", "qd", "ac", "ks", "tc"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "ah",
        "talon": [None, None, None, None, None, None, None, None, None],
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("qd")),
          PlayCardAction(PlayerId.ONE, Card.from_string("qd")),
        ]
      },
      # Make sure the player computes the winning probabilities as if suits must
      # be followed.
      {
        "cards_in_hand": (["qc", "ts", "ah", "as", "ad"],
                          [None, None, None, None, None]),
        "trump": Suit.SPADES,
        "trump_card": "js",
        "talon": [None, None, None],
        "won_tricks": ([("td", "kd"), ("qd", "jc")], [("jh", "kh")]),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("qc")),
          CloseTheTalonAction(PlayerId.ONE),
        ]
      },
    ])

  def test_save_marriages(self):
    self._run_test_cases_with_option("save_marriages", [False, True], [
      # Do not break a marriage to win a Jack.
      {
        "cards_in_hand": (["qd", "kd", "ad", "js", "qs"],
                          [None, None, None, None, None]),
        "trump": Suit.CLUBS,
        "trump_card": "ac",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jd"),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("kd")),
          PlayCardAction(PlayerId.ONE, Card.from_string("js")),
        ]
      },
    ])

  def test_priority_discard(self):
    self._run_test_cases_with_option("priority_discard", [False, True], [
      # Discard a card from an exhausted suit.
      {
        "cards_in_hand": (["jd", "qd", "ac", "ks", "tc"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "ah",
        "talon": [None, None, None, None, None],
        "won_tricks": ([("qs", "js")], [("ts", "as")]),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("jd")),
          PlayCardAction(PlayerId.ONE, Card.from_string("ks")),
        ]
      },
      # Discard a jack with ten protection.
      {
        "cards_in_hand": (["jd", "jc", "td", "ac", "tc"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "ah",
        "talon": [None, None, None, None, None, None, None, None, None],
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("jd")),
          PlayCardAction(PlayerId.ONE, Card.from_string("jc")),
        ]
      },
      # Discard a jack with no ten protection.
      {
        "cards_in_hand": (["ks", "jd", "td", "ac", "tc"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "ah",
        "talon": [None, None, None, None, None],
        "won_tricks": ([("qs", "js")], [("ts", "th")]),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("jd")),
          PlayCardAction(PlayerId.ONE, Card.from_string("jd")),
        ]
      },
      # Discard a Queen/King without marriage chances.
      {
        "cards_in_hand": (["ks", "qd", "td", "ac", "tc"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "ah",
        "talon": [None, None, None, None, None],
        "won_tricks": ([("qs", "js")], [("ts", "th")]),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("qd")),
          PlayCardAction(PlayerId.ONE, Card.from_string("ks")),
        ]
      },
      # Discard a Queen/King with marriage chances.
      {
        "cards_in_hand": (["ks", "qs", "kd", "ac", "tc"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "ah",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "th"),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("qs")),
          PlayCardAction(PlayerId.ONE, Card.from_string("kd")),
        ]
      },
      # Discard a Queen/King for a marriage.
      {
        "cards_in_hand": (["ks", "qs", "ad", "ac", "tc"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "ah",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "th"),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("qs")),
          PlayCardAction(PlayerId.ONE, Card.from_string("qs")),
        ]
      },
      # Discard a non-trump card.
      {
        "cards_in_hand": (["jh", "qh", "th", "ac", "ad"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "ah",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "ks"),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("ad")),
          PlayCardAction(PlayerId.ONE, Card.from_string("ad")),
        ]
      },
    ])

  def test_trump_for_marriage(self):
    self._run_test_cases_with_option("trump_for_marriage", [False, True], [
      # Trump to take the lead and announce a non-trump marriage.
      {
        "cards_in_hand": (["ks", "qs", "th", "ac", "tc"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "ah",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jd"),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("qs")),
          PlayCardAction(PlayerId.ONE, Card.from_string("th")),
        ]
      },
      # We have the trump marriage, but we cannot trump since we don't have a
      # third trump card to use.
      {
        "cards_in_hand": (["kh", "qh", "ts", "ac", "tc"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "ah",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jd"),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("ts")),
          PlayCardAction(PlayerId.ONE, Card.from_string("ts")),
        ]
      },
      # Use trump Ace to take the lead and announce the trump marriage.
      {
        "cards_in_hand": (["kh", "qh", "ts", "ac", "ah"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "th",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "jd"),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("ts")),
          PlayCardAction(PlayerId.ONE, Card.from_string("ah")),
        ]
      },
    ])

  def test_avoid_direct_loss(self):
    self._run_test_cases_with_option("avoid_direct_loss", [False, True], [
      # Play a trump card instead of discarding the smallest non trump card.
      {
        "cards_in_hand": (["jh", "td", "th", "kh", "ad"],
                          [None, None, None, None, None]),
        "trump": Suit.HEARTS,
        "trump_card": "ah",
        "talon": [None],
        "won_tricks": ([],
                       [("kd", "tc"), ("js", "qs"), ("ts", "as"),
                        ("jc", "ac")]),
        "current_trick": (None, "qc"),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("td")),
          PlayCardAction(PlayerId.ONE, Card.from_string("jh")),
        ]
      },
      # Play the smallest card instead of discarding a card from an exhausted
      # suit.
      {
        "cards_in_hand": (["jh", "td", "th", "tc", "ad"],
                          [None, None, None, None, None]),
        "trump": Suit.SPADES,
        "trump_card": "as",
        "talon": [None],
        "won_tricks": ([],
                       [("jc", "qc"), ("kc", "ts"), ("ac", "js"),
                        ("jd", "kh")]),
        "marriage_suits": ([], [Suit.HEARTS]),
        "current_trick": (None, "ks"),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("tc")),
          PlayCardAction(PlayerId.ONE, Card.from_string("jh")),
        ]
      },
      # There is no direct loss; discard a small card.
      {
        "cards_in_hand": (["jh", "td", "ts", "tc", "ad"],
                          [None, None, None, None, None]),
        "trump": Suit.SPADES,
        "trump_card": "as",
        "talon": [None, None, None, None, None, None, None, None, None],
        "current_trick": (None, "kh"),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("jh")),
          PlayCardAction(PlayerId.ONE, Card.from_string("jh")),
        ]
      },
    ])

  def test_trump_control(self):
    self._run_test_cases_with_option("trump_control", [False, True], [
      # No trumps after one trick. Play a high card.
      {
        "cards_in_hand": (["jh", "jd", "th", "kc", "qd"],
                          [None, None, None, None, None]),
        "trump": Suit.SPADES,
        "trump_card": "as",
        "talon": [None, None, None, None, None, None, None],
        "won_tricks": ([("qc", "jc")], []),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("jh")),
          PlayCardAction(PlayerId.ONE, Card.from_string("th")),
        ]
      },
      # There is no need to trump control; discard a small card.
      {
        "cards_in_hand": (["jh", "ts", "ks", "tc", "ad"],
                          [None, None, None, None, None]),
        "trump": Suit.SPADES,
        "trump_card": "as",
        "talon": [None, None, None, None, None, None, None, None, None],
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("jh")),
          PlayCardAction(PlayerId.ONE, Card.from_string("jh")),
        ]
      },
      # The opponent has more trumps than us, but we cannot play a high card
      # since the opponent might trump it and win the game.
      {
        "cards_in_hand": (["qh", "td", "th", "tc", "ah"],
                          ["qs", None, None, None, None]),
        "trump": Suit.SPADES,
        "trump_card": "js",
        "talon": [None, None, None, None, None],
        "won_tricks": ([],
                       [("ad", "ks"), ("qc", "qd")]),
        "marriage_suits": ([], [Suit.SPADES]),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("qh")),
          PlayCardAction(PlayerId.ONE, Card.from_string("qh")),
        ]
      },
      # No trump control since there are no more trumps.
      {
        "cards_in_hand": (["qh", "td", "th", "ts", "as"],
                          [None, None, None, None, None]),
        "trump": Suit.SPADES,
        "trump_card": "js",
        "talon": [None, None, None, None, None],
        "won_tricks": ([("ks", "ad"), ("qs", "qd")],
                       []),
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("qh")),
          PlayCardAction(PlayerId.ONE, Card.from_string("qh")),
        ]
      },
      # No trump control since we have no high cards.
      {
        "cards_in_hand": (["qh", "jd", "jh", "ks", "jc"],
                          [None, None, None, None, None]),
        "trump": Suit.SPADES,
        "trump_card": "js",
        "talon": [None, None, None, None, None, None, None, None, None],
        "expected_action": [
          PlayCardAction(PlayerId.ONE, Card.from_string("jh")),
          PlayCardAction(PlayerId.ONE, Card.from_string("jh")),
        ]
      },
    ])
