#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import copy
import random
from math import comb
from typing import List, Optional, Dict

from model.card import Card
from model.game_state import GameState
from model.player_action import PlayerAction, AnnounceMarriageAction
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
  :param opp_cards: Opponent's cards. Cards that are not public are None.
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
          # TODO(ai): Here we could take into account that we might pull all
          #   trumps from the opponent's hand with our high trumps.
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


def prob_opp_has_more_trumps(my_cards: List[Card],
                             opp_cards: List[Optional[Card]],
                             remaining_cards: List[Card],
                             trump: Suit,
                             is_forth_trick_with_opened_talon: bool):
  """
  Returns the probability that the opponent has more trump cards than the
  current player.
  :param my_cards: The cards in the current player's hand.
  :param opp_cards: The cards in the opponent's hand. The cards that are not
  public should be None.
  :param remaining_cards: Cards that are not yet played, excluding the trump
  card, in case the talon is not empty.
  :param trump: The trump suit.
  :param is_forth_trick_with_opened_talon: This must be true if we should assume
  we are before the fifth trick, the talon is not closed and the current player
  wins the fifth trick. In this case the opponent will pick up the trump card.
  :return: The probability that the opponent has more trump cards.
  """
  num_my_trumps = len([card for card in my_cards if card.suit == trump])
  num_opp_trumps = len([card for card in opp_cards if
                        card is not None and card.suit == trump])

  num_remaining_trumps = len(
    [card for card in remaining_cards if card.suit == trump]) - num_opp_trumps

  num_opp_unknown_cards = len([card for card in opp_cards if card is None])

  # Assume the opponent will get the trump card after this trick.
  if is_forth_trick_with_opened_talon:
    num_opp_trumps += 1
    num_opp_unknown_cards -= 1

  num_remaining_cards = len(remaining_cards)
  num_remaining_cards -= len([card for card in opp_cards if card is not None])

  total_scenarios = comb(num_remaining_cards, num_opp_unknown_cards)
  probabilities = []
  for i in range(num_remaining_trumps + 1):
    possible_opp_trumps = num_opp_trumps + i
    if possible_opp_trumps <= num_my_trumps:
      continue
    if num_opp_unknown_cards < i:
      break
    possibilities = comb(num_remaining_trumps, i) * comb(
      num_remaining_cards - num_remaining_trumps, num_opp_unknown_cards - i)
    probabilities.append(possibilities / total_scenarios)
  return sum(probabilities)


def get_best_marriage(available_actions: List[PlayerAction],
                      trump: Suit) -> Optional[AnnounceMarriageAction]:
  """
  Searches through the list of available_actions for AnnounceMarriageActions. If
  there is no such action, it returns None. If there is an action that announces
  the trump marriage, it will return it (either with Queen or with King,
  randomly). If there are one or more actions that announce non-trump marriages
  and there is no trump marriage, it will return randomly an action that
  announces a non-trump marriage.
  """
  marriages = []
  has_trump_marriage = False
  for action in available_actions:
    if isinstance(action, AnnounceMarriageAction):
      if action.card.suit == trump and not has_trump_marriage:
        marriages = [action]
        has_trump_marriage = True
      elif action.card.suit == trump or not has_trump_marriage:
        marriages.append(action)
  if len(marriages) > 0:
    return random.choice(marriages)
  return None


def get_unseen_cards(game_view: GameState) -> List[Card]:
  """
  Returns the sorted list of cards that were not yet seen by the player
  corresponding to the given game view.
  """
  cards_set = game_view.cards_in_hand.one + game_view.cards_in_hand.two + \
              game_view.talon + [game_view.trump_card] + \
              [game_view.current_trick.one, game_view.current_trick.two] + \
              [trick.one for trick in game_view.won_tricks.one] + \
              [trick.two for trick in game_view.won_tricks.one] + \
              [trick.one for trick in game_view.won_tricks.two] + \
              [trick.two for trick in game_view.won_tricks.two]
  cards_set = {card for card in Card.get_all_cards() if card not in cards_set}
  cards_set = list(sorted(cards_set))
  return cards_set


def populate_game_view(game_view: GameState,
                       permutation: List[Card]) -> GameState:
  """
  Fill in the unknown cards in the opponent's hand and in the talon, in order,
  with the cards from permutation. Returns the resulting perfect information
  GameState.
  """
  game_state = copy.deepcopy(game_view)
  if None in game_view.cards_in_hand.one:
    opp_cards = game_state.cards_in_hand.one
    assert None not in game_state.cards_in_hand.two, \
      ("Cards missing in both hands", game_view)
  else:
    opp_cards = game_state.cards_in_hand.two
  for i, opp_card in enumerate(opp_cards):
    if opp_card is None:
      opp_cards[i] = permutation.pop(0)
  for i, talon_card in enumerate(game_state.talon):
    if talon_card is None:
      game_state.talon[i] = permutation.pop(0)
  assert len(permutation) == 0, ("Too many cards in permutation", permutation)
  return game_state
