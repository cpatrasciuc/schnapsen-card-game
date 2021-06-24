#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.
import pprint
import random
from math import comb
from typing import List, Optional

from ai.random_player import RandomPlayer
from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState
from model.player_action import PlayerAction, PlayCardAction, \
  ExchangeTrumpCardAction, AnnounceMarriageAction, CloseTheTalonAction
from model.player_id import PlayerId
from model.suit import Suit


def _get_played_cards(game_view: GameState) -> List[Card]:
  result = []
  result += [card for trick in game_view.won_tricks.one for card in
             [trick.one, trick.two]]
  result += [card for trick in game_view.won_tricks.two for card in
             [trick.one, trick.two]]
  return result


def _highest_adjacent_card_in_hand(card: Card, cards_in_hand: List[Card],
                                   played_cards: List[Card]) -> Card:
  card_values = list(CardValue)
  index = card_values.index(card.card_value)
  adjacent_cards = [card]
  while index < len(card_values) - 1:
    next_card = Card(card.suit, card_value=card_values[index + 1])
    if next_card in cards_in_hand:
      adjacent_cards.append(next_card)
    elif next_card not in played_cards:
      break
    index += 1
  return adjacent_cards[-1]


def _key_by_value_and_suit(card: Card):
  return card.card_value, card.suit


def _get_winning_prob(cards_in_hand: List[Card],
                      remaining_cards: List[Card],
                      opp_cards: List[Optional[Card]],
                      trump: Suit, must_follow_suit: bool):
  opp_public_cards = set([c for c in opp_cards if c is not None])
  opp_trumps = set([c for c in opp_public_cards if c.suit == trump])
  num_opp_unknown_cards = len(opp_cards) - len(opp_public_cards)

  unseen_cards = [c for c in remaining_cards if c not in opp_public_cards]
  unplayed_trumps = [card for card in remaining_cards if card.suit == trump]

  winning_prob = {}
  for card in cards_in_hand:
    # Probability that this card cannot be won by the opponent.
    unplayed_cards_same_suit = [c for c in remaining_cards if
                                c.suit == card.suit]
    unplayed_better_cards = [c for c in unplayed_cards_same_suit if
                             c.card_value > card.card_value]
    if not must_follow_suit and card.suit != trump:
      unplayed_better_cards += unplayed_trumps

    if len(opp_public_cards.intersection(unplayed_better_cards)) > 0:
      winning_prob[card] = 0.0
      continue

    num_total_scenarios = comb(len(unseen_cards), num_opp_unknown_cards)

    if not must_follow_suit:
      num_winning_scenarios = comb(
        len(unseen_cards) - len(unplayed_better_cards), num_opp_unknown_cards)
    else:
      unseen_smaller_cards_same_suit = [c for c in unseen_cards if
                                        c.card_value < card.card_value and \
                                        c.suit == card.suit]
      opp_smaller_cards_same_suit = [c for c in opp_public_cards if
                                     c.card_value < card.card_value and \
                                     c.suit == card.suit]
      num_winning_scenarios = 0
      for i in range(len(unseen_smaller_cards_same_suit) + 1):
        if i > num_opp_unknown_cards:
          break
        smaller_cards_in_opp_hand = len(opp_smaller_cards_same_suit) + i
        # No smaller cards, so make sure the opponent doesn't have any trump.
        if smaller_cards_in_opp_hand == 0 and card.suit != trump:
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
                                      i) * comb(
          num_unimportant_cards, num_opp_unknown_cards - i)
    winning_prob[card] = num_winning_scenarios / num_total_scenarios
  return winning_prob


if __name__ == "__main__":
  cards = Card.get_all_cards()
  d = {str(card): card for card in cards}
  cards_in_hand = [d[card] for card in ['J♥', 'Q♦', 'X♥', 'A♣', 'J♣']]
  remaining_cards = [d[card] for card in
                     ['K♦', 'Q♣', 'X♦', 'J♠', 'Q♥', 'A♠', 'K♠', 'A♥', 'J♦',
                      'A♦', 'K♣', 'X♣', 'K♥', 'Q♠']]
  pprint.pprint(_get_winning_prob(
    cards_in_hand,
    remaining_cards, [None, None, None, None, None],
    Suit.SPADES, False))


