#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import enum
import random
from math import comb
from typing import List, Optional, Dict

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
  opp_public_cards = {card for card in opp_cards if card is not None}
  opp_trumps = {card for card in opp_public_cards if card.suit == trump}
  num_opp_unknown_cards = len(opp_cards) - len(opp_public_cards)

  unseen_cards = [card for card in remaining_cards if
                  card not in opp_public_cards]
  unplayed_trumps = [card for card in remaining_cards if card.suit == trump]

  winning_prob = {}
  for card_in_hand in cards_in_hand:
    # Probability that this card cannot be won by the opponent.
    unplayed_cards_same_suit = [card for card in remaining_cards if
                                card.suit == card_in_hand.suit]
    unplayed_better_cards = [card for card in unplayed_cards_same_suit if
                             card.card_value > card_in_hand.card_value]
    if not must_follow_suit and card_in_hand.suit != trump:
      unplayed_better_cards += unplayed_trumps

    if len(opp_public_cards.intersection(unplayed_better_cards)) > 0:
      winning_prob[card_in_hand] = 0.0
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
                                      i) * comb(
          num_unimportant_cards, num_opp_unknown_cards - i)
    winning_prob[card_in_hand] = num_winning_scenarios / num_total_scenarios
  return winning_prob


# TODO(heuristic): When closing the talon/winning probs, count trumps from your
#   hand to counter remaining trumps. Then non-trump Ace or Ten could have
#   prob == 1.0.

