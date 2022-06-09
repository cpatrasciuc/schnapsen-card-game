#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import abc
import copy
from typing import List

from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState
from model.game_state_validation import validate_game_states
from model.player_id import PlayerId
from model.player_pair import PlayerPair
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
  def execute(self, game_state: GameState) -> GameState:
    """
    Abstract method that returns a new game state object that represents the
    result of performing this player action on the game state provided as an
    argument. The input and output game states share as much info as possible.
    The action must be a legal action given the current state of the game.
    This can be checked with can_execute_on().
    """


class PlayCardAction(PlayerAction):
  """Plays a card from hand; it's used for both cards in a trick."""

  def __init__(self, player_id: PlayerId, card: Card):
    """
    Instantiates a new PlayCardAction.
    :param player_id: The player that will perform this action.
    :param card: The card to be played. Must be in the player's hand.
    """
    # TODO(optimization): Maybe add a constructor that takes the index of the
    #                     card in the player's hand.
    assert card is not None
    super().__init__(player_id)
    self._card = card

  @property
  def card(self) -> Card:
    return self._card

  def can_execute_on(self, game_state: GameState) -> bool:
    if game_state.next_player != self.player_id:
      return False
    if self._card not in game_state.cards_in_hand[self.player_id]:
      return False
    if not game_state.is_to_lead(self.player_id):
      if game_state.must_follow_suit():
        if not self._is_following_suit(game_state):
          return False
    return True

  def _is_following_suit(self, game_state: GameState) -> bool:
    """
    This method checks whether the card to be played follows suit.
    This means the player must:

    * Head the trick with a higher card of the same suit.
    * If unable to do so, they must discard a lower card of the same suit.
    * If both above are not possible, they must head the trick with a trump.
    * Only if they are unable to do the three above, they can discard a card of
      their choice.

    :return: True if the above conditions are met; False otherwise.
    """
    other = game_state.current_trick[self.player_id.opponent()]
    hand = game_state.cards_in_hand[self.player_id]
    if self._card.suit == other.suit:
      if self._card.card_value > other.card_value:
        return True
      for card in hand:
        if card.suit == other.suit and card.card_value > other.card_value:
          return False
    elif self._card.suit == game_state.trump:
      for card in hand:
        if card.suit == other.suit:
          return False
    else:
      for card in hand:
        if card.suit in (other.suit, game_state.trump):
          return False
    return True

  @validate_game_states
  def execute(self, game_state: GameState) -> GameState:
    """
    Plays self._card and updates the game_state accordingly.

    If the current player is to lead, it updates the current_trick, sets
    game_state.next_player to the opponent ID and returns.

    If the current player completes a trick, it checks who won the trick,
    it updates the won_tricks and trick_points for the winner, removes the cards
    from the players' hands and draws new cards from the talon if possible.
    While updating the trick_points it also takes into account any pending
    points from already announced marriages.
    At the end, it resets the current_trick and sets the next_player to the ID
    of the player that won the trick.
    """
    # pylint: disable=too-many-branches
    assert self.can_execute_on(game_state)
    new_game_state = copy.copy(game_state)

    if self.player_id == PlayerId.ONE:
      new_game_state.current_trick = PlayerPair(self._card,
                                                game_state.current_trick.two)
    else:
      new_game_state.current_trick = PlayerPair(game_state.current_trick.one,
                                                self._card)

    if new_game_state.current_trick[self.player_id.opponent()] is None:
      # The player lead the trick. Wait for the other player to play a card.
      new_game_state.next_player = self.player_id.opponent()
      return new_game_state

    # The player completes a trick. Check who won it.
    if self._card.wins(game_state.current_trick[self.player_id.opponent()],
                       game_state.trump):
      winner = self.player_id
    else:
      winner = self.player_id.opponent()

    # If it's the first trick won by this player, check if there are any
    # pending marriage points to be added.
    new_game_state.trick_points = PlayerPair(game_state.trick_points.one,
                                             game_state.trick_points.two)
    if new_game_state.trick_points[winner] == 0:
      for suit in new_game_state.marriage_suits[winner]:
        _add_marriage_points(new_game_state, winner, suit)

    # Update won_tricks and trick_points.
    if winner == PlayerId.ONE:
      new_game_state.won_tricks = PlayerPair(list(game_state.won_tricks.one),
                                             game_state.won_tricks.two)
      new_game_state.won_tricks.one.append(new_game_state.current_trick)
    else:
      new_game_state.won_tricks = PlayerPair(game_state.won_tricks.one,
                                             list(game_state.won_tricks.two))
      new_game_state.won_tricks.two.append(new_game_state.current_trick)
    new_game_state.trick_points[winner] += \
      new_game_state.current_trick.one.card_value
    new_game_state.trick_points[winner] += \
      new_game_state.current_trick.two.card_value

    # Remove the cards from players' hands.
    new_game_state.cards_in_hand = PlayerPair(
      list(game_state.cards_in_hand.one), list(game_state.cards_in_hand.two))
    for player_id in PlayerId:
      new_game_state.cards_in_hand[player_id].remove(
        new_game_state.current_trick[player_id])

    # In case the talon is closed and the player could not follow the lead
    # suit, reveal the lead-suit cards in the talon. This will allow an AI
    # player to know which cards cannot be in the opponent's hand, if it has to
    # make a decision in the future.
    lead_suit = new_game_state.current_trick[self.player_id.opponent()].suit
    played_suit = new_game_state.current_trick[self.player_id].suit
    if new_game_state.is_talon_closed and lead_suit != played_suit:
      new_game_state.talon = list(game_state.talon)
      for i, card in enumerate(new_game_state.talon):
        if card.suit == lead_suit:
          new_game_state.talon[i] = card.copy()
          new_game_state.talon[i].public = True
        # In case the player didn't follow suit and didn't play a trump card,
        # reveal all the trump cards in the talon as well.
        if card.suit == new_game_state.trump and \
            played_suit != new_game_state.trump:
          new_game_state.talon[i] = card.copy()
          new_game_state.talon[i].public = True

    # Clear current trick.
    new_game_state.current_trick = PlayerPair(None, None)

    # Maybe draw new cards from the talon.
    if len(game_state.talon) > 0 and not game_state.is_talon_closed:
      new_game_state.talon = list(game_state.talon)
      new_game_state.cards_in_hand[winner].append(new_game_state.talon.pop(0))
      if len(new_game_state.talon) > 0:
        new_game_state.cards_in_hand[winner.opponent()].append(
          new_game_state.talon.pop(0))
      else:
        new_game_state.cards_in_hand[winner.opponent()].append(
          new_game_state.trump_card)
        new_game_state.trump_card = None
    # TODO(ai): If the talon is closed and the opponent cannot play the same
    #  suit or trump, make the cards of that suit and trump public in the talon.

    # Update the next player
    new_game_state.next_player = winner

    return new_game_state

  def __eq__(self, other):
    if not isinstance(other, PlayCardAction):
      return False
    return self._player_id == other._player_id and self._card == other._card

  def __hash__(self):
    return hash((self._player_id, self._card))

  def __repr__(self):
    return f"PlayCardAction({self.player_id}, {self._card})"


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

  @property
  def card(self) -> Card:
    return self._card

  def can_execute_on(self, game_state: GameState) -> bool:
    if not game_state.is_to_lead(self.player_id):
      return False
    queen = Card(self._card.suit, CardValue.QUEEN)
    king = Card(self._card.suit, CardValue.KING)
    if queen not in game_state.cards_in_hand[self.player_id]:
      return False
    if king not in game_state.cards_in_hand[self.player_id]:
      return False
    return True

  @validate_game_states
  def execute(self, game_state: GameState) -> GameState:
    """
    Updates game_state to include the marriage announcement and plays
    self._card. The next player will be the opponent.

    If the player won any tricks so far, their trick_points get updated to
    reflect the value of the marriage. Otherwise, this update is delayed until
    they win a trick.
    """
    assert self.can_execute_on(game_state)
    new_game_state = copy.copy(game_state)
    player_cards = list(game_state.cards_in_hand[self.player_id])
    marriage_pair_index = player_cards.index(self._card.marriage_pair)
    player_cards[marriage_pair_index] = self._card.marriage_pair.copy()
    player_cards[marriage_pair_index].public = True
    if self.player_id == PlayerId.ONE:
      new_game_state.cards_in_hand = PlayerPair(player_cards,
                                                game_state.cards_in_hand.two)
      new_game_state.current_trick = PlayerPair(self._card,
                                                game_state.current_trick.two)
      new_game_state.marriage_suits = PlayerPair(
        list(game_state.marriage_suits.one), game_state.marriage_suits.two)
      new_game_state.marriage_suits.one.append(self._card.suit)
    else:
      new_game_state.cards_in_hand = PlayerPair(game_state.cards_in_hand.one,
                                                player_cards)
      new_game_state.current_trick = PlayerPair(game_state.current_trick.one,
                                                self._card)
      new_game_state.marriage_suits = PlayerPair(
        game_state.marriage_suits.one, list(game_state.marriage_suits.two))
      new_game_state.marriage_suits.two.append(self._card.suit)
    new_game_state.trick_points = PlayerPair(game_state.trick_points.one,
                                             game_state.trick_points.two)
    if new_game_state.trick_points[self.player_id] > 0:
      _add_marriage_points(new_game_state, self.player_id, self._card.suit)
    new_game_state.next_player = self.player_id.opponent()
    return new_game_state

  def __eq__(self, other):
    if not isinstance(other, AnnounceMarriageAction):
      return False
    return self._player_id == other._player_id and self._card == other._card

  def __hash__(self):
    return hash((self._player_id, self._card))

  def __repr__(self):
    return f"AnnounceMarriageAction({self.player_id}, {self._card})"