# TODO(heuristic): Save 33 points.
# TODO(ai): Replace RandomPLayer with Player when the implementation in ready.
class HeuristicPlayer(RandomPlayer):
  """http://psellos.com/schnapsen/strategy.html"""

  def __init__(self, player_id: PlayerId, can_close_talon=False,
               smart_discard: bool = True, save_marriages=False,
               trump_for_marriage=False, avoid_direct_loss=False,
               trump_control=False, improve_trumping=False):
    super().__init__(player_id=player_id, force_trump_exchange=True,
                     never_close_talon=True, force_marriage_announcement=True)
    self._smart_discard = smart_discard
    self._can_close_talon = can_close_talon
    self._save_marriages = save_marriages
    self._trump_for_marriage = trump_for_marriage
    self._avoid_direct_loss = avoid_direct_loss
    self._trump_control = trump_control
    self._improve_trumping = improve_trumping
    self._marriage_suit = None
    self._remaining_cards = None
    self._my_cards = None
    self._my_trump_cards = None
    self._played_cards = None

  def _cache_card_lists(self, game_view: GameState) -> None:
    self._my_cards = game_view.cards_in_hand[self.id]
    self._my_trump_cards = [card for card in self._my_cards if
                            card.suit == game_view.trump]
    self._my_trump_cards.sort(key=_key_by_value_and_suit)
    self._played_cards = _get_played_cards(game_view)
    self._remaining_cards = self._get_remaining_cards(game_view)
    self._remaining_cards.sort(key=_key_by_value_and_suit)

  def request_next_action(self, game_view: GameState) -> PlayerAction:
    assert game_view.next_player == self.id, "Not my turn"
    self._cache_card_lists(game_view)
    if game_view.is_to_lead(self.id):
      return self._on_lead_action(game_view)
    return self._not_on_lead_action(game_view)

  def _on_lead_action(self, game_view: GameState) -> PlayerAction:
    action = super().request_next_action(game_view)

    # Maybe exchange trump.
    if isinstance(action, ExchangeTrumpCardAction):
      return action

    # Check if we have a preferred marriage in hand, but don't play it yet
    # because we might have higher cards that cannot be beaten by the opponent
    # (e.g., Trump Ace) and can secure the necessary points such that showing
    # the marriage will end the game.
    self._marriage_suit = None
    if isinstance(action, AnnounceMarriageAction):
      self._marriage_suit = action.card.suit

    # Maybe close the talon.
    close_talon_action = self._should_close_talon(game_view)
    if close_talon_action is not None:
      return close_talon_action

    # Get the preferred action to be played depending on the game state.
    if not game_view.must_follow_suit():
      return self._on_lead_do_not_follow_suit(game_view)
    else:
      return self._on_lead_follow_suit(game_view)

  def _on_lead_do_not_follow_suit(self,
                                  game_view: GameState) -> PlayerAction:
    winning_cards = {k: v for k, v in
                     self._get_winning_prob(game_view).items() if v == 1.0}
    remaining_cards = self._remaining_cards
    points = game_view.trick_points[self.id]
    king = None
    if self._marriage_suit is not None:
      marriage_value = 40 if self._marriage_suit == game_view.trump else 20
      points += marriage_value
      king = Card(self._marriage_suit, CardValue.KING)

    # If the cards that cannot be won by the opponent can get us to the end,
    # start playing them.
    if len(winning_cards) > 0:
      points += sum(
        [card.card_value for card in remaining_cards[:len(winning_cards)]])
      points += sum([card.card_value for card in winning_cards])
      if points > 65:
        card = list(winning_cards.keys())[0]
        if card in [CardValue.QUEEN, CardValue.KING] \
            and card.marriage_pair in self._my_cards:
          return AnnounceMarriageAction(self.id, card)
        return PlayCardAction(self.id, card)

    # If we cannot win yet, and we have a marriage, announce it. If the Ace and
    # Ten from that suit cannot be in the opponents hand, play the King.
    if self._marriage_suit is not None:
      ten = Card(self._marriage_suit, CardValue.TEN)
      ace = Card(self._marriage_suit, CardValue.ACE)
      if (ten in self._my_cards or ten in self._played_cards) and \
          (ace in self._my_cards or ace in self._played_cards):
        return AnnounceMarriageAction(self.id, king)
      return AnnounceMarriageAction(self.id, king.marriage_pair)

    card = self._maybe_trump_control(game_view)
    if card is not None:
      return PlayCardAction(self.id, card)

    # Play a small card.
    card = self._best_discard(game_view)
    return PlayCardAction(self.id, card)

  def _on_lead_follow_suit(self,
                           game_view: GameState) -> PlayerAction:
    winning_cards = self._get_winning_prob(game_view)
    max_chance = max(winning_cards.values())
    if max_chance > 0:  # TODO: Set a threshold here.
      if self._marriage_suit is not None:
        king = Card(self._marriage_suit, CardValue.KING)
        if winning_cards.get(king, 0) == max_chance:
          return AnnounceMarriageAction(self.id, king)
      card = random.choice(
        [c for c, v in winning_cards.items() if v == max_chance])
      if card in [CardValue.QUEEN, CardValue.KING] \
          and card.marriage_pair in self._my_cards:
        return AnnounceMarriageAction(self.id, card)
      return PlayCardAction(self.id, card)

    if self._marriage_suit is not None:
      return AnnounceMarriageAction(self.id,
                                    Card(self._marriage_suit, CardValue.KING))

    card = self._best_discard(game_view)
    return PlayCardAction(self.id, card)

  def _get_winning_prob(self, game_view):
    return _get_winning_prob(self._my_cards,
                             self._remaining_cards,
                             game_view.cards_in_hand[self.id.opponent()],
                             game_view.trump, game_view.must_follow_suit())

  def _get_remaining_cards(self, game_view: GameState) -> List[Card]:
    remaining_cards = set(Card.get_all_cards())
    remaining_cards -= set(self._my_cards)
    remaining_cards -= set(self._played_cards)
    remaining_cards -= {game_view.trump_card}
    return list(remaining_cards)

  def _not_on_lead_action(self, game_view: GameState) -> PlayerAction:
    if game_view.must_follow_suit():
      played_card = self._not_on_lead_follow_suit(game_view)
    else:
      played_card = self._not_on_lead_do_not_follow_suit(game_view)
    return PlayCardAction(self.id, played_card)

  def _not_on_lead_follow_suit(self, game_view: GameState) -> Card:
    played_card = game_view.current_trick[self.id.opponent()]
    assert played_card is not None
    best_same_suit_card = self._best_same_suit_card(played_card, game_view)
    if best_same_suit_card is not None:
      my_same_suit_cards = [c for c in self._my_cards if
                            c.suit == played_card.suit]
      if best_same_suit_card.card_value == CardValue.KING and \
          best_same_suit_card.marriage_pair in self._my_cards and \
          len(my_same_suit_cards) > 2:
        my_same_suit_cards.remove(best_same_suit_card)
        my_same_suit_cards.remove(best_same_suit_card.marriage_pair)
        best_same_suit_card = my_same_suit_cards[-1]
      return best_same_suit_card

    # Do we have to play trump?
    trump_suit_cards = [card for card in self._my_cards if
                        card.suit == game_view.trump]
    trump_suit_cards.sort(key=_key_by_value_and_suit)
    if len(trump_suit_cards) > 0:
      all_trump_cards = [Card(game_view.trump, card_value) for card_value
                         in CardValue]
      remaining_trump_cards = [card for card in all_trump_cards if
                               card not in self._played_cards]
      max_opp = len(remaining_trump_cards) - 1
      max_self = len(trump_suit_cards) - 1
      while max_opp >= 0 and max_self >= 1:
        if remaining_trump_cards[max_opp] > trump_suit_cards[max_self]:
          break
        max_opp -= 1
        max_self -= 1
      trump_card = _highest_adjacent_card_in_hand(
        trump_suit_cards[max_self],
        self._my_cards,
        self._played_cards)
      if trump_card.card_value in [CardValue.KING, CardValue.QUEEN] and \
          trump_card.marriage_pair in self._my_trump_cards and \
          len(self._my_trump_cards) > 2:
        self._my_trump_cards.remove(trump_card)
        self._my_trump_cards.remove(trump_card.marriage_pair)
        trump_card = self._my_trump_cards[-1]
      return trump_card
    return self._best_discard(game_view)

  def _my_smallest_non_trump_card(self, game_view: GameState) -> Optional[Card]:
    non_trump_cards = [card for card in self._my_cards if
                       card.suit != game_view.trump]
    non_trump_cards.sort(key=_key_by_value_and_suit)
    if len(non_trump_cards) > 0:
      return non_trump_cards[0]
    return None

  def _not_on_lead_do_not_follow_suit(self, game_view: GameState) -> Card:
    played_card = game_view.current_trick[self.id.opponent()]
    assert played_card is not None
    best_same_suit_card = self._best_same_suit_card(played_card, game_view)
    if best_same_suit_card is not None:
      if best_same_suit_card.wins(played_card, game_view.trump):
        if best_same_suit_card.card_value == CardValue.KING and \
            best_same_suit_card.marriage_pair in self._my_cards:
          # Here we break a marriage to win a Jack from the same suit.
          if not self._save_marriages:
            return best_same_suit_card
        else:
          return best_same_suit_card

    trump_for_marriage = False
    if self._trump_for_marriage:
      for suit in Suit:
        king = Card(suit, CardValue.KING)
        if king in self._my_cards and king.marriage_pair in self._my_cards:
          if suit != game_view.trump or len(self._my_trump_cards) > 2:
            trump_for_marriage = True
            break

    if len(game_view.won_tricks.one) + len(game_view.won_tricks.two) == 3 and \
        self._can_exchange_trump_jack_for_marriage(game_view):
      trump_for_marriage = True

    # TODO(heuristic): Maybe trump for win.
    if played_card.card_value in [CardValue.TEN, CardValue.ACE] or \
        trump_for_marriage:
      if played_card.suit != game_view.trump:
        trump_card = self._win_with_trump(game_view)
        if trump_card is not None:
          return trump_card

    return self._best_discard(game_view)

  def _win_with_trump(self, game_view: GameState) -> Card:
    if len(self._my_trump_cards) > 0:
      trump_card = _highest_adjacent_card_in_hand(self._my_trump_cards[0],
                                                  self._my_cards,
                                                  self._played_cards)
      if trump_card.card_value == CardValue.KING and \
          trump_card.marriage_pair in self._my_trump_cards and \
          len(self._my_trump_cards) > 2:
        self._my_trump_cards.remove(trump_card)
        self._my_trump_cards.remove(trump_card.marriage_pair)
        return self._my_trump_cards[-1]
      if self._can_exchange_trump_jack_for_marriage(game_view):
        self._my_trump_cards.remove(Card(game_view.trump, CardValue.JACK))
        self._my_trump_cards.remove(game_view.trump_card.marriage_pair)
        return self._my_trump_cards[-1]
      return trump_card

  def _can_exchange_trump_jack_for_marriage(self, game_view):
    if len(self._my_trump_cards) <= 2:
      return False
    jack = Card(game_view.trump, CardValue.JACK)
    if jack not in self._my_trump_cards:
      return False
    king = Card(game_view.trump, CardValue.KING)
    queen = Card(game_view.trump, CardValue.QUEEN)
    if king in self._my_trump_cards and queen == game_view.trump_card:
      return True
    if queen in self._my_trump_cards and king == game_view.trump_card:
      return True
    return False

  def _best_same_suit_card(self, played_card: Card,
                           game_view: GameState) -> Optional[Card]:
    same_suit_cards = [card for card in self._my_cards if
                       played_card.suit == card.suit]
    same_suit_cards.sort(key=_key_by_value_and_suit)
    if len(same_suit_cards) > 0:
      winning_cards = [card for card in same_suit_cards if
                       card.card_value > played_card.card_value]
      winning_cards.sort(key=_key_by_value_and_suit)
      if len(winning_cards) > 0:
        # Get the highest not-yet-played card from the same suit.
        all_cards_same_suit = [Card(played_card.suit, card_value) for card_value
                               in CardValue]
        remaining_cards_same_suit = [card for card in all_cards_same_suit if
                                     card not in self._played_cards \
                                     and card != played_card and \
                                     card not in self._my_cards]
        max_opp = len(remaining_cards_same_suit) - 1
        max_self = len(winning_cards) - 1
        while max_opp >= 0 and max_self >= 1:
          if remaining_cards_same_suit[max_opp] > winning_cards[max_self]:
            # TODO(heuristic): Update similar to _not_on_lead_follow_suit to
            # save marriage or return adjacent.
            return winning_cards[max_self]
          max_opp -= 1
          max_self -= 1
        return _highest_adjacent_card_in_hand(winning_cards[max_self],
                                              self._my_cards,
                                              self._played_cards)

      # We must play same suit smaller card, so play the smallest.
      return same_suit_cards[0]
    return None

  def _best_discard(self, game_view: GameState) -> Card:
    if self._smart_discard:
      return self._discard_with_priorities(game_view)
    card = self._my_smallest_non_trump_card(game_view)
    if card is not None:
      return card
    return min(self._my_cards, key=_key_by_value_and_suit)

  def _discard_with_priorities(self, game_view: GameState) -> Card:
    priorities = ["cards_from_exhausted_suits",
                  "jack_with_ten_protection",
                  "jack_with_no_ten_protection",
                  "queen_or_king_with_no_marriage_chance",
                  "queen_or_king_with_marriage_chance",
                  "queen_or_king_with_marriage_in_hand",
                  "other_non_trump_cards",
                  "trump_cards"]
    preferred_discards = {priority: [] for priority in priorities}
    current_played_card = game_view.current_trick[self.id.opponent()]
    remaining_suits = set(card.suit for card in self._remaining_cards)
    played_cards = self._played_cards
    if current_played_card is not None:
      played_cards = self._played_cards + [current_played_card]
    for card in self._my_cards:
      if card.suit == game_view.trump:
        preferred_discards["trump_cards"].append(card)
        continue
      if card.suit not in remaining_suits:
        preferred_discards["cards_from_exhausted_suits"].append(card)
      elif card.card_value == CardValue.JACK:
        ten = Card(card.suit, CardValue.TEN)
        ace = Card(card.suit, CardValue.ACE)
        king = Card(card.suit, CardValue.KING)
        queen = Card(card.suit, CardValue.QUEEN)
        if ten in self._my_cards and \
            ace not in self._my_cards and \
            ace not in played_cards and \
            king not in self._my_cards and \
            queen not in self._my_cards:
          preferred_discards["jack_with_no_ten_protection"].append(card)
        else:
          preferred_discards["jack_with_ten_protection"].append(card)
      elif card.card_value in [CardValue.QUEEN, CardValue.KING]:
        marriage_pair = card.marriage_pair
        if marriage_pair in self._my_cards:
          preferred_discards["queen_or_king_with_marriage_in_hand"].append(card)
        elif marriage_pair not in played_cards:
          preferred_discards["queen_or_king_with_marriage_chance"].append(card)
        else:
          preferred_discards["queen_or_king_with_no_marriage_chance"].append(
            card)
      else:
        preferred_discards["other_non_trump_cards"].append(card)
    best_card = None
    for priority in priorities:
      cards = preferred_discards[priority]
      if len(cards) > 0:
        cards.sort(key=_key_by_value_and_suit)
        best_card = cards[0]
        break
    if self._avoid_direct_loss and current_played_card is not None:
      points = current_played_card.card_value + game_view.trick_points[
        self.id.opponent()]
      if points + best_card.card_value > 65:
        trump_card = self._win_with_trump(game_view)
        if trump_card is not None:
          return trump_card
        smallest_card = self._my_smallest_non_trump_card(game_view)
        if smallest_card is not None:
          return smallest_card
        return min(self._my_cards, key=_key_by_value_and_suit)
    return best_card

  def _should_close_talon(self, game_view: GameState) -> Optional[
    CloseTheTalonAction]:
    if not self._can_close_talon:
      return None
    action = CloseTheTalonAction(self.id)
    if not action.can_execute_on(game_view):
      return None
    # This is just an estimation. The two big flaws are:
    #   * If multiple cards have a probability of 1.0, it means that playing
    #     them as the next card will win the next trick. But it doesn't mean the
    #     probabilities will stay the same after this trick. For example, if we
    #     have the Ace and Ten from a non-trump suit, they might have both a
    #     probability of 1.0 if it's guaranteed that the opponent has one card
    #     from the same non-trump suit, but after we play the Ace, the Ten might
    #     not have a probability of 1.0 anymore if there are no more cards from
    #     this suit and the opponent can trump it.
    #   * It computes a lower bound on the number of points we can gain by
    #     assuming that the opponent plays the smallest remaining cards (without
    #     following suit), but since suit must be followed we might gain more
    #     than what we estimate here.
    # Overall, despite these two big flaws, it seems the player behaves better
    # with this heuristic enabled.
    winning_prob = self._get_winning_prob(game_view)
    total = game_view.trick_points[self.id]
    prob_and_cards = [(prob, card) for card, prob in winning_prob.items()]
    prob_and_cards.sort(reverse=True)
    for i, prod_and_card in enumerate(prob_and_cards):
      prob, card = prod_and_card
      total += prob * (card.card_value + self._remaining_cards[i].card_value)
    if total > 65:
      return action
    return None

  def _maybe_trump_control(self, game_view: GameState):
    if not self._trump_control:
      return None

    # If the opponent can win the game by trumping out high card, don't play it.
    remaining_trumps = [c for c in self._remaining_cards if
                        c.suit == game_view.trump]
    if len(remaining_trumps) > 0:
      max_remaining_trump = max(remaining_trumps)
      if max_remaining_trump.card_value + CardValue.ACE > 65:
        return None

    num_my_trumps = len(self._my_trump_cards)
    opp_cards = game_view.cards_in_hand[self.id.opponent()]
    num_opp_trumps = len([card for card in opp_cards if
                          card is not None and card.suit == game_view.trump])
    played_trumps = len(
      [card for card in self._played_cards if card.suit == game_view.trump])
    num_remaining_trumps = 5 - num_my_trumps - num_opp_trumps - played_trumps - \
                           (1 if game_view.trump_card is not None else 0)
    num_opp_unknown_cards = len([card for card in opp_cards if card is None])
    if not game_view.is_talon_closed and len(game_view.talon) == 1:
      num_opp_trumps += 1
      num_opp_unknown_cards -= 1
    num_remaining_cards = len(self._remaining_cards)
    num_remaining_cards -= len([c for c in opp_cards if c is not None])
    total_scenarios = comb(num_remaining_cards, num_opp_unknown_cards)
    probabilities = []
    for i in range(num_remaining_trumps + 1):
      possible_opp_trumps = num_opp_trumps + i
      if possible_opp_trumps <= num_my_trumps:
        continue
      if num_opp_unknown_cards < i:
        break
      possibilities = comb(num_remaining_trumps, i) * comb(
        num_remaining_cards - num_remaining_trumps,
        num_opp_unknown_cards - i)
      probabilities.append(possibilities / total_scenarios)
    if sum(probabilities) > 0.5:
      high_cards = [card for card in self._my_cards if
                    card.suit != game_view.trump
                    and card.card_value in [CardValue.TEN, CardValue.ACE]]
      if len(high_cards) > 0:
        remaining_suits = set(c.suit for c in self._remaining_cards)
        single_tens = [c for c in high_cards if
                       c.card_value == CardValue.TEN and \
                       c.suit not in remaining_suits]
        other_tens = [c for c in high_cards if
                      c.card_value == CardValue.TEN and \
                      c.suit in remaining_suits]
        single_aces = [c for c in high_cards if
                       c.card_value == CardValue.ACE and \
                       c.suit not in remaining_suits]
        other_aces = [c for c in high_cards if
                      c.card_value == CardValue.ACE and \
                      c.suit in remaining_suits]
        for card_list in [single_tens, single_aces, other_tens, other_aces]:
          if len(card_list) > 0:
            return random.choice(card_list)
    return None