# TODO(ai): Replace RandomPlayer with Player when the implementation in ready.
class HeuristicPlayer(RandomPlayer):
  """http://psellos.com/schnapsen/strategy.html"""

  def __init__(self, player_id: PlayerId, can_close_talon=False,
               smart_discard: bool = True, save_marriages=False,
               trump_for_marriage=False, avoid_direct_loss=False,
               trump_control=False):
    super().__init__(player_id=player_id, force_trump_exchange=True,
                     never_close_talon=True, force_marriage_announcement=True)
    self._smart_discard = smart_discard
    self._can_close_talon = can_close_talon
    self._save_marriages = save_marriages
    self._trump_for_marriage = trump_for_marriage
    self._avoid_direct_loss = avoid_direct_loss
    self._trump_control = trump_control
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
    if game_view.must_follow_suit():
      return self._on_lead_follow_suit(game_view)
    return self._on_lead_do_not_follow_suit(game_view)

  def _on_lead_do_not_follow_suit(self,
                                  game_view: GameState) -> PlayerAction:
    # If the cards that cannot be won by the opponent can get us to the end,
    # start playing them.
    action = self._play_winning_cards(game_view)
    if action is not None:
      return action

    # If we cannot win yet, and we have a marriage, announce it. If the Ace and
    # Ten from that suit cannot be in the opponents hand, play the King.
    if self._marriage_suit is not None:
      king = Card(self._marriage_suit, CardValue.KING)
      ten = Card(self._marriage_suit, CardValue.TEN)
      ace = Card(self._marriage_suit, CardValue.ACE)
      if (ten in self._my_cards or ten in self._played_cards) and \
          (ace in self._my_cards or ace in self._played_cards):
        return AnnounceMarriageAction(self.id, king)
      return AnnounceMarriageAction(self.id, king.marriage_pair)

    # If we expect that the opponent has more trumps and we have big cards
    # (i.e., tens or aces), play one of the high card to force the opponent to
    # either play a trump or give up a lot of points.
    card = self._maybe_trump_control(game_view)
    if card is not None:
      return PlayCardAction(self.id, card)

    # Discard one of the small cards.
    card = self._best_discard(game_view)
    return PlayCardAction(self.id, card)

  def _play_winning_cards(self, game_view: GameState) -> Optional[PlayerAction]:
    winning_cards = {card: prob for card, prob in
                     self._get_winning_prob(game_view).items() if prob == 1.0}
    if len(winning_cards) == 0:
      return None
    remaining_cards = self._remaining_cards
    points = game_view.trick_points[self.id]
    if self._marriage_suit is not None:
      marriage_value = 40 if self._marriage_suit == game_view.trump else 20
      points += marriage_value
    points += sum(
      [card.card_value for card in remaining_cards[:len(winning_cards)]])
    points += sum([card.card_value for card in winning_cards])
    if points < 66:
      return None
    # TODO(heuristic): Pick a random winning card.
    card = list(winning_cards.keys())[0]
    return self._play_card_or_marriage(card)

  def _play_card_or_marriage(self, card: Card) -> PlayerAction:
    if card in [CardValue.QUEEN, CardValue.KING] \
        and card.marriage_pair in self._my_cards:
      return AnnounceMarriageAction(self.id, card)
    return PlayCardAction(self.id, card)

  def _on_lead_follow_suit(self,
                           game_view: GameState) -> PlayerAction:
    # If talon is depleted, the probabilities here would be either 0 or 1. If
    # we have any card with 100% winning prob, play it. If the talon is closed,
    # play the card with the highest probability to win (can be smaller than 1).
    probabilities = self._get_winning_prob(game_view)
    max_chance = max(probabilities.values())
    if max_chance > 0:  # TODO: Set a threshold here.
      # If we have a marriage and the king has the same winning chance as the
      # maximum among all the other cards in hand, prefer to announce the
      # marriage.
      if self._marriage_suit is not None:
        king = Card(self._marriage_suit, CardValue.KING)
        if probabilities.get(king, 0) == max_chance:
          return AnnounceMarriageAction(self.id, king)

      # Play a random card among the ones with the highest chance to win the
      # next trick.
      card_to_play = random.choice(
        [card for card, prob in probabilities.items() if prob == max_chance])
      return self._play_card_or_marriage(card_to_play)

    # If there is no chance we win the next trick and we have a marriage,
    # announce it.
    if self._marriage_suit is not None:
      return AnnounceMarriageAction(self.id,
                                    Card(self._marriage_suit, CardValue.KING))

    # Discard one of the small cards.
    card_to_play = self._best_discard(game_view)
    return PlayCardAction(self.id, card_to_play)

  def _get_winning_prob(self, game_view: GameState) -> Dict[Card, float]:
    return _get_winning_prob(self._my_cards,
                             self._remaining_cards,
                             game_view.cards_in_hand[self.id.opponent()],
                             game_view.trump,
                             game_view.must_follow_suit())

  def _get_remaining_cards(self, game_view: GameState) -> List[Card]:
    remaining_cards = set(Card.get_all_cards())
    remaining_cards -= set(self._my_cards)
    remaining_cards -= set(self._played_cards)
    remaining_cards -= {game_view.trump_card}
    return list(remaining_cards)

  def _not_on_lead_action(self, game_view: GameState) -> PlayerAction:
    if game_view.must_follow_suit():
      card = self._not_on_lead_follow_suit(game_view)
    else:
      card = self._not_on_lead_do_not_follow_suit(game_view)
    return PlayCardAction(self.id, card)

  def _not_on_lead_follow_suit(self, game_view: GameState) -> Card:
    opp_card = game_view.current_trick[self.id.opponent()]
    assert opp_card is not None
    best_same_suit_card = self._best_same_suit_card(opp_card)
    if best_same_suit_card is not None:
      return self._avoid_breaking_marriage(best_same_suit_card)

    # No trump? Discard a small card.
    if len(self._my_trump_cards) == 0:
      return self._best_discard(game_view)

    # Find the best trump card to play.
    trump_card_to_play = self._best_winning_card(opp_card, self._my_trump_cards)
    return self._avoid_breaking_marriage(trump_card_to_play)

  def _avoid_breaking_marriage(self, card_to_play: Card) -> Card:
    same_suit_cards = [card for card in self._my_cards if
                       card.suit == card_to_play.suit]
    if len(same_suit_cards) < 3:
      return card_to_play
    if card_to_play.card_value in [CardValue.KING, CardValue.QUEEN] and \
        card_to_play.marriage_pair in same_suit_cards:
      same_suit_cards.remove(card_to_play)
      same_suit_cards.remove(card_to_play.marriage_pair)
      return same_suit_cards[-1]
    return card_to_play

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

    # If we can win with a same suit card, do it.
    best_same_suit_card = self._best_same_suit_card(played_card)
    if best_same_suit_card is not None:
      if best_same_suit_card.wins(played_card, game_view.trump):
        if best_same_suit_card.card_value == CardValue.KING and \
            best_same_suit_card.marriage_pair in self._my_cards:
          # Here we break a marriage to win a Jack from the same suit.
          if not self._save_marriages:
            return best_same_suit_card
        else:
          return best_same_suit_card

    if played_card.suit == game_view.trump or len(self._my_trump_cards) == 0:
      return self._best_discard(game_view)

    use_trump = played_card.card_value in [CardValue.TEN, CardValue.ACE]
    if not use_trump:
      use_trump = self._should_trump_for_marriage(game_view)
    if not use_trump:
      num_played_tricks = len(game_view.won_tricks.one) + \
                          len(game_view.won_tricks.two)
      if num_played_tricks == 3 and \
          self._can_exchange_trump_jack_for_marriage(game_view):
        use_trump = True

    trump_card = self._maybe_trump_for_the_win(game_view)
    if trump_card is not None:
      return trump_card

    if use_trump:
      return self._win_with_trump(game_view)

    return self._best_discard(game_view)

  def _maybe_trump_for_the_win(self, game_view: GameState) -> Optional[Card]:
    if len(self._my_trump_cards) == 0:
      return None
    played_card = game_view.current_trick[self.id.opponent()]
    assert played_card is not None
    winning_cards = {card: prob for card, prob in
                     self._get_winning_prob(game_view).items() if prob == 1.0}
    unplayed_cards = [card for card in self._remaining_cards if
                      card != played_card]
    min_trump_card = min(self._my_trump_cards)
    points = game_view.trick_points[self.id]
    points += played_card.card_value + min_trump_card.card_value
    if min_trump_card in winning_cards:
      del winning_cards[min_trump_card]
    points += sum([card.card_value for card in winning_cards])
    points += sum(
      [card.card_value for card in unplayed_cards[:len(winning_cards)]])
    if points > 65:
      return min_trump_card
    return None

  def _should_trump_for_marriage(self, game_view):
    if not self._trump_for_marriage:
      return False
    for suit in Suit:
      king = Card(suit, CardValue.KING)
      if king in self._my_cards and king.marriage_pair in self._my_cards:
        if suit != game_view.trump or len(self._my_trump_cards) > 2:
          return True
    return False

  def _win_with_trump(self, game_view: GameState) -> Card:
    assert len(self._my_trump_cards) > 0
    trump_card = _highest_adjacent_card_in_hand(self._my_trump_cards[0],
                                                self._my_cards,
                                                self._played_cards)
    if self._can_exchange_trump_jack_for_marriage(game_view):
      self._my_trump_cards.remove(Card(game_view.trump, CardValue.JACK))
      self._my_trump_cards.remove(game_view.trump_card.marriage_pair)
      return self._my_trump_cards[-1]
    return self._avoid_breaking_marriage(trump_card)

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

  def _best_same_suit_card(self, opp_card: Card) -> Optional[Card]:
    same_suit_cards = [card for card in self._my_cards if
                       opp_card.suit == card.suit]
    same_suit_cards.sort(key=_key_by_value_and_suit)
    if len(same_suit_cards) == 0:
      return None
    winning_cards = [card for card in same_suit_cards if
                     card.card_value > opp_card.card_value]
    winning_cards.sort(key=_key_by_value_and_suit)
    if len(winning_cards) == 0:
      return same_suit_cards[0]
    return self._best_winning_card(opp_card, winning_cards)

  def _best_winning_card(self, opp_card: Card,
                         winning_cards: List[Card]) -> Card:
    assert len({card.suit for card in winning_cards}) == 1, winning_cards
    suit = winning_cards[0].suit
    all_cards_same_suit = [Card(suit, card_value) for card_value in CardValue]
    unplayed_cards_same_suit = [card for card in all_cards_same_suit if
                                card not in self._played_cards \
                                and card != opp_card and \
                                card not in self._my_cards]
    max_opp = len(unplayed_cards_same_suit) - 1
    max_self = len(winning_cards) - 1
    while max_opp >= 0 and max_self >= 1:
      if unplayed_cards_same_suit[max_opp] > winning_cards[max_self]:
        break
      max_opp -= 1
      max_self -= 1
    return _highest_adjacent_card_in_hand(winning_cards[max_self],
                                          self._my_cards,
                                          self._played_cards)

  def _best_discard(self, game_view: GameState) -> Card:
    if self._smart_discard:
      return self._discard_with_priorities(game_view)
    card = self._my_smallest_non_trump_card(game_view)
    if card is not None:
      return card
    return min(self._my_cards, key=_key_by_value_and_suit)

  def _discard_with_priorities(self, game_view: GameState) -> Card:
    class Priority(enum.Enum):
      EXHAUSTED_SUITS = enum.auto()
      JACK_WITH_TEN_PROTECTION = enum.auto()
      JACK_WITHOUT_TEN_PROTECTION = enum.auto()
      QUEEN_OR_KING_WITHOUT_MARRIAGE_CHANCE = enum.auto()
      QUEEN_OR_KING_WITH_MARRIAGE_CHANCE = enum.auto()
      QUEEN_OR_KING_WITH_MARRIAGE_IN_HAND = enum.auto()
      OTHER_NON_TRUMP_CARDS = enum.auto()
      TRUMP_CARDS = enum.auto()

    buckets = {priority: [] for priority in Priority}
    remaining_suits = set(card.suit for card in self._remaining_cards)
    played_cards = self._played_cards
    opp_card = game_view.current_trick[self.id.opponent()]
    if opp_card is not None:
      played_cards = self._played_cards + [opp_card]

    # Place each card in its priority bucket.
    for card in self._my_cards:
      if card.suit == game_view.trump:
        buckets[Priority.TRUMP_CARDS].append(card)
      elif card.suit not in remaining_suits:
        buckets[Priority.EXHAUSTED_SUITS].append(card)
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
          buckets[Priority.JACK_WITHOUT_TEN_PROTECTION].append(card)
        else:
          buckets[Priority.JACK_WITH_TEN_PROTECTION].append(card)
      elif card.card_value in [CardValue.QUEEN, CardValue.KING]:
        marriage_pair = card.marriage_pair
        if marriage_pair in self._my_cards:
          buckets[Priority.QUEEN_OR_KING_WITH_MARRIAGE_IN_HAND].append(card)
        elif marriage_pair not in played_cards:
          buckets[Priority.QUEEN_OR_KING_WITH_MARRIAGE_CHANCE].append(card)
        else:
          buckets[Priority.QUEEN_OR_KING_WITHOUT_MARRIAGE_CHANCE].append(card)
      else:
        buckets[Priority.OTHER_NON_TRUMP_CARDS].append(card)

    # Get the smallest card from the first non-empty bucket sorted by
    # priority.
    best_card = None
    for priority in Priority:
      cards = buckets[priority]
      if len(cards) > 0:
        cards.sort(key=_key_by_value_and_suit)
        best_card = cards[0]
        break

    # If the best card so far would lead to a direct loss, try to avoid it.
    if self._avoid_direct_loss and opp_card is not None:
      points = opp_card.card_value + game_view.trick_points[self.id.opponent()]
      if points + best_card.card_value > 65:
        if len(self._my_trump_cards) > 0:
          return self._win_with_trump(game_view)
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
    probabilities = self._get_winning_prob(game_view)
    points = game_view.trick_points[self.id]
    prob_and_cards = [(prob, card) for card, prob in probabilities.items()]
    prob_and_cards.sort(reverse=True)
    for i, prod_and_card in enumerate(prob_and_cards):
      prob, card = prod_and_card
      points += prob * (card.card_value + self._remaining_cards[i].card_value)
    if points > 65:
      return action
    return None

  def _maybe_trump_control(self, game_view: GameState) -> Optional[Card]:
    if not self._trump_control:
      return None

    high_cards = [card for card in self._my_cards if
                  card.suit != game_view.trump
                  and card.card_value in [CardValue.TEN, CardValue.ACE]]
    if len(high_cards) == 0:
      return None

    # If the opponent can win the game by trumping out high card, don't play it.
    remaining_trumps = [card for card in self._remaining_cards if
                        card.suit == game_view.trump]
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

    num_remaining_trumps = 5 - num_my_trumps - num_opp_trumps
    num_remaining_trumps -= played_trumps
    num_remaining_trumps -= (1 if game_view.trump_card is not None else 0)

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

    if sum(probabilities) <= 0.5:
      return None

    remaining_suits = set(card.suit for card in self._remaining_cards)
    single_tens = [card for card in high_cards if
                   card.card_value == CardValue.TEN and \
                   card.suit not in remaining_suits]
    other_tens = [card for card in high_cards if
                  card.card_value == CardValue.TEN and \
                  card.suit in remaining_suits]
    single_aces = [card for card in high_cards if
                   card.card_value == CardValue.ACE and \
                   card.suit not in remaining_suits]
    other_aces = [card for card in high_cards if
                  card.card_value == CardValue.ACE and \
                  card.suit in remaining_suits]
    for card_list in [single_tens, single_aces, other_tens, other_aces]:
      if len(card_list) > 0:
        return random.choice(card_list)
    assert False, "Should not reach this code"
