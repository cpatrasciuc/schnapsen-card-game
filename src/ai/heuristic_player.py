#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import dataclasses
import enum
import logging
import pprint
import random
from typing import List, Optional, Dict

from ai.random_player import RandomPlayer
from ai.utils import card_win_probabilities, prob_opp_has_more_trumps
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


class _Priority(enum.Enum):
  EXHAUSTED_SUITS = enum.auto()
  JACK_WITH_TEN_PROTECTION = enum.auto()
  JACK_WITHOUT_TEN_PROTECTION = enum.auto()
  QUEEN_OR_KING_WITHOUT_MARRIAGE_CHANCE = enum.auto()
  QUEEN_OR_KING_WITH_MARRIAGE_CHANCE = enum.auto()
  QUEEN_OR_KING_WITH_MARRIAGE_IN_HAND = enum.auto()
  OTHER_NON_TRUMP_CARDS = enum.auto()
  TRUMP_CARDS = enum.auto()


@dataclasses.dataclass(frozen=True)
class HeuristicPlayerOptions:
  priority_discard: bool = True
  can_close_talon: bool = True
  save_marriages: bool = True
  trump_for_marriage: bool = True
  avoid_direct_loss: bool = True
  trump_control: bool = True


# TODO(heuristic): When closing the talon/winning probs, count trumps from your
#   hand to counter remaining trumps. Then non-trump Ace or Ten could have
#   prob == 1.0.

