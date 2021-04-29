#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import dataclasses
import random
from collections import Counter
from typing import List, Optional

from model.card import Card
from model.card_value import CardValue
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit

Trick = PlayerPair[Card]
"""
A pair of cards, one played by each player. One or both the cards can be None,
meaning that the trick is not yet completed and we are waiting for one or both
players to play their card.
"""


class InvalidGameStateError(Exception):
  """
  An exception thrown by GameState.validate() if an inconsistency is found.
  """


@dataclasses.dataclass
class GameState:
  """Stores all the information about a game at a specific point in time."""

  # pylint: disable=too-many-instance-attributes

  # The cards that each player holds in their hands. The lists are not sorted.
  # Each player can have at most 5 cards in their hand.
  cards_in_hand: PlayerPair[List[Card]]

  # The trump suit. If the trump_card is not None, this field must be equal with
  # the suit of the trump_card.
  trump: Suit

  # The face-up card in the middle of the table showing the trump suit.
  # If a player holds the Trump Jack, the player may exchange it for this card
  # before leading their next trick.
  # This is None iff the talon is exhausted.
  trump_card: Optional[Card]

  # The remaining deck, placed face-down on the trump card.
  # TODO(optimization): Maybe change this to collections.deque.
  talon: List[Card]

  # The player expected to make the next move. It cannot be None.
  next_player: PlayerId = PlayerId.ONE

  # If one player decided to close the talon, this field stores their player ID.
  # The opponent_points_when_talon_was_closed must also be set.
  # Use close_talon(), instead of setting this directly.
  player_that_closed_the_talon: Optional[PlayerId] = None

  # When a player decides to close the talon, this field stores their opponents'
  # trick points right before the deck was closed. This is needed to compute the
  # score at the end of this round.
  # This should only be set if player_that_closed_the_talon is not None.
  # Use close_talon(), instead of setting this directly.
  opponent_points_when_talon_was_closed: Optional[int] = None

  # The list of tricks won by each player so far.
  won_tricks: PlayerPair[List[Trick]] = PlayerPair([], [])

  # The suits for the marriages announced by each player.
  # The points corresponding to these marriages do not count if the player did
  # not win any trick.
  marriage_suits: PlayerPair[List[Suit]] = PlayerPair([], [])

  # The points earned by each player so far. It does not include the points
  # scored by announcing marriages, if the player did not win any trick.
  trick_points: PlayerPair[int] = PlayerPair(0, 0)

  # The Bummerl score. The first player to reach 7 points wins.
  # TODO: Maybe move this to a Bummerl class.
  game_points: PlayerPair[int] = PlayerPair(0, 0)

  # This stores the current, incomplete trick. This means we are waiting for
  # either one of both players to play card.
  current_trick: Trick = PlayerPair(None, None)

  def on_lead(self, player_id):
    """
    Checks if we are at the beginning of a trick and the given player is
    expected to make the next move.
    If a player is on lead, it can exchange the trump card or close the talon.
    """
    # TODO(tests): add a test case for this.
    return self.next_player == player_id and self.current_trick == PlayerPair(
      None, None)

  def must_follow_suit(self) -> bool:
    """
    Checks if players must follow-suit. This is true when the talon is empty or
    closed.
    """
    return self.is_talon_closed or len(self.talon) == 0

  @property
  def is_talon_closed(self) -> bool:
    return self.player_that_closed_the_talon is not None

  def close_talon(self) -> None:
    """
    Closes the talon. Saves the current player and their opponent's current
    trick points. Can only be called before a card is played by the on-lead
    player.
    """
    if self.is_talon_closed:
      raise InvalidGameStateError("The talon is already closed")
    if len(self.talon) == 0:
      raise InvalidGameStateError("An empty talon cannot be closed")
    if not self.on_lead(self.next_player):
      raise InvalidGameStateError(
        "The talon can only be closed by the on-lead player")
    self.player_that_closed_the_talon = self.next_player
    self.opponent_points_when_talon_was_closed = self.trick_points[
      self.player_that_closed_the_talon.opponent()]
    self._validate_talon()

  def validate(self) -> None:
    """
    Runs a series of check to validate the current game state (e.g., no
    duplicate cards, the trick points are correct based on won tricks and
    announced marriages).
    It does not perform type checks directly.
    :exception InvalidGameStateError if an inconsistency is found.
    """
    self._validate_trump_and_trump_card()
    self._verify_there_are_twenty_unique_cards()
    self._validate_num_cards_in_hand()
    self._validate_current_trick_and_next_player()
    self._validate_talon()
    self._validate_marriage_suits()
    self._validate_trick_points()
    self._validate_won_tricks()
    self._validate_game_points()

  def _validate_game_points(self):
    for player_id in PlayerId:
      if not 0 <= self.game_points[player_id] < 7:
        raise InvalidGameStateError(
          "Game points should be between 0 and 6: %s has %d" % (
            player_id, self.game_points[player_id]))

  def _validate_talon(self):
    if self.is_talon_closed and len(self.talon) == 0:
      raise InvalidGameStateError("An empty talon cannot be closed")
    player_is_set = self.player_that_closed_the_talon is not None
    points_are_set = self.opponent_points_when_talon_was_closed is not None
    if player_is_set != points_are_set:
      raise InvalidGameStateError(
        "player_that_closed_the_talon and opponent_points_when_talon_was_closed"
        " must be either both set or both None: "
        f"{self.player_that_closed_the_talon} "
        f"{self.opponent_points_when_talon_was_closed}")
    if player_is_set:
      if self.opponent_points_when_talon_was_closed > self.trick_points[
        self.player_that_closed_the_talon.opponent()]:
        raise InvalidGameStateError(
          "opponent_points_when_talon_was_closed is greater than the current "
          "value of trick_points for that player")

  def _validate_current_trick_and_next_player(self):
    if self.current_trick[self.next_player] is not None:
      raise InvalidGameStateError(
        f"current_trick already contains a card for {self.next_player}")

  def _validate_num_cards_in_hand(self):
    num_cards_player_one = len(self.cards_in_hand.one)
    if num_cards_player_one != len(self.cards_in_hand.two):
      raise InvalidGameStateError(
        "The players must have an equal number of cards in their hands: "
        + f"{num_cards_player_one} vs {len(self.cards_in_hand.two)}")
    if num_cards_player_one > 5:
      raise InvalidGameStateError(
        "The players cannot have more than 5 cards in hand: "
        + f"{num_cards_player_one}")
    if num_cards_player_one < 5:
      if (not self.is_talon_closed) and (len(self.talon) > 0):
        raise InvalidGameStateError(
          f"The players should have 5 cards in hand: {num_cards_player_one}")

  def _verify_there_are_twenty_unique_cards(self):
    all_cards = [self.trump_card]
    all_cards += self.cards_in_hand.one + self.cards_in_hand.two
    all_cards += self.talon
    all_cards += self._get_played_cards()
    all_cards = [card for card in all_cards if card is not None]
    if len(all_cards) != 20:
      raise InvalidGameStateError(
        f"Total number of cards must be 20, not {len(all_cards)}")
    duplicated_card_names = [str(card) for card, count in
                             Counter(all_cards).items() if count > 1]
    if len(duplicated_card_names) != 0:
      raise InvalidGameStateError(
        "Duplicated cards: %s" % ",".join(duplicated_card_names))

  def _validate_trump_and_trump_card(self):
    if self.trump is None:
      raise InvalidGameStateError("Trump suit cannot be None")
    if self.trump_card is not None:
      if self.trump_card.suit != self.trump:
        raise InvalidGameStateError("trump and trump_card.suit do not match")
    if self.trump_card is None and len(self.talon) > 0:
      raise InvalidGameStateError("trump_card is missing")

  def _validate_marriage_suits(self):
    marriages = self.marriage_suits.one + self.marriage_suits.two
    duplicated_marriages = [suit for suit, count in Counter(marriages).items()
                            if count > 1]
    if len(duplicated_marriages) > 0:
      raise InvalidGameStateError("Duplicated marriage suits: %s" % (
        ",".join(str(suit) for suit in duplicated_marriages)))

    # Check if at least one card from the marriage suits was played and that the
    # not-yet-played cards are in the player's hand.
    tricks = self.won_tricks.one + self.won_tricks.two
    for player_id in PlayerId:
      for marriage_suit in self.marriage_suits[player_id]:
        marriage = [Card(marriage_suit, CardValue.QUEEN),
                    Card(marriage_suit, CardValue.KING)]
        played_cards = [trick[player_id] for trick in tricks if
                        trick[player_id] in marriage]
        if len(played_cards) == 0:
          raise InvalidGameStateError(
            f"Marriage {marriage_suit} was announced, but no card was played")
        if len(played_cards) == 1:
          marriage.remove(played_cards[0])
          if marriage[0] not in self.cards_in_hand[player_id]:
            raise InvalidGameStateError(
              f"{player_id} announced marriage {marriage_suit} and played one" +
              " card. The other card is not in their hand.")

  def _validate_trick_points(self):
    expected_points = PlayerPair()
    for player_id in PlayerId:
      expected_points[player_id] = sum(
        [card.card_value for trick in self.won_tricks[player_id] for card in
         [trick.one, trick.two]])
      if expected_points[player_id] > 0:
        expected_points[player_id] += sum(
          [20 if suit != self.trump else 40 for suit in
           self.marriage_suits[player_id]])
    if expected_points != self.trick_points:
      raise InvalidGameStateError(
        f"Invalid trick points. Expected {expected_points}, "
        + f"actual {self.trick_points}")

  def _validate_won_tricks(self):
    for player_id in PlayerId:
      for trick in self.won_tricks[player_id]:
        if trick[player_id.opponent()].wins(trick[player_id], self.trump):
          raise InvalidGameStateError(
            f"{player_id} cannot win this trick: {trick.one}, {trick.two}")

  def _get_played_cards(self):
    return [card for trick in self.won_tricks.one + self.won_tricks.two for
            card in [trick.one, trick.two]]

  @staticmethod
  def new_game(dealer: PlayerId = PlayerId.ONE,
               random_seed: Optional[int] = None) -> "GameState":
    """
    Creates and returns a new game state representing the beginning of a new
    game.
    :param dealer: The PlayerID that deals the cards. The opponent will be
    on-lead.
    :param random_seed: Seed to pass to the random number generator. Calls using
    the same seed will shuffle the deck in the same way. The game states can be
    different, depending on who is the dealer. If the dealer is the same the
    game states will be equal.
    :return: the new game state.
    """
    deck = Card.get_all_cards()
    rng = random.Random(x=random_seed)
    rng.shuffle(deck)
    if dealer == PlayerId.ONE:
      cards_in_hand = PlayerPair(one=deck[:5], two=deck[5:10])
    else:
      cards_in_hand = PlayerPair(one=deck[5:10], two=deck[:5])
    trump_card = deck[10]
    return GameState(cards_in_hand=cards_in_hand, trump=trump_card.suit,
                     trump_card=trump_card, talon=deck[11:],
                     next_player=dealer.opponent())
