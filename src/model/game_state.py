#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import dataclasses
import random
from typing import List, Optional

from model.card import Card
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit


def get_game_points(
    trick_points: PlayerPair[int], won_last_trick: Optional[PlayerId] = None,
    closed_the_talon: Optional[PlayerId] = None,
    opp_points_when_talon_was_closed: Optional[int] = None) -> PlayerPair[int]:
  """
  Returns the game points won by each player at the end of a game. Only the
  winner will score points; the other player will score zero points.

  :param trick_points: The trick points for each player at the end of the game.
  :param won_last_trick: The player that won the last trick. Only needed if the
    talon was not closed (i.e., closed_the_talon is None).
  :param closed_the_talon: The player that closed the talon, if any.
  :param opp_points_when_talon_was_closed: If one player closed the talon, this
    argument should contain the points that their opponent had when the talon
    was closed.
  :return: A PlayerPair with the game points for each player. One entry will be
    zero.
  """
  assert closed_the_talon is not None or won_last_trick is not None

  def _get_game_points_won(opponent_points: int) -> int:
    if opponent_points >= 33:
      return 1
    if opponent_points > 0:
      return 2
    return 3

  if closed_the_talon is not None:
    assert opp_points_when_talon_was_closed is not None
    if trick_points[closed_the_talon] >= 66:
      winner = closed_the_talon
      points = _get_game_points_won(opp_points_when_talon_was_closed)
    else:
      winner = closed_the_talon.opponent()
      points = max(2, _get_game_points_won(opp_points_when_talon_was_closed))
  else:
    if trick_points.one >= 66:
      winner = PlayerId.ONE
      points = _get_game_points_won(trick_points.two)
    elif trick_points.two >= 66:
      winner = PlayerId.TWO
      points = _get_game_points_won(trick_points.one)
    else:
      assert trick_points.one + trick_points.two == 120
      winner = won_last_trick
      points = 1
  result = PlayerPair(0, 0)
  result[winner] = points
  return result


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
  won_tricks: PlayerPair[List[Trick]] = dataclasses.field(
    default_factory=lambda: PlayerPair([], []))

  # The suits for the marriages announced by each player.
  # The points corresponding to these marriages do not count if the player did
  # not win any trick.
  marriage_suits: PlayerPair[List[Suit]] = dataclasses.field(
    default_factory=lambda: PlayerPair([], []))

  # The points earned by each player so far. It does not include the points
  # scored by announcing marriages, if the player did not win any trick.
  trick_points: PlayerPair[int] = dataclasses.field(
    default_factory=lambda: PlayerPair(0, 0))

  # This stores the current, incomplete trick. This means we are waiting for
  # either one of both players to play card.
  current_trick: Trick = dataclasses.field(
    default_factory=lambda: Trick(None, None))

  def is_to_lead(self, player_id):
    """
    Checks if we are at the beginning of a trick and the given player is
    expected to make the next move.
    If a player is to lead, it can exchange the trump card or close the talon.
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
    trick points. Can only be called before a card is played by the player that
    is to lead.
    """
    if self.is_talon_closed:
      raise InvalidGameStateError("The talon is already closed")
    if len(self.talon) == 0:
      raise InvalidGameStateError("An empty talon cannot be closed")
    if not self.is_to_lead(self.next_player):
      raise InvalidGameStateError(
        "The talon can only be closed by the player that is to lead")
    self.player_that_closed_the_talon = self.next_player
    self.opponent_points_when_talon_was_closed = self.trick_points[
      self.player_that_closed_the_talon.opponent()]

  @staticmethod
  def new_game(dealer: PlayerId = PlayerId.ONE,
               random_seed: Optional[int] = None) -> "GameState":
    """
    Creates and returns a new game state representing the beginning of a new
    game.
    :param dealer: The PlayerID that deals the cards. The opponent will be
    to lead.
    :param random_seed: Seed to pass to the random number generator. Calls using
    the same seed will shuffle the deck in the same way. The game states can be
    different, depending on who is the dealer. If the dealer is the same the
    game states will be equal.
    :return: the new game state.
    """
    # TODO(refactor): Rename this to new().
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

  def is_game_over(self) -> bool:
    """
    Returns True if the game is over at this point in time. This means one
    player reached 66 points or there are no more cards to be played (i.e., all
    twenty cards were played or the talon was closed and all the cards from the
    player's hands were played).
    """
    # TODO(refactor): Make this a property, similar to Bummerl.is_over.
    target_score = 66
    if self.trick_points.one >= target_score:
      return True
    if self.trick_points.two >= target_score:
      return True
    if len(self.cards_in_hand.one) == 0:
      return True
    return False

  # TODO(refactor): Rename this to game_points() after game_points are moved.
  # TODO(refactor): Maybe make this a property.
  def score(self) -> PlayerPair[int]:
    """
    Returns the game points scored by each player after this game is over.
    Can only be called after the game is over.
    """
    assert self.is_game_over()
    return get_game_points(self.trick_points, self.next_player,
                           self.player_that_closed_the_talon,
                           self.opponent_points_when_talon_was_closed)
