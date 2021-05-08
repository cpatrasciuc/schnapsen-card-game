#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from collections import Counter
from functools import wraps
from typing import List

from model.card import Card
from model.card_value import CardValue
from model.game_state import InvalidGameStateError, GameState
from model.player_id import PlayerId
from model.player_pair import PlayerPair


def _get_played_cards(game_state: GameState) -> List[Card]:
  return [card
          for trick in game_state.won_tricks.one + game_state.won_tricks.two
          for card in [trick.one, trick.two]]


def _validate_trump_and_trump_card(game_state: GameState) -> None:
  if game_state.trump is None:
    raise InvalidGameStateError("Trump suit cannot be None")
  if game_state.trump_card is not None:
    if game_state.trump_card.suit != game_state.trump:
      raise InvalidGameStateError("trump and trump_card.suit do not match")
  if game_state.trump_card is None and len(game_state.talon) > 0:
    raise InvalidGameStateError("trump_card is missing")


def _validate_talon(game_state: GameState) -> None:
  if game_state.is_talon_closed and len(game_state.talon) == 0:
    raise InvalidGameStateError("An empty talon cannot be closed")
  player_is_set = game_state.player_that_closed_the_talon is not None
  points_are_set = game_state.opponent_points_when_talon_was_closed is not None
  if player_is_set != points_are_set:
    raise InvalidGameStateError(
      "player_that_closed_the_talon and opponent_points_when_talon_was_closed"
      " must be either both set or both None: "
      f"{game_state.player_that_closed_the_talon} "
      f"{game_state.opponent_points_when_talon_was_closed}")
  if player_is_set:
    if game_state.opponent_points_when_talon_was_closed > \
        game_state.trick_points[
          game_state.player_that_closed_the_talon.opponent()]:
      raise InvalidGameStateError(
        "opponent_points_when_talon_was_closed is greater than the current "
        "value of trick_points for that player")


def _validate_current_trick_and_next_player(game_state: GameState) -> None:
  if game_state.current_trick[game_state.next_player] is not None:
    raise InvalidGameStateError(
      f"current_trick already contains a card for {game_state.next_player}")
  else:
    if game_state.is_to_lead(game_state.next_player):
      opp_tricks = len(game_state.won_tricks[game_state.next_player.opponent()])
      next_player_tricks = len(game_state.won_tricks[game_state.next_player])
      if next_player_tricks == 0 and opp_tricks > 0:
        raise InvalidGameStateError(
          "The player that is to lead did not win any trick")


def _validate_num_cards_in_hand(game_state: GameState) -> None:
  num_cards_player_one = len(game_state.cards_in_hand.one)
  if num_cards_player_one != len(game_state.cards_in_hand.two):
    raise InvalidGameStateError(
      "The players must have an equal number of cards in their hands: "
      + f"{num_cards_player_one} vs {len(game_state.cards_in_hand.two)}")
  if num_cards_player_one > 5:
    raise InvalidGameStateError(
      "The players cannot have more than 5 cards in hand: "
      + f"{num_cards_player_one}")
  if num_cards_player_one < 5:
    if (not game_state.is_talon_closed) and (len(game_state.talon) > 0):
      raise InvalidGameStateError(
        f"The players should have 5 cards in hand: {num_cards_player_one}")
    if game_state.is_talon_closed:
      num_tricks_played = len(game_state.won_tricks.one) + len(
        game_state.won_tricks.two)
      min_cards_in_hand = 5 - num_tricks_played
      if num_cards_player_one < min_cards_in_hand:
        raise InvalidGameStateError(
          f"Players must have at least {min_cards_in_hand} cards in hand, not" +
          f" {num_cards_player_one}")


def _verify_there_are_twenty_unique_cards(game_state: GameState) -> None:
  all_cards = [game_state.trump_card]
  all_cards += game_state.cards_in_hand.one + game_state.cards_in_hand.two
  all_cards += game_state.talon
  all_cards += _get_played_cards(game_state)
  all_cards = [card for card in all_cards if card is not None]
  if len(all_cards) != 20:
    raise InvalidGameStateError(
      f"Total number of cards must be 20, not {len(all_cards)}")
  duplicated_card_names = [str(card) for card, count in
                           Counter(all_cards).items() if count > 1]
  if len(duplicated_card_names) != 0:
    raise InvalidGameStateError(
      "Duplicated cards: %s" % ",".join(duplicated_card_names))