# TODO(ai): Replace RandomPlayer with Player when the implementation in ready.
class HeuristicPlayer(RandomPlayer):
  """
  A player implementation based on the strategy outlined here:
  http://psellos.com/schnapsen/strategy.html
  """

  def __init__(self, player_id: PlayerId,
               options: Optional[HeuristicPlayerOptions] = None):
    """
    Creates a new HeuristicPlayer instance.
    :param player_id: The Id of the player in a game of Schnapsen (Player ONE or
    TWO).
    :param options: A set of parameters controlling the player's behavior.
    """
    super().__init__(player_id=player_id, force_trump_exchange=True,
                     never_close_talon=True, force_marriage_announcement=True)
    self._options = options or HeuristicPlayerOptions()

    # These variables cache the current state of the game across multiple
    # private method calls. They are refreshed every time a new player action is
    # requested, by calling _cache_game_state().
    self._marriage_suit = None
    self._remaining_cards = None
    self._my_cards = None
    self._my_trump_cards = None
    self._played_cards = None
    self._opp_card = None

  def _cache_game_state(self, game_view: GameState) -> None:
    self._opp_card = game_view.current_trick[self.id.opponent()]
    self._my_cards = game_view.cards_in_hand[self.id]
    self._my_trump_cards = [card for card in self._my_cards if
                            card.suit == game_view.trump]
    self._my_trump_cards.sort(key=_key_by_value_and_suit)
    self._played_cards = _get_played_cards(game_view)
    self._remaining_cards = self._get_remaining_cards(game_view)
    self._remaining_cards.sort(key=_key_by_value_and_suit)

  def request_next_action(self, game_view: GameState) -> PlayerAction:
    """Returns the action that this player chose to play next."""
    assert game_view.next_player == self.id, "Not my turn"
    self._cache_game_state(game_view)
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
      logging.debug("HeuristicPlayer: Storing marriage suit: %s",
                    action.card.suit)
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
      logging.debug("HeuristicPlayer: Announcing marriage for %s",
                    self._marriage_suit)
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
    logging.debug("HeuristicPlayer: Discarding %s", card)
    return PlayCardAction(self.id, card)

  def _play_winning_cards(self, game_view: GameState) -> Optional[PlayerAction]:
    """
    This method collects the list of cards that cannot be won by the opponent
    and computes a lower bound for the points that we would win if we play them.
    If this lower bound is enough to win the game, we play one of these cards;
    otherwise the method returns None.
    """
    winning_cards = {card: prob for card, prob in
                     self._get_winning_prob(game_view).items() if prob == 1.0}
    logging.debug("HeuristicPlayer: Card win probabilities:\n%s",
                  pprint.pformat(winning_cards))

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
    logging.debug(
      "HeuristicPlayer: Estimated points if winning cards are played: %s",
      points)

    if points < 66:
      logging.debug("HeuristicPlayer: Cannot get to 66 using winning cards.")
      return None

    # TODO(heuristic): Pick a random winning card.
    card = random.choice(list(winning_cards.keys()))
    logging.debug("HeuristicPlayer: Play winning card: %s", card)
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
    logging.debug("HeuristicPlayer: Card win probabilities:\n%s",
                  pprint.pformat(probabilities))
    max_prob = max(probabilities.values())
    logging.debug("HeuristicPlayer: The maximum winning probability is %.2f",
                  max_prob)
    if max_prob > 0:  # TODO: Set a threshold here.
      # If we have a marriage and the king has the same winning chance as the
      # maximum among all the other cards in hand, prefer to announce the
      # marriage.
      if self._marriage_suit is not None:
        king = Card(self._marriage_suit, CardValue.KING)
        king_prob = probabilities.get(king, 0)
        logging.debug(
          "HeuristicPlayer: %s probability: %.2f", king, king_prob)
        if king_prob == max_prob:
          logging.debug("HeuristicPlayer: Announcing the marriage for %s", king)
          return AnnounceMarriageAction(self.id, king)

      # Play a random card among the ones with the highest chance to win the
      # next trick.
      card_to_play = random.choice(
        [card for card, prob in probabilities.items() if prob == max_prob])
      logging.debug(
        "HeuristicPlayer: Play a card with the maximum win probability %s",
        card_to_play)
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
    return card_win_probabilities(self._my_cards,
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
    logging.debug("HeuristicPlayer: Playing %s", card)
    return PlayCardAction(self.id, card)

  def _not_on_lead_follow_suit(self, game_view: GameState) -> Card:
    assert self._opp_card is not None
    best_same_suit_card = self._best_same_suit_card(self._opp_card)
    if best_same_suit_card is not None:
      logging.debug("HeuristicPlayer: Best same suit card: %s",
                    best_same_suit_card)
      return self._avoid_breaking_marriage(best_same_suit_card)

    # No trump? Discard a small card.
    if len(self._my_trump_cards) == 0:
      logging.debug("HeuristicPlayer: No trumps. Discard a small card")
      return self._best_discard(game_view)

    # Find the best trump card to play.
    trump_card_to_play = self._best_winning_card(self._opp_card,
                                                 self._my_trump_cards)
    logging.debug("HeuristicPlayer: Tentative trump card: %s",
                  trump_card_to_play)
    return self._avoid_breaking_marriage(trump_card_to_play)

  def _avoid_breaking_marriage(self, card_to_play: Card) -> Card:
    """
    Returns card_to_play, if card_to_play is not part of a marriage. If it is
    part of a marriage, it returns the highest same suit card (it can still be
    card_to_play).
    """
    same_suit_cards = [card for card in self._my_cards if
                       card.suit == card_to_play.suit]
    if len(same_suit_cards) < 3:
      return card_to_play
    if card_to_play.card_value in [CardValue.KING, CardValue.QUEEN] and \
        card_to_play.marriage_pair in same_suit_cards:
      logging.debug("HeuristicPlayer: Trying to avoid breaking the %s marriage",
                    card_to_play.suit)
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
    assert self._opp_card is not None

    # If we can win with a same suit card, do it.
    best_same_suit_card = self._best_same_suit_card(self._opp_card)
    logging.debug("HeuristicPlayer: Best same suit card: %s",
                  best_same_suit_card)
    if best_same_suit_card is not None:
      if best_same_suit_card.wins(self._opp_card, game_view.trump):
        if best_same_suit_card.card_value == CardValue.KING and \
            best_same_suit_card.marriage_pair in self._my_cards:
          # Here we break a marriage to win a Jack from the same suit.
          if not self._options.save_marriages:
            return best_same_suit_card
          logging.debug("HeuristicPlayer: Saving the %s marriage",
                        best_same_suit_card.suit)
        else:
          return best_same_suit_card

    if self._opp_card.suit == game_view.trump or len(self._my_trump_cards) == 0:
      logging.debug("HeuristicPlayer: Cannot trump, so discard a small card")
      return self._best_discard(game_view)

    use_trump = False
    if self._opp_card.card_value in [CardValue.TEN, CardValue.ACE]:
      logging.debug("HeuristicPlayer: Should trump to win a Ten or an Ace")
      use_trump = True
    if not use_trump:
      use_trump = self._should_trump_for_marriage(game_view)
    if not use_trump:
      num_played_tricks = len(game_view.won_tricks.one) + \
                          len(game_view.won_tricks.two)
      if num_played_tricks == 3 and \
          self._can_exchange_trump_jack_for_marriage(game_view):
        logging.debug(
          "HeuristicPlayer: Should trump since it's the last chance to "
          "exchange the trump card for the trump marriage")
        use_trump = True

    trump_card = self._maybe_trump_for_the_win(game_view)
    if trump_card is not None:
      logging.debug(
        "HeuristicPlayer: Trump with %s since we can win from here",
        trump_card)
      return trump_card

    if use_trump:
      return self._win_with_trump(game_view)

    logging.debug("HeuristicPlayer: Discarding a small card")
    return self._best_discard(game_view)

  def _maybe_trump_for_the_win(self, game_view: GameState) -> Optional[Card]:
    """
    This method computes a lower bound of the points that can be surely won with
    the current cards in hand. If that is enough to win the game, returns the
    smallest trump card as the card to be played now, to win the current trick.
    If that is not the case, it returns None.
    """
    assert self._opp_card is not None
    if len(self._my_trump_cards) == 0:
      logging.debug("HeuristicPlayer: Cannot trump for the win; no trump cards")
      return None
    winning_cards = {card: prob for card, prob in
                     self._get_winning_prob(game_view).items() if prob == 1.0}
    logging.debug("HeuristicPlayer: Card win probabilities: %s",
                  pprint.pformat(winning_cards))
    unplayed_cards = [card for card in self._remaining_cards if
                      card != self._opp_card]
    min_trump_card = min(self._my_trump_cards)
    points = game_view.trick_points[self.id]
    points += self._opp_card.card_value + min_trump_card.card_value
    if min_trump_card in winning_cards:
      del winning_cards[min_trump_card]
    points += sum([card.card_value for card in winning_cards])
    points += sum(
      [card.card_value for card in unplayed_cards[:len(winning_cards)]])
    logging.debug("HeuristicPlayer: Lower bound of points that can be won: %s",
                  points)
    if points > 65:
      return min_trump_card
    return None

  def _should_trump_for_marriage(self, game_view: GameState) -> bool:
    """
    Returns True if the player should play a trump card to take the lead and
    announce a marriage that it already has in hand. If the marriage is the
    trump marriage, it also checks whether the player has a third trump card to
    use now.
    """
    if not self._options.trump_for_marriage:
      return False
    for suit in Suit:
      king = Card(suit, CardValue.KING)
      if king in self._my_cards and king.marriage_pair in self._my_cards:
        if suit != game_view.trump or len(self._my_trump_cards) > 2:
          return True
    return False

  def _win_with_trump(self, game_view: GameState) -> Card:
    """
    Returns the best trump card that should be used to win the current trick.
    """
    assert len(self._my_trump_cards) > 0
    trump_card = _highest_adjacent_card_in_hand(self._my_trump_cards[0],
                                                self._my_cards,
                                                self._played_cards)
    logging.debug("HeuristicPlayer: Tentative trump card: %s", trump_card)
    if self._can_exchange_trump_jack_for_marriage(game_view):
      logging.debug("HeuristicPlayer: Can exchange trump card for marriage")
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
    """
    Returns the best same suit card that can be used to win a trick against
    opp_card. If there is no such card, it returns the smallest card in hand
    having the same suit as opp_card. If there are no such cards, it returns
    None.
    """
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
    """
    Returns the best entry in winning_cards that should be used to win a trick
    against opp_card, by taking into account the cards that were already played.
    """
    assert len({card.suit for card in winning_cards}) == 1, winning_cards
    suit = winning_cards[0].suit
    all_cards_same_suit = [Card(suit, card_value) for card_value in CardValue]
    unplayed_cards_same_suit = [card for card in all_cards_same_suit if
                                card not in self._played_cards \
                                and card != opp_card and \
                                card not in self._my_cards]
    logging.debug("HeuristicPlayer: Unplayed %s cards: %s", suit,
                  unplayed_cards_same_suit)
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
    """
    Returns the best card in hand that should be discarded. This method is also
    used to get the leading card in the early stages of the game when we don't
    want to lead with high cards.
    """
    if self._options.priority_discard:
      return self._discard_with_priorities(game_view)
    card = self._my_smallest_non_trump_card(game_view)
    if card is not None:
      logging.debug(
        "HeuristicPlayer: Discarding one of the smallest non-trump cards: %s",
        card)
      return card
    card = min(self._my_cards, key=_key_by_value_and_suit)
    logging.debug("HeuristicPlayer: Discard the smallest card: %s", card)
    return card

  def _discard_with_priorities(self, game_view: GameState) -> Card:
    buckets = self._discard_buckets(game_view)
    logging.debug("HeuristicPlayer: Discard priority buckets:\n%s",
                  pprint.pformat(buckets))

    # Get the smallest card from the first non-empty bucket sorted by
    # priority.
    best_card = None
    for priority in _Priority:  # pragma: no cover
      cards = buckets[priority]
      if len(cards) > 0:
        cards.sort(key=_key_by_value_and_suit)
        best_card = cards[0]
        break

    # If the best card so far would lead to a direct loss, try to avoid it.
    if self._options.avoid_direct_loss and self._opp_card is not None:
      points = game_view.trick_points[self.id.opponent()]
      points += self._opp_card.card_value
      if points + best_card.card_value > 65:
        if len(self._my_trump_cards) > 0:
          return self._win_with_trump(game_view)
        return self._my_smallest_non_trump_card(game_view)

    return best_card

  def _discard_buckets(self, game_view) -> Dict[_Priority, List[Card]]:
    """
    Divides the cards in hand in the corresponding discard priority buckets and
    returns them as a dictionary.
    """
    buckets = {priority: [] for priority in _Priority}
    remaining_suits = set(card.suit for card in self._remaining_cards)
    played_cards = self._played_cards
    if self._opp_card is not None:
      played_cards = self._played_cards + [self._opp_card]
    # Place each card in its priority bucket.
    for card in self._my_cards:
      if card.suit == game_view.trump:
        buckets[_Priority.TRUMP_CARDS].append(card)
      elif card.suit not in remaining_suits:
        buckets[_Priority.EXHAUSTED_SUITS].append(card)
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
          buckets[_Priority.JACK_WITHOUT_TEN_PROTECTION].append(card)
        else:
          buckets[_Priority.JACK_WITH_TEN_PROTECTION].append(card)
      elif card.card_value in [CardValue.QUEEN, CardValue.KING]:
        marriage_pair = card.marriage_pair
        if marriage_pair in self._my_cards:
          buckets[_Priority.QUEEN_OR_KING_WITH_MARRIAGE_IN_HAND].append(card)
        elif marriage_pair not in played_cards:
          buckets[_Priority.QUEEN_OR_KING_WITH_MARRIAGE_CHANCE].append(card)
        else:
          buckets[_Priority.QUEEN_OR_KING_WITHOUT_MARRIAGE_CHANCE].append(card)
      else:
        buckets[_Priority.OTHER_NON_TRUMP_CARDS].append(card)
    return buckets

  def _should_close_talon(self, game_view: GameState) -> Optional[
    CloseTheTalonAction]:
    """
    Decides whether the player should close the talon. If yes, it returns the
    corresponding PlayerAction; otherwise it returns None.
    """
    if not self._options.can_close_talon:
      return None

    action = CloseTheTalonAction(self.id)
    if not action.can_execute_on(game_view):
      logging.debug("HeuristicPlayer: Cannot close the talon")
      return None

    # This is just an estimation. The two big flaws are:
    #   * If multiple cards have a probability of 1.0, it means that playing
    #     them as the next card will win the next trick. But it doesn't mean the
    #     probabilities will stay the same after this trick. For example, if we
    #     have the Ace and Ten from a non-trump suit, they might both have a
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
    # TODO(heuristic): This should call card_win_probabilities with
    #  must_follow_suit = True.
    probabilities = self._get_winning_prob(game_view)
    logging.debug("HeuristicPlayer: Card win probabilities: %s",
                  pprint.pformat(probabilities))
    points = game_view.trick_points[self.id]
    prob_and_cards = [(prob, card) for card, prob in probabilities.items()]
    prob_and_cards.sort(reverse=True)
    for i, prod_and_card in enumerate(prob_and_cards):
      prob, card = prod_and_card
      points += prob * (card.card_value + self._remaining_cards[i].card_value)
    logging.debug("HeuristicPlayer: Lower bound of points that can be won: %s",
                  points)
    if points > 65:
      logging.debug("HeuristicPlayer: Close the talon")
      return action
    return None

  def _maybe_trump_control(self, game_view: GameState) -> Optional[Card]:
    """
    If the probability that the opponent has more trump cards than us is greater
    than 0.5, play an non-trump Ace or a Ten, if available. The method returns
    the card that should be played. If it's not likely that the opponent has
    more trumps or we don't have any Ace or Ten, the method returns None.
    """
    if not self._options.trump_control:
      return None

    high_cards = [card for card in self._my_cards if
                  card.suit != game_view.trump
                  and card.card_value in [CardValue.TEN, CardValue.ACE]]
    if len(high_cards) == 0:
      logging.debug("HeuristicPlayer: No high cards")
      return None

    remaining_trumps = [card for card in self._remaining_cards if
                        card.suit == game_view.trump]
    if len(remaining_trumps) == 0:
      logging.debug(
        "HeuristicPLayer: No trump control since there are no trumps remaining")
      return None

    # If the opponent can win the game by trumping our high card, don't play it.
    max_remaining_trump = max(remaining_trumps)
    opp_points = game_view.trick_points[self.id.opponent()]
    if opp_points + max_remaining_trump.card_value + CardValue.ACE > 65:
      logging.debug(
        "HeuristicPlayer: No trump control because the opponent could win")
      return None

    fifth_trick_with_open_talon = not game_view.is_talon_closed and \
                                  len(game_view.talon) == 1
    probability = prob_opp_has_more_trumps(self._my_cards,
                                           game_view.cards_in_hand[
                                             self.id.opponent()],
                                           self._remaining_cards,
                                           game_view.trump,
                                           fifth_trick_with_open_talon)
    logging.debug(
      "HeuristicPlayer: Probability that the opponent has more trumps: %.2f",
      probability)
    if probability <= 0.5:
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
    assert False, "Should not reach this code"  # pragma: no cover