class ExchangeTrumpCardAction(PlayerAction):
  """Exchanges the trump jack in the player's hand with the trump card."""

  def can_execute_on(self, game_state: GameState) -> bool:
    if not game_state.is_to_lead(self.player_id):
      return False
    if game_state.is_talon_closed:
      return False
    if game_state.trump_card is None:
      return False
    trump_jack = Card(suit=game_state.trump, card_value=CardValue.JACK)
    if trump_jack not in game_state.cards_in_hand[self.player_id]:
      return False
    return True

  @validate_game_states
  def execute(self, game_state: GameState) -> GameState:
    assert self.can_execute_on(game_state)
    new_game_state = copy.copy(game_state)
    trump_jack = Card(suit=game_state.trump, card_value=CardValue.JACK)
    new_player_cards = [card for card in
                        game_state.cards_in_hand[self.player_id] if
                        card != trump_jack]
    new_player_cards.append(new_game_state.trump_card)
    if self.player_id == PlayerId.ONE:
      cards_in_hand = PlayerPair(new_player_cards, game_state.cards_in_hand.two)
    else:
      cards_in_hand = PlayerPair(game_state.cards_in_hand.one, new_player_cards)
    new_game_state.cards_in_hand = cards_in_hand
    new_game_state.trump_card = trump_jack
    new_game_state.trump_card.public = True
    return new_game_state

  def __eq__(self, other):
    if not isinstance(other, ExchangeTrumpCardAction):
      return False
    return self._player_id == other._player_id

  def __hash__(self):
    return hash(self._player_id)

  def __repr__(self):
    return f"ExchangeTrumpCardAction({self.player_id})"


