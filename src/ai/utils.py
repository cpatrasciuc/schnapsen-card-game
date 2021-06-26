#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from math import comb
from typing import List, Optional, Dict

from model.card import Card
from model.suit import Suit


def card_win_probabilities(cards_in_hand: List[Card],
                           remaining_cards: List[Card],
                           opp_cards: List[Optional[Card]],
                           trump: Suit, must_follow_suit: bool) -> Dict[
  Card, float]:
  """
  For each card in hand, it computes the probability that the opponent does not
  have a card that can win against it. It does not take into account advanced
  strategies or sequencing.
  :param cards_in_hand: The cards in the player's hand.
  :param remaining_cards: The list of cards that were not played yet, excluding
  the trump card in case the talon is not empty.
  :param opp_cards: The list of opponent cards. Cards that are not public are
  None.
  :param trump: The trump suit.
  :param must_follow_suit: True if the talon is closed or empty.
  :return: A dictionary mapping each card to its winning probability.
  """
  # pylint: disable=too-many-locals
  opp_public_cards = {card for card in opp_cards if card is not None}
  opp_trumps = {card for card in opp_public_cards if card.suit == trump}
  num_opp_unknown_cards = len(opp_cards) - len(opp_public_cards)

  unseen_cards = [card for card in remaining_cards if
                  card not in opp_public_cards]
  unplayed_trumps = [card for card in remaining_cards if card.suit == trump]

  win_prob = {}
  for card_in_hand in cards_in_hand:
    # Probability that this card cannot be won by the opponent.
    unplayed_cards_same_suit = [card for card in remaining_cards if
                                card.suit == card_in_hand.suit]
    unplayed_better_cards = [card for card in unplayed_cards_same_suit if
                             card.card_value > card_in_hand.card_value]
    if not must_follow_suit and card_in_hand.suit != trump:
      unplayed_better_cards += unplayed_trumps

    if len(opp_public_cards.intersection(unplayed_better_cards)) > 0:
      win_prob[card_in_hand] = 0.0
      continue

    num_total_scenarios = comb(len(unseen_cards), num_opp_unknown_cards)

    if not must_follow_suit:
      num_winning_scenarios = comb(
        len(unseen_cards) - len(unplayed_better_cards), num_opp_unknown_cards)
    else:
      unseen_smaller_cards_same_suit = \
        [card for card in unseen_cards if
         card.card_value < card_in_hand.card_value and \
         card.suit == card_in_hand.suit]
      opp_smaller_cards_same_suit = \
        [card for card in opp_public_cards if
         card.card_value < card_in_hand.card_value and \
         card.suit == card_in_hand.suit]
      num_winning_scenarios = 0
      for i in range(len(unseen_smaller_cards_same_suit) + 1):
        if i > num_opp_unknown_cards:
          break
        smaller_cards_in_opp_hand = len(opp_smaller_cards_same_suit) + i
        # No smaller cards, so make sure the opponent doesn't have any trump.
        if smaller_cards_in_opp_hand == 0 and card_in_hand.suit != trump:
          if len(opp_trumps) > 0:
            continue
          num_better_cards = len(unplayed_better_cards) + len(unplayed_trumps)
          num_unimportant_cards = len(unseen_cards) - num_better_cards - len(
            unseen_smaller_cards_same_suit)
        else:
          num_better_cards = len(unplayed_better_cards)
          num_unimportant_cards = len(unseen_cards) - num_better_cards - len(
            unseen_smaller_cards_same_suit)
        num_winning_scenarios += comb(len(unseen_smaller_cards_same_suit),
                                      i) * comb(num_unimportant_cards,
                                                num_opp_unknown_cards - i)
    win_prob[card_in_hand] = num_winning_scenarios / num_total_scenarios
  return win_prob
