#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.
import random
from typing import List, Optional

from ai.random_player import RandomPlayer
from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState
from model.player_action import PlayerAction, PlayCardAction, \
  ExchangeTrumpCardAction, AnnounceMarriageAction
from model.player_id import PlayerId


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


# TODO(ai): Consider trump control from http://psellos.com/schnapsen/strategy.html.
# Play aces or tens early if the trump situation favors your opponent.

# TODO(ai): cache.

# TODO(ai): Replace RandomPLayer with Player when the implementation in ready.
class HeuristicPlayer(RandomPlayer):
  """http://psellos.com/schnapsen/strategy.html"""

  def __init__(self, player_id: PlayerId,
               smart_discard: bool = True):
    super().__init__(player_id=player_id, force_trump_exchange=True,
                     never_close_talon=True, force_marriage_announcement=True)
    self._smart_discard = smart_discard
    self._marriage_suit = None

  def request_next_action(self, game_view: GameState) -> PlayerAction:
    assert game_view.next_player == self.id, "Not my turn"
    if game_view.is_to_lead(self.id):
      return self._get_leading_action(game_view)
    return self._get_answer_action(game_view)

  def _get_leading_action(self, game_view: GameState) -> PlayerAction:
    # TODO(ai): Maybe close the talon.
    action = super().request_next_action(game_view)
    if isinstance(action, ExchangeTrumpCardAction):
      return action
    self._marriage_suit = None
    if isinstance(action, AnnounceMarriageAction):
      self._marriage_suit = action.card.suit
    if not game_view.must_follow_suit():
      return self._get_leading_action_dont_follow_suit(game_view)
    else:
      return self._get_leading_action_follow_suit(game_view)

  def _get_leading_action_dont_follow_suit(self,
                                           game_view: GameState) -> PlayerAction:
    winning_cards = {k: v for k, v in
                     self._get_winning_scores(game_view).items() if v == 1.0}
    remaining_cards = self._get_remaining_cards(game_view)
    remaining_cards.sort(key=_key_by_value_and_suit)
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
            and card.marriage_pair in game_view.cards_in_hand[self.id]:
          return AnnounceMarriageAction(self.id, card)
        return PlayCardAction(self.id, card)

    # If we cannot win yet, and we have a marriage, announce it. If the Ace and
    # Ten from that suit cannot be in the opponents hand, play the King.
    if self._marriage_suit is not None:
      ten = Card(self._marriage_suit, CardValue.TEN)
      ace = Card(self._marriage_suit, CardValue.ACE)
      cards_in_hand = game_view.cards_in_hand[self.id]
      played_cards = _get_played_cards(game_view)
      if (ten in cards_in_hand or ten in played_cards) and \
          (ace in cards_in_hand or ace in played_cards):
        return AnnounceMarriageAction(self.id, king)
      return AnnounceMarriageAction(self.id, king.marriage_pair)

    # Play a small card.
    card = self._best_discard(game_view)
    return PlayCardAction(self.id, card)

  def _get_leading_action_follow_suit(self,
                                      game_view: GameState) -> PlayerAction:
    winning_cards = self._get_winning_scores(game_view)
    if len(winning_cards) > 0:
      max_chance = max(winning_cards.values())
      if self._marriage_suit is not None:
        king = Card(self._marriage_suit, CardValue.KING)
        if winning_cards.get(king, 0) == max_chance:
          return AnnounceMarriageAction(self.id, king)
      card = random.choice(
        [c for c, v in winning_cards.items() if v == max_chance])
      if card in [CardValue.QUEEN, CardValue.KING] \
          and card.marriage_pair in game_view.cards_in_hand[self.id]:
        return AnnounceMarriageAction(self.id, card)
      return PlayCardAction(self.id, card)

    if self._marriage_suit is not None:
      return AnnounceMarriageAction(self.id,
                                    Card(self._marriage_suit, CardValue.KING))

    card = self._best_discard(game_view)
    return PlayCardAction(self.id, card)

  def _get_winning_scores(self, game_view):
    remaining_cards = self._get_remaining_cards(game_view)
    remaining_trumps = [card for card in remaining_cards if
                        card.suit == game_view.trump]
    # Play the highest card that surely wins.
    winning_cards = {}
    for card in game_view.cards_in_hand[self.id]:
      # TODO(ai): Compute the probability of winning based on:
      # - not having a higher same suit card, having a smaller same suit card,
      # - not having a same suit card, not having a trump.
      remaining_cards_same_suit = [c for c in remaining_cards if
                                   c.suit == card.suit]
      remaining_cards_same_suit.sort(key=_key_by_value_and_suit)
      if len(remaining_cards_same_suit) == 0:
        if len(remaining_trumps) == 0:
          winning_cards[card] = 1.0
        continue
      if not game_view.must_follow_suit() and len(remaining_trumps) > 0 and \
          card.suit != game_view.trump:
        # Opponent could trump.
        continue
      if remaining_cards_same_suit[-1].card_value > card.card_value:
        # Opponent might have a better card. They could also have a trump.
        continue
      if len(game_view.talon) == 0:
        winning_cards[card] = 1.0
      else:
        if len(remaining_trumps) == 0:
          winning_cards[card] = 1.0
        else:
          winning_cards[card] = len(remaining_cards_same_suit) / len(
            remaining_cards)
    return winning_cards

  def _get_remaining_cards(self, game_view: GameState) -> List[Card]:
    remaining_cards = set(Card.get_all_cards())
    remaining_cards -= set(game_view.cards_in_hand[self.id])
    remaining_cards -= set(_get_played_cards(game_view))
    remaining_cards -= {game_view.trump_card}
    return list(remaining_cards)

  def _get_answer_action(self, game_view: GameState) -> PlayerAction:
    if game_view.must_follow_suit():
      played_card = self._get_answer_action_follow_suit(game_view)
    else:
      played_card = self._get_answer_action_do_not_follow_suit(game_view)
    return PlayCardAction(self.id, played_card)

  def _get_answer_action_follow_suit(self, game_view: GameState) -> Card:
    played_card = game_view.current_trick[self.id.opponent()]
    assert played_card is not None
    best_same_suit_card = self._best_same_suit_card(played_card, game_view)
    if best_same_suit_card is not None:
      return best_same_suit_card

    # Do we have to play trump?
    trump_suit_cards = [card for card in game_view.cards_in_hand[self.id] if
                        card.suit == game_view.trump]
    trump_suit_cards.sort(key=_key_by_value_and_suit)
    if len(trump_suit_cards) > 0:
      all_trump_cards = [Card(game_view.trump, card_value) for card_value
                         in CardValue]
      remaining_trump_cards = [card for card in all_trump_cards if
                               card not in _get_played_cards(game_view)]
      max_opp = len(remaining_trump_cards) - 1
      max_self = len(trump_suit_cards) - 1
      while max_opp >= 0 and max_self >= 1:
        if remaining_trump_cards[max_opp] > trump_suit_cards[max_self]:
          return trump_suit_cards[max_self]
        max_opp -= 1
        max_self -= 1
      return trump_suit_cards[max_self]
    return self._best_discard(game_view)

  def _smallest_non_trump_card(self, game_view: GameState) -> Optional[Card]:
    non_trump_cards = [card for card in game_view.cards_in_hand[self.id] if
                       card.suit != game_view.trump]
    non_trump_cards.sort(key=_key_by_value_and_suit)
    if len(non_trump_cards) > 0:
      return non_trump_cards[0]
    return None

  def _get_answer_action_do_not_follow_suit(self, game_view: GameState) -> Card:
    played_card = game_view.current_trick[self.id.opponent()]
    assert played_card is not None
    best_same_suit_card = self._best_same_suit_card(played_card, game_view)
    if best_same_suit_card is not None:
      if best_same_suit_card.wins(played_card, game_view.trump):
        return best_same_suit_card
    if played_card.card_value in [CardValue.TEN, CardValue.ACE]:
      if played_card.suit != game_view.trump:
        trump_cards = [card for card in game_view.cards_in_hand[self.id] if
                       card.suit == game_view.trump]
        trump_cards.sort(key=_key_by_value_and_suit)
        if len(trump_cards) > 0:
          trump_card = _highest_adjacent_card_in_hand(
            trump_cards[0], game_view.cards_in_hand[self.id],
            _get_played_cards(game_view))
          # TODO(ai): Save trump marriage.
          if trump_card.card_value == CardValue.KING and \
              trump_card.marriage_pair in trump_cards and \
              len(trump_cards) > 2:
            trump_cards.remove(trump_card)
            trump_cards.remove(trump_card.marriage_pair)
            return trump_cards[-1]
          return trump_card
    return self._best_discard(game_view)

  def _best_same_suit_card(self, played_card: Card,
                           game_view: GameState) -> Optional[Card]:
    same_suit_cards = [card for card in game_view.cards_in_hand[self.id] if
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
                                     card not in _get_played_cards(game_view) \
                                     and card != played_card and \
                                     card not in game_view.cards_in_hand[
                                       self.id]]
        max_opp = len(remaining_cards_same_suit) - 1
        max_self = len(winning_cards) - 1
        while max_opp >= 0 and max_self >= 1:
          if remaining_cards_same_suit[max_opp] > winning_cards[max_self]:
            return winning_cards[max_self]
          max_opp -= 1
          max_self -= 1
        return _highest_adjacent_card_in_hand(winning_cards[max_self],
                                              game_view.cards_in_hand[self.id],
                                              _get_played_cards(game_view))

      # We must play same suit smaller card, so play the smallest.
      return same_suit_cards[0]
    return None

  def _best_discard(self, game_view: GameState) -> Card:
    cards_in_hand = game_view.cards_in_hand[self.id]
    if self._smart_discard:
      preferred_discards = []
      played_cards = _get_played_cards(game_view)
      current_played_card = game_view.current_trick[self.id.opponent()]
      if current_played_card is not None:
        played_cards.append(current_played_card)
      for card in cards_in_hand:
        if card.suit == game_view.trump:
          continue
        if card.card_value == CardValue.JACK:
          ten = Card(card.suit, CardValue.TEN)
          ace = Card(card.suit, CardValue.ACE)
          king = Card(card.suit, CardValue.KING)
          queen = Card(card.suit, CardValue.QUEEN)
          if ten in cards_in_hand and \
              ace not in cards_in_hand and \
              ace not in played_cards and \
              king not in cards_in_hand and \
              queen not in cards_in_hand:
            continue
          preferred_discards.append(card)
        elif card.card_value in [CardValue.QUEEN, CardValue.KING]:
          marriage_pair = card.marriage_pair
          if marriage_pair in cards_in_hand:
            continue
          if marriage_pair not in played_cards:
            continue
          preferred_discards.append(card)
        else:
          continue
      if len(preferred_discards) > 0:
        remaining_suits = set(
          card.suit for card in self._get_remaining_cards(game_view))
        # TODO(ai): Maybe here picked the highest discard from an exhausted suit
        # if must not follow suit.
        preferred_discards.sort(key=_key_by_value_and_suit)
        for card in preferred_discards:
          if card.suit not in remaining_suits:
            return card
        return preferred_discards[0]
    card = self._smallest_non_trump_card(game_view)
    if card is not None:
      return card
    return min(cards_in_hand, key=_key_by_value_and_suit)
