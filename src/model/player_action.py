#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import abc

from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState
from model.player_id import PlayerId
from model.suit import Suit


def _add_marriage_points(game_state: GameState, player_id: PlayerId,
                         suit: Suit):
  marriage_value = 40 if suit == game_state.trump else 20
  game_state.trick_points[player_id] += marriage_value


class PlayerAction(abc.ABC):
  """
  Abstract base class for all possible player actions.

  The subclasses corresponding to each action are the following:

  * PlayCardAction - play a card from hand; it's used for both cards in a trick.
  * AnnounceMarriageAction - announce a marriage and play one of the two cards.
  * ExchangeTrumpCardAction - exchange the trump jack in hand for the trump
    card on the table.
  * CloseTheTalonAction - close the talon.
  """

  def __init__(self, player_id: PlayerId):
    """
    Instantiates a new player action.
    :param player_id: The player that will perform this action.
    """
    assert player_id is not None
    self._player_id = player_id

  @property
  def player_id(self):
    return self._player_id

  @abc.abstractmethod
  def can_execute_on(self, game_state: GameState) -> bool:
    """
    Abstract method that must return True if this action is a legal action, in
    the situation represented by the game state provided as an argument.
    """

  @abc.abstractmethod
  def execute(self, game_state: GameState):
    """
    Abstract method that must perform the necessary changes corresponding to
    performing this player action on the game state provided as an argument.
    The action must be a legal action given the currest state of the game.
    This can be checked with can_execute_on().
    """


class AnnounceMarriageAction(PlayerAction):
  """Announces a marriage and plays one of the two cards."""

  def __init__(self, player_id: PlayerId, card: Card):
    """
    Instantiates a new AnnounceMarriageAction.
    :param player_id: The player that will perform this action.
    :param card: One of the two cards in the marriage that will be played.
    """
    assert card.card_value in [CardValue.QUEEN, CardValue.KING]
    super().__init__(player_id)
    self._card = card

  def can_execute_on(self, game_state: GameState) -> bool:
    if not game_state.on_lead(self.player_id):
      return False
    queen = Card(self._card.suit, CardValue.QUEEN)
    king = Card(self._card.suit, CardValue.KING)
    if queen not in game_state.cards_in_hand[self.player_id]:
      return False
    if king not in game_state.cards_in_hand[self.player_id]:
      return False
    return True

  def execute(self, game_state: GameState):
    """
    Updates game_state to include the marriage announcement and plays
    self._card. The next player will be the opponent.

    If the player won any tricks so far, their trick_points get updated to
    reflect the value of the marriage. Otherwise, this update is delayed until
    they win a trick.
    """
    assert self.can_execute_on(game_state)
    game_state.current_trick[self.player_id] = self._card
    game_state.marriage_suits[self.player_id].append(self._card.suit)
    if game_state.trick_points[self.player_id] > 0:
      _add_marriage_points(game_state, self.player_id, self._card.suit)
    game_state.next_player = self.player_id.opponent()
    # TODO(game): Check if the player has more than 66 points and game is over.


class ExchangeTrumpCardAction(PlayerAction):
  """Exchanges the trump jack in the player's hand with the trump card."""

  def can_execute_on(self, game_state: GameState) -> bool:
    if not game_state.on_lead(self.player_id):
      return False
    if game_state.is_talon_closed:
      return False
    if game_state.trump_card is None:
      return False
    trump_jack = Card(suit=game_state.trump, card_value=CardValue.JACK)
    if trump_jack not in game_state.cards_in_hand[self.player_id]:
      return False
    return True

  def execute(self, game_state: GameState):
    assert self.can_execute_on(game_state)
    trump_jack = Card(suit=game_state.trump, card_value=CardValue.JACK)
    game_state.cards_in_hand[self.player_id].remove(trump_jack)
    game_state.cards_in_hand[self.player_id].append(game_state.trump_card)
    game_state.trump_card = trump_jack


class CloseTheTalonAction(PlayerAction):
  """The player who is to lead closes the talon."""

  def can_execute_on(self, game_state: GameState) -> bool:
    if not game_state.on_lead(self.player_id):
      return False
    if game_state.is_talon_closed:
      return False
    if len(game_state.talon) == 0:
      return False
    return True

  def execute(self, game_state: GameState):
    assert self.can_execute_on(game_state)
    game_state.close_talon()
