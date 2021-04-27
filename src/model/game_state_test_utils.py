#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState
from model.player_pair import PlayerPair
from model.suit import Suit


def get_game_state_for_tests() -> GameState:
  """
  Generates a valid game state that could be used as a starting point in tests.

  The game state is the following:
    * cards_in_hand: [Q♥, K♥, X♥, X♠, A♠], [Q♦, K♣, J♣, J♠, Q♣]
    * trump: ♣
    * trump_card: A♣
    * talon: [J♦]
    * won_tricks: [(K♠, Q♠), (A♦, K♦)], [(J♥, A♥), (X♦, X♣)]
    * marriage_suits: [], [♦]
    * trick_points: (22, 53)
    * game_points: (0, 0)
    * current_trick: (None, None)
  """
  cards_in_hand = PlayerPair(
    one=[Card(Suit.HEARTS, CardValue.QUEEN),
         Card(Suit.HEARTS, CardValue.KING),
         Card(Suit.HEARTS, CardValue.TEN),
         Card(Suit.SPADES, CardValue.TEN),
         Card(Suit.SPADES, CardValue.ACE)],
    two=[Card(Suit.DIAMONDS, CardValue.QUEEN),
         Card(Suit.CLUBS, CardValue.KING),
         Card(Suit.CLUBS, CardValue.JACK),
         Card(Suit.SPADES, CardValue.JACK),
         Card(Suit.CLUBS, CardValue.QUEEN)])
  trump_card = Card(Suit.CLUBS, CardValue.ACE)
  talon = [Card(Suit.DIAMONDS, CardValue.JACK)]
  won_tricks = PlayerPair(
    one=[PlayerPair(Card(Suit.SPADES, CardValue.KING),
                    Card(Suit.SPADES, CardValue.QUEEN)),
         PlayerPair(Card(Suit.DIAMONDS, CardValue.ACE),
                    Card(Suit.DIAMONDS, CardValue.KING))],
    two=[PlayerPair(Card(Suit.HEARTS, CardValue.JACK),
                    Card(Suit.HEARTS, CardValue.ACE)),
         PlayerPair(Card(Suit.DIAMONDS, CardValue.TEN),
                    Card(Suit.CLUBS, CardValue.TEN))])
  marriage_suits = PlayerPair(one=[], two=[Suit.DIAMONDS])
  trick_points = PlayerPair(one=22, two=53)
  game_points = PlayerPair(one=0, two=0)
  current_trick = PlayerPair(None, None)
  return GameState(cards_in_hand=cards_in_hand, trump=trump_card.suit,
                   trump_card=trump_card, talon=talon, won_tricks=won_tricks,
                   marriage_suits=marriage_suits, trick_points=trick_points,
                   game_points=game_points, current_trick=current_trick)
