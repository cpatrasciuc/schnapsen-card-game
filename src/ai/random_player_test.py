#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from typing import Set

from ai.random_player import RandomPlayer
from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState
from model.game_state_test_utils import get_game_state_for_tests, \
  get_game_state_with_empty_talon_for_tests
from model.game_state_validation import GameStateValidator
from model.player_action import ExchangeTrumpCardAction, \
  AnnounceMarriageAction, PlayerAction, PlayCardAction, CloseTheTalonAction
from model.player_id import PlayerId
from model.suit import Suit


def _get_action_set(player: RandomPlayer, game_state: GameState,
                    num_iter: int = 1000) -> Set[PlayerAction]:
  return {player.request_next_action(game_state) for _ in range(num_iter)}


class RandomPlayerTest(unittest.TestCase):
  def test_default_random_player(self):
    game_state = get_game_state_for_tests()
    player = RandomPlayer(PlayerId.ONE)
    self.assertEqual(
      {AnnounceMarriageAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.QUEEN)),
       AnnounceMarriageAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.KING)),
       PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.TEN)),
       PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)),
       PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)),
       CloseTheTalonAction(PlayerId.ONE)},
      _get_action_set(player, game_state))

  def test_never_close_talon(self):
    game_state = get_game_state_for_tests()
    player = RandomPlayer(PlayerId.ONE, never_close_talon=True)
    self.assertEqual(
      {AnnounceMarriageAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.QUEEN)),
       AnnounceMarriageAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.KING)),
       PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.TEN)),
       PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)),
       PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE))},
      _get_action_set(player, game_state))

  def test_force_trump_exchange(self):
    game_state = get_game_state_for_tests()

    # No trump jack.
    player = RandomPlayer(PlayerId.ONE, force_trump_exchange=True)
    self.assertEqual(
      {AnnounceMarriageAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.QUEEN)),
       AnnounceMarriageAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.KING)),
       PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.TEN)),
       PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)),
       PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.ACE)),
       CloseTheTalonAction(PlayerId.ONE)},
      _get_action_set(player, game_state))

    # Has trump jack. Can exchange trump.
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    player = RandomPlayer(PlayerId.TWO, force_trump_exchange=True)
    self.assertEqual({ExchangeTrumpCardAction(PlayerId.TWO)},
                     _get_action_set(player, game_state))
    player = RandomPlayer(PlayerId.TWO, force_trump_exchange=True,
                          force_marriage_announcement=True)
    self.assertEqual({ExchangeTrumpCardAction(PlayerId.TWO)},
                     _get_action_set(player, game_state))

  def test_force_marriage_announcement(self):
    game_state = get_game_state_for_tests()
    player = RandomPlayer(PlayerId.ONE, force_marriage_announcement=True)

    # Player has a non trump marriage.
    king_hearts = Card(Suit.HEARTS, CardValue.KING)
    queen_hearts = king_hearts.marriage_pair
    self.assertEqual({AnnounceMarriageAction(PlayerId.ONE, king_hearts),
                      AnnounceMarriageAction(PlayerId.ONE, queen_hearts)},
                     _get_action_set(player, game_state))

    # Player has a trump marriage.
    with GameStateValidator(game_state):
      game_state.next_player = PlayerId.TWO
    player = RandomPlayer(PlayerId.TWO, force_marriage_announcement=True)
    king_clubs = Card(Suit.CLUBS, CardValue.KING)
    queen_clubs = king_clubs.marriage_pair
    self.assertEqual({AnnounceMarriageAction(PlayerId.TWO, king_clubs),
                      AnnounceMarriageAction(PlayerId.TWO, queen_clubs)},
                     _get_action_set(player, game_state))

    # Player has a trump and a non-trump marriage.
    with GameStateValidator(game_state):
      queen_hearts = game_state.cards_in_hand.one.pop(0)
      king_hearts = game_state.cards_in_hand.one.pop(0)
      jack_clubs = game_state.cards_in_hand.two.pop(2)
      jack_spades = game_state.cards_in_hand.two.pop(2)
      game_state.cards_in_hand.one.extend([jack_clubs, jack_spades])
      game_state.cards_in_hand.two.extend([queen_hearts, king_hearts])
    self.assertEqual({AnnounceMarriageAction(PlayerId.TWO, king_clubs),
                      AnnounceMarriageAction(PlayerId.TWO, queen_clubs)},
                     _get_action_set(player, game_state))

    # Player has two non-trump marriages.
    with GameStateValidator(game_state):
      jack_spades = game_state.cards_in_hand.one.pop()
      ace_clubs = game_state.trump_card
      game_state.trump_card = jack_spades
      game_state.trump = jack_spades.suit
      jack_spades.public = True
      game_state.cards_in_hand.one.append(ace_clubs)
    self.assertEqual({AnnounceMarriageAction(PlayerId.TWO, king_clubs),
                      AnnounceMarriageAction(PlayerId.TWO, queen_clubs),
                      AnnounceMarriageAction(PlayerId.TWO, king_hearts),
                      AnnounceMarriageAction(PlayerId.TWO, queen_hearts)},
                     _get_action_set(player, game_state))

    # No marriage.
    game_state = get_game_state_with_empty_talon_for_tests()
    player = RandomPlayer(PlayerId.ONE, force_marriage_announcement=True)
    self.assertEqual(
      {PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.ACE)),
       PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.KING)),
       PlayCardAction(PlayerId.ONE, Card(Suit.HEARTS, CardValue.TEN)),
       PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN))},
      _get_action_set(player, game_state))