def _validate_marriage_suits(game_state: GameState) -> None:
  marriages = game_state.marriage_suits.one + game_state.marriage_suits.two
  duplicated_marriages = [suit for suit, count in Counter(marriages).items()
                          if count > 1]
  if len(duplicated_marriages) > 0:
    raise InvalidGameStateError("Duplicated marriage suits: %s" % (
      ",".join(str(suit) for suit in duplicated_marriages)))

  # Check if at least one card from the marriage suits was played and that the
  # not-yet-played cards are in the player's hand.
  tricks = game_state.won_tricks.one + game_state.won_tricks.two
  for player_id in PlayerId:
    for marriage_suit in game_state.marriage_suits[player_id]:
      marriage = [Card(marriage_suit, CardValue.QUEEN),
                  Card(marriage_suit, CardValue.KING)]
      played_cards = [trick[player_id] for trick in tricks if
                      trick[player_id] in marriage]
      if game_state.current_trick[player_id] in marriage:
        played_cards.append(game_state.current_trick[player_id])
      if len(played_cards) == 0:
        raise InvalidGameStateError(
          f"Marriage {marriage_suit} was announced, but no card was played")
      if len(played_cards) == 1:
        marriage.remove(played_cards[0])
        if marriage[0] not in game_state.cards_in_hand[player_id]:
          raise InvalidGameStateError(
            f"{player_id} announced marriage {marriage_suit} and played one" +
            " card. The other card is not in their hand.")


def _validate_trick_points(game_state: GameState) -> None:
  expected_points = PlayerPair()
  for player_id in PlayerId:
    expected_points[player_id] = sum(
      [card.card_value for trick in game_state.won_tricks[player_id] for card in
       [trick.one, trick.two]])
    if expected_points[player_id] > 0:
      expected_points[player_id] += sum(
        [20 if suit != game_state.trump else 40 for suit in
         game_state.marriage_suits[player_id]])
  if expected_points != game_state.trick_points:
    raise InvalidGameStateError(
      f"Invalid trick points. Expected {expected_points}, "
      + f"actual {game_state.trick_points}")


def _validate_won_tricks(game_state: GameState) -> None:
  for player_id in PlayerId:
    for trick in game_state.won_tricks[player_id]:
      if trick[player_id.opponent()].wins(trick[player_id], game_state.trump):
        raise InvalidGameStateError(
          f"{player_id} cannot win this trick: {trick.one}, {trick.two}")


def validate(game_state: GameState) -> None:
  """
  Runs a series of checks to validate the current game state (e.g., no
  duplicate cards, the trick points are correct based on won tricks and
  announced marriages).
  It does not perform type checks directly.
  It does not perform complex checks. For example, it doesn't verify that the
  current state can be obtained by performing a series of legal moves starting
  from a valid new-game state.
  :exception InvalidGameStateError if an inconsistency is found.
  """
  _validate_trump_and_trump_card(game_state)
  _verify_there_are_twenty_unique_cards(game_state)
  _validate_num_cards_in_hand(game_state)
  _validate_current_trick_and_next_player(game_state)
  _validate_talon(game_state)
  _validate_marriage_suits(game_state)
  _validate_trick_points(game_state)
  _validate_won_tricks(game_state)


class GameStateValidator:
  """
  Context manager that calls validate() on a given GameState instance when
  entering and exiting the context. It is useful to ensure that a set of manual
  changes performed on a valid GameState instance leave it in a valid state.

  ::
    game_state = ... # game_state is valid here
    with GameStateValidator(game_state):
      # game_state must be valid here
      do_manual_changes(game_state)
      # game_state might not be valid here
      do_more_manual_changes(game_state)
      # game_state must be valid here
    # game_state is valid here
  """

  def __init__(self, game_state: GameState):
    assert game_state is not None
    self._game_state = game_state

  def __enter__(self) -> None:
    validate(self._game_state)

  def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
    validate(self._game_state)
    return False


# noinspection PyUnreachableCode
def validate_game_states(func):
  """
  Function decorator that calls validate() on all GameState arguments passed to
  the decorated function before and after the decorated function is called.
  It has no effect if __debug__ is False.
  """
  if __debug__:
    @wraps(func)  # pragma: no cover
    def wrapper(*args, **kwds):
      game_states = []
      game_states += [arg for arg in args if isinstance(arg, GameState)]
      game_states += [value for name, value in kwds.items() if
                      isinstance(value, GameState)]
      for game_state in game_states:
        validate(game_state)
      return_value = func(*args, **kwds)
      for game_state in game_states:
        validate(game_state)
      return return_value

    return wrapper
  return func  # pragma: no cover
