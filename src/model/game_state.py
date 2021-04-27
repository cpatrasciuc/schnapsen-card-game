#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import dataclasses
from collections import Counter
from typing import List

from model.card import Card
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
  trump_card: Card

  # The remaining deck, placed face-down on the trump card.
  talon: List[Card]

  # The player expected to make the next move. It cannot be None.
  next_player: PlayerId = PlayerId.ONE

  # This is True if one of the players chose to close the talon.
  is_talon_closed: bool = False

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

  # pylint: disable=too-many-instance-attributes

  def on_lead(self, player_id):
    """
    Checks if we are at the beginning of a trick and the given player is
    expected to make the next move.
    If a player is on lead, it can exchange the trump card or close the talon.
    """
    # TODO(tests): add a test case for this.
    return self.next_player == player_id and self.current_trick == (None, None)

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

    # TODO: Add validation for won_tricks, marriage_suits, trick_points.

    self._validate_game_points()

  def _validate_game_points(self):
    for player_id in PlayerId:
      if not 0 <= self.game_points[player_id] < 7:
        raise InvalidGameStateError(
          "Game points should be between 0 and 6: %s has %d" % (
            player_id, self.game_points[player_id]))

  def _validate_talon(self):
    # TODO(tests): Add a test for this.
    if self.is_talon_closed and len(self.talon) == 0:
      raise InvalidGameStateError("An empty talon cannot be closed")

  def _validate_current_trick_and_next_player(self):
    if self.current_trick[self.next_player] is not None:
      raise InvalidGameStateError(
        "current_trick already contains a card for the next_player")

  def _validate_num_cards_in_hand(self):
    num_cards_player_one = len(self.cards_in_hand.one)
    if num_cards_player_one != len(self.cards_in_hand.two):
      raise InvalidGameStateError(
        "The players must have an equal number of cards in their hands")
    if num_cards_player_one > 5:
      raise InvalidGameStateError(
        "The players cannot have more than 5 cards in hand: %d" % (
          num_cards_player_one))
    if num_cards_player_one < 5:
      if (not self.is_talon_closed) and (len(self.talon) > 0):
        raise InvalidGameStateError(
          "The players should have 5 cards in hand: %d" % num_cards_player_one)

  def _verify_there_are_twenty_unique_cards(self):
    all_cards = [self.trump_card]
    all_cards += self.cards_in_hand.one + self.cards_in_hand.two
    all_cards += self.talon
    all_cards += self._get_played_cards()
    all_cards = [card for card in all_cards if card is not None]
    if len(all_cards) != 20:
      raise InvalidGameStateError(
        "Total number of cards must be 20, not %d" % len(all_cards))
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

  def _get_played_cards(self):
    return [card for trick in self.won_tricks.one + self.won_tricks.two for card
            in [trick.one, trick.two]]