class CloseTheTalonAction(PlayerAction):
  """The player who is to lead closes the talon."""

  def can_execute_on(self, game_state: GameState) -> bool:
    if not game_state.is_to_lead(self.player_id):
      return False
    if game_state.is_talon_closed:
      return False
    if len(game_state.talon) == 0:
      return False
    return True

  @validate_game_states
  def execute(self, game_state: GameState) -> GameState:
    assert self.can_execute_on(game_state)
    new_game_state = copy.copy(game_state)
    new_game_state.close_talon()
    return new_game_state

  def __eq__(self, other):
    if not isinstance(other, CloseTheTalonAction):
      return False
    return self._player_id == other._player_id

  def __hash__(self):
    return hash(self._player_id)

  def __repr__(self):
    return f"CloseTheTalonAction({self.player_id})"


def get_available_actions(game_state: GameState) -> List[PlayerAction]:
  """
  Returns a list of all the valid actions that can be performed in a given game
  state.
  """
  actions: List[PlayerAction] = []
  player_id = game_state.next_player
  is_to_lead = game_state.is_to_lead(player_id)
  for card in game_state.cards_in_hand[player_id]:
    # TODO(options): Allow Queen/King to be played without announcing marriage?
    if card.card_value in [CardValue.QUEEN, CardValue.KING] and is_to_lead:
      marriage = AnnounceMarriageAction(player_id, card)
      if marriage.can_execute_on(game_state):
        actions.append(marriage)
        continue
    play_card = PlayCardAction(player_id, card)
    if play_card.can_execute_on(game_state):
      actions.append(play_card)
  if is_to_lead:
    exchange_trump = ExchangeTrumpCardAction(player_id)
    if exchange_trump.can_execute_on(game_state):
      actions.append(exchange_trump)
    close_talon = CloseTheTalonAction(player_id)
    if close_talon.can_execute_on(game_state):
      actions.append(close_talon)
  return actions
