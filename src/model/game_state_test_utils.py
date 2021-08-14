#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState
from model.game_state_validation import GameStateValidator
from model.player_action import PlayCardAction, CloseTheTalonAction
from model.player_id import PlayerId
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
    * next_player: PlayerId.ONE
    * won_tricks: [(K♠, Q♠), (A♦, K♦)], [(J♥, A♥), (X♦, X♣)]
    * marriage_suits: [], [♦]
    * trick_points: (22, 53)
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
  current_trick = PlayerPair(None, None)
  return GameState(cards_in_hand=cards_in_hand, trump=trump_card.suit,
                   trump_card=trump_card, talon=talon, won_tricks=won_tricks,
                   marriage_suits=marriage_suits, trick_points=trick_points,
                   current_trick=current_trick)


def get_game_state_with_empty_talon_for_tests() -> GameState:
  """
  Generates a valid game state in which more than five tricks have been played
  and the talon is empty. This is meant to be used as a starting point for
  tests.

  The game state is the following:
    * cards_in_hand: [A♣, K♥, X♥, X♠], [J♦, K♣, J♣, Q♣]
    * trump: ♣
    * trump_card: None
    * talon: []
    * next_player: PlayerId.ONE
    * won_tricks: [(K♠, Q♠), (A♦, K♦), (A♠, J♠)],
                  [(J♥, A♥), (X♦, X♣), (Q♥, Q♦)]
    * marriage_suits: [], [♦]
    * trick_points: (35, 59)
    * current_trick: (None, None)
  """
  cards_in_hand = PlayerPair(
    one=[Card(Suit.CLUBS, CardValue.ACE),
         Card(Suit.HEARTS, CardValue.KING),
         Card(Suit.HEARTS, CardValue.TEN),
         Card(Suit.SPADES, CardValue.TEN)],
    two=[Card(Suit.DIAMONDS, CardValue.JACK),
         Card(Suit.CLUBS, CardValue.KING),
         Card(Suit.CLUBS, CardValue.JACK),
         Card(Suit.CLUBS, CardValue.QUEEN)])
  talon = []
  won_tricks = PlayerPair(
    one=[PlayerPair(Card(Suit.SPADES, CardValue.KING),
                    Card(Suit.SPADES, CardValue.QUEEN)),
         PlayerPair(Card(Suit.DIAMONDS, CardValue.ACE),
                    Card(Suit.DIAMONDS, CardValue.KING)),
         PlayerPair(Card(Suit.SPADES, CardValue.ACE),
                    Card(Suit.SPADES, CardValue.JACK))],
    two=[PlayerPair(Card(Suit.HEARTS, CardValue.JACK),
                    Card(Suit.HEARTS, CardValue.ACE)),
         PlayerPair(Card(Suit.DIAMONDS, CardValue.TEN),
                    Card(Suit.CLUBS, CardValue.TEN)),
         PlayerPair(Card(Suit.HEARTS, CardValue.QUEEN),
                    Card(Suit.DIAMONDS, CardValue.QUEEN))])
  marriage_suits = PlayerPair(one=[], two=[Suit.DIAMONDS])
  trick_points = PlayerPair(one=35, two=59)
  current_trick = PlayerPair(None, None)
  return GameState(cards_in_hand=cards_in_hand, trump=Suit.CLUBS,
                   trump_card=None, talon=talon, won_tricks=won_tricks,
                   marriage_suits=marriage_suits, trick_points=trick_points,
                   current_trick=current_trick)


def get_game_state_with_all_tricks_played() -> GameState:
  """
  Generates a valid game state in which all the tricks were played and no player
  could reach 66 points.

  The game state is the following:
    * cards_in_hand: [], []
    * trump: ♣
    * trump_card: None
    * talon: []
    * next_player: PlayerId.ONE
    * won_tricks: [(K♠, Q♠), (A♠, X♥), (K♣, Q♣), (A♣, X♣), (J♣, J♠)],
                  [(Q♥, K♥), (X♥, A♥), (Q♦, K♦), (X♦, A♦), (J♥, J♦)]
    * marriage_suits: [], []
    * trick_points: (60, 60)
    * current_trick: (None, None)
  """
  cards_in_hand = PlayerPair([], [])
  talon = []
  won_tricks = PlayerPair(
    one=[PlayerPair(Card(Suit.SPADES, CardValue.KING),
                    Card(Suit.SPADES, CardValue.QUEEN)),
         PlayerPair(Card(Suit.SPADES, CardValue.ACE),
                    Card(Suit.SPADES, CardValue.TEN)),
         PlayerPair(Card(Suit.CLUBS, CardValue.KING),
                    Card(Suit.CLUBS, CardValue.QUEEN)),
         PlayerPair(Card(Suit.CLUBS, CardValue.ACE),
                    Card(Suit.CLUBS, CardValue.TEN)),
         PlayerPair(Card(Suit.CLUBS, CardValue.JACK),
                    Card(Suit.SPADES, CardValue.JACK))],
    two=[PlayerPair(Card(Suit.HEARTS, CardValue.QUEEN),
                    Card(Suit.HEARTS, CardValue.KING)),
         PlayerPair(Card(Suit.HEARTS, CardValue.TEN),
                    Card(Suit.HEARTS, CardValue.ACE)),
         PlayerPair(Card(Suit.DIAMONDS, CardValue.QUEEN),
                    Card(Suit.DIAMONDS, CardValue.KING)),
         PlayerPair(Card(Suit.DIAMONDS, CardValue.TEN),
                    Card(Suit.DIAMONDS, CardValue.ACE)),
         PlayerPair(Card(Suit.DIAMONDS, CardValue.JACK),
                    Card(Suit.HEARTS, CardValue.JACK))])
  marriage_suits = PlayerPair([], [])
  trick_points = PlayerPair(one=60, two=60)
  current_trick = PlayerPair(None, None)
  return GameState(cards_in_hand=cards_in_hand, trump=Suit.CLUBS,
                   trump_card=None, talon=talon, won_tricks=won_tricks,
                   marriage_suits=marriage_suits, trick_points=trick_points,
                   current_trick=current_trick)


def get_game_state_for_you_first_no_you_first_puzzle() -> GameState:
  """
  Generates a game state for the scenario described here:
  http://psellos.com/schnapsen/blog/2012/03/005-first.html

  The game state is the following:
    * cards_in_hand: [K♠, Q♥, A♥, Q♣, J♣], [X♥, J♥, A♦, Q♦, J♦]
    * trump: ♦
    * trump_card: None
    * talon: []
    * next_player: PlayerId.ONE
    * won_tricks: [(K♣, Q♠), (K♦, A♣), (A♠, X♠)], [(J♠, K♥), (X♣, X♦)]
    * marriage_suits: [], []
    * trick_points: (43, 26)
    * current_trick: (None, None)
  """
  cards_in_hand = PlayerPair(
    one=[Card(Suit.SPADES, CardValue.KING),
         Card(Suit.HEARTS, CardValue.QUEEN),
         Card(Suit.HEARTS, CardValue.ACE),
         Card(Suit.CLUBS, CardValue.QUEEN),
         Card(Suit.CLUBS, CardValue.JACK)],
    two=[Card(Suit.HEARTS, CardValue.TEN),
         Card(Suit.HEARTS, CardValue.JACK),
         Card(Suit.DIAMONDS, CardValue.ACE),
         Card(Suit.DIAMONDS, CardValue.QUEEN),
         Card(Suit.DIAMONDS, CardValue.JACK)])
  won_tricks = PlayerPair(
    one=[PlayerPair(Card(Suit.CLUBS, CardValue.KING),
                    Card(Suit.SPADES, CardValue.QUEEN)),
         PlayerPair(Card(Suit.DIAMONDS, CardValue.KING),
                    Card(Suit.CLUBS, CardValue.ACE)),
         PlayerPair(Card(Suit.SPADES, CardValue.ACE),
                    Card(Suit.SPADES, CardValue.TEN))],
    two=[PlayerPair(Card(Suit.SPADES, CardValue.JACK),
                    Card(Suit.HEARTS, CardValue.KING)),
         PlayerPair(Card(Suit.CLUBS, CardValue.TEN),
                    Card(Suit.DIAMONDS, CardValue.TEN))])
  trick_points = PlayerPair(one=43, two=26)
  current_trick = PlayerPair(None, None)
  return GameState(cards_in_hand=cards_in_hand, trump=Suit.DIAMONDS,
                   trump_card=None, talon=[], won_tricks=won_tricks,
                   trick_points=trick_points, current_trick=current_trick)


def get_game_state_for_elimination_play_puzzle() -> GameState:
  """
  Generates a game state for the scenario described here:
  http://psellos.com/schnapsen/blog/2012/04/006-elimination.html

  The game state is the following:
    * cards_in_hand: [K♠, Q♥, A♥, Q♣, J♣], [X♥, J♥, A♦, J♠, K♣]
    * trump: ♦
    * trump_card: None
    * talon: []
    * next_player: PlayerId.ONE
    * won_tricks: [(Q♦, Q♠), (K♦, A♣), (J♦, A♠)], [(X♠, K♥), (X♣, X♦)]
    * marriage_suits: [], []
    * trick_points: (34, 34)
    * current_trick: (None, None)
  """
  cards_in_hand = PlayerPair(
    one=[Card(Suit.SPADES, CardValue.KING),
         Card(Suit.HEARTS, CardValue.QUEEN),
         Card(Suit.HEARTS, CardValue.ACE),
         Card(Suit.CLUBS, CardValue.QUEEN),
         Card(Suit.CLUBS, CardValue.JACK)],
    two=[Card(Suit.HEARTS, CardValue.TEN),
         Card(Suit.HEARTS, CardValue.JACK),
         Card(Suit.DIAMONDS, CardValue.ACE),
         Card(Suit.SPADES, CardValue.JACK),
         Card(Suit.CLUBS, CardValue.KING)])
  won_tricks = PlayerPair(
    one=[PlayerPair(Card(Suit.DIAMONDS, CardValue.QUEEN),
                    Card(Suit.SPADES, CardValue.QUEEN)),
         PlayerPair(Card(Suit.DIAMONDS, CardValue.KING),
                    Card(Suit.CLUBS, CardValue.ACE)),
         PlayerPair(Card(Suit.DIAMONDS, CardValue.JACK),
                    Card(Suit.SPADES, CardValue.ACE))],
    two=[PlayerPair(Card(Suit.SPADES, CardValue.TEN),
                    Card(Suit.HEARTS, CardValue.KING)),
         PlayerPair(Card(Suit.CLUBS, CardValue.TEN),
                    Card(Suit.DIAMONDS, CardValue.TEN))])
  trick_points = PlayerPair(one=34, two=34)
  current_trick = PlayerPair(None, None)
  return GameState(cards_in_hand=cards_in_hand, trump=Suit.DIAMONDS,
                   trump_card=None, talon=[], won_tricks=won_tricks,
                   trick_points=trick_points, current_trick=current_trick)


def get_game_state_for_playing_to_win_the_last_trick_puzzle() -> GameState:
  """
  Generates a game state for the scenario described here:
  http://psellos.com/schnapsen/blog/2019/12/144-last.html

  The game state is the following:
    * cards_in_hand: [K♠, X♥, K♣, X♦, Q♦], [J♥, J♣, A♦, K♦, J♦]
    * trump: ♣
    * trump_card: None
    * talon: []
    * next_player: PlayerId.ONE
    * won_tricks: [(A♥, Q♠), (A♣, A♠)], [(J♠, X♠), (Q♥, X♣), (K♥, Q♣)]
    * marriage_suits: [], []
    * trick_points: (36, 32)
    * current_trick: (None, None)
  """
  cards_in_hand = PlayerPair(
    one=[Card(Suit.SPADES, CardValue.KING),
         Card(Suit.HEARTS, CardValue.TEN),
         Card(Suit.CLUBS, CardValue.KING),
         Card(Suit.DIAMONDS, CardValue.TEN),
         Card(Suit.DIAMONDS, CardValue.QUEEN)],
    two=[Card(Suit.HEARTS, CardValue.JACK),
         Card(Suit.CLUBS, CardValue.JACK),
         Card(Suit.DIAMONDS, CardValue.ACE),
         Card(Suit.DIAMONDS, CardValue.KING),
         Card(Suit.DIAMONDS, CardValue.JACK)])
  won_tricks = PlayerPair(
    one=[PlayerPair(Card(Suit.HEARTS, CardValue.ACE),
                    Card(Suit.SPADES, CardValue.QUEEN)),
         PlayerPair(Card(Suit.CLUBS, CardValue.ACE),
                    Card(Suit.SPADES, CardValue.ACE))],
    two=[PlayerPair(Card(Suit.SPADES, CardValue.JACK),
                    Card(Suit.SPADES, CardValue.TEN)),
         PlayerPair(Card(Suit.HEARTS, CardValue.QUEEN),
                    Card(Suit.CLUBS, CardValue.TEN)),
         PlayerPair(Card(Suit.HEARTS, CardValue.KING),
                    Card(Suit.CLUBS, CardValue.QUEEN))])
  trick_points = PlayerPair(one=36, two=32)
  current_trick = PlayerPair(None, None)
  return GameState(cards_in_hand=cards_in_hand, trump=Suit.CLUBS,
                   trump_card=None, talon=[], won_tricks=won_tricks,
                   trick_points=trick_points, current_trick=current_trick)


def get_game_state_for_tempo_puzzle() -> GameState:
  """
  Generates a game state for the scenario described here:
  http://psellos.com/schnapsen/blog/2012/08/027-tempo.html

  The game state is the following:
    * cards_in_hand: [J♠, Q♥, A♣, K♣, J♣], [A♠, A♥, K♥, J♥, Q♣]
    * trump: ♠
    * trump_card: None
    * talon: []
    * next_player: PlayerId.ONE
    * won_tricks: [(X♠, Q♠), (X♣, X♦), (Q♦, J♦)], [(K♦, A♦), (X♥, K♠)]
    * marriage_suits: [], []
    * trick_points: (38, 29)
    * current_trick: (None, None)
  """
  cards_in_hand = PlayerPair(
    one=[Card(Suit.SPADES, CardValue.JACK),
         Card(Suit.HEARTS, CardValue.QUEEN),
         Card(Suit.CLUBS, CardValue.ACE),
         Card(Suit.CLUBS, CardValue.KING),
         Card(Suit.CLUBS, CardValue.JACK)],
    two=[Card(Suit.SPADES, CardValue.ACE),
         Card(Suit.HEARTS, CardValue.ACE),
         Card(Suit.HEARTS, CardValue.KING),
         Card(Suit.HEARTS, CardValue.JACK),
         Card(Suit.CLUBS, CardValue.QUEEN)])
  won_tricks = PlayerPair(
    one=[PlayerPair(Card(Suit.SPADES, CardValue.TEN),
                    Card(Suit.SPADES, CardValue.QUEEN)),
         PlayerPair(Card(Suit.CLUBS, CardValue.TEN),
                    Card(Suit.DIAMONDS, CardValue.TEN)),
         PlayerPair(Card(Suit.DIAMONDS, CardValue.QUEEN),
                    Card(Suit.DIAMONDS, CardValue.JACK))],
    two=[PlayerPair(Card(Suit.DIAMONDS, CardValue.KING),
                    Card(Suit.DIAMONDS, CardValue.ACE)),
         PlayerPair(Card(Suit.HEARTS, CardValue.TEN),
                    Card(Suit.SPADES, CardValue.KING))])
  trick_points = PlayerPair(one=38, two=29)
  current_trick = PlayerPair(None, None)
  return GameState(cards_in_hand=cards_in_hand, trump=Suit.SPADES,
                   trump_card=None, talon=[], won_tricks=won_tricks,
                   trick_points=trick_points, current_trick=current_trick)


def get_game_view_for_duck_puzzle() -> GameState:
  """
  Generates a game view for the scenario described here:
  http://psellos.com/schnapsen/blog/2012/03/003-duck.html

  The game state is the following:
    * cards_in_hand: [A♠, X♠, A♥, Q♥, K♦], [K♠, Q♠, None, None, None]
    * unseen_cards: K♥, X♥, X♦, Q♦
    * trump: ♦
    * trump_card: J♦
    * talon: [None]
    * next_player: PlayerId.ONE
    * won_tricks: [(A♦, A♣), (K♣, J♣)], [(Q♣, X♣), (J♥, J♠)]
    * marriage_suits: [], []
    * trick_points: (28, 17)
    * current_trick: (None, Q♠)
  """
  cards_in_hand = PlayerPair(
    one=[Card(Suit.SPADES, CardValue.ACE),
         Card(Suit.SPADES, CardValue.TEN),
         Card(Suit.HEARTS, CardValue.ACE),
         Card(Suit.HEARTS, CardValue.QUEEN),
         Card(Suit.DIAMONDS, CardValue.KING)],
    two=[Card(Suit.SPADES, CardValue.KING),
         Card(Suit.SPADES, CardValue.QUEEN),
         None, None, None])
  trump_card = Card(Suit.DIAMONDS, CardValue.JACK)
  won_tricks = PlayerPair(
    one=[PlayerPair(Card(Suit.DIAMONDS, CardValue.ACE),
                    Card(Suit.CLUBS, CardValue.ACE)),
         PlayerPair(Card(Suit.CLUBS, CardValue.KING),
                    Card(Suit.CLUBS, CardValue.JACK))],
    two=[PlayerPair(Card(Suit.CLUBS, CardValue.QUEEN),
                    Card(Suit.CLUBS, CardValue.TEN)),
         PlayerPair(Card(Suit.HEARTS, CardValue.JACK),
                    Card(Suit.SPADES, CardValue.JACK))])
  trick_points = PlayerPair(one=28, two=37)
  marriage_suits = PlayerPair(one=[], two=[Suit.SPADES])
  current_trick = PlayerPair(None, Card(Suit.SPADES, CardValue.QUEEN))
  return GameState(cards_in_hand=cards_in_hand, trump=trump_card.suit,
                   trump_card=trump_card, talon=[None], won_tricks=won_tricks,
                   trick_points=trick_points, marriage_suits=marriage_suits,
                   current_trick=current_trick)


def get_game_view_for_who_laughs_last_puzzle() -> GameState:
  """
  Generates a game view for the scenario described here:
  http://psellos.com/schnapsen/blog/2012/03/004-last.html

  The game state is the following:
    * cards_in_hand: [K♥, Q♥, A♣, X♦, Q♦], [X♠, None, None, None, None]
    * unseen_cards: A♠, X♥, X♣, A♦, K♦
    * trump: ♥
    * trump_card: J♥
    * talon: [None]
    * next_player: PlayerId.ONE
    * won_tricks: [(Q♠, J♦)], [(Q♣, K♣), (J♣, J♠), (K♠, A♥)]
    * marriage_suits: [], []
    * trick_points: (5, 26)
    * current_trick: (None, X♠)
  """
  cards_in_hand = PlayerPair(
    one=[Card(Suit.HEARTS, CardValue.KING),
         Card(Suit.HEARTS, CardValue.QUEEN),
         Card(Suit.CLUBS, CardValue.ACE),
         Card(Suit.DIAMONDS, CardValue.TEN),
         Card(Suit.DIAMONDS, CardValue.QUEEN)],
    two=[Card(Suit.SPADES, CardValue.TEN), None, None, None, None])
  trump_card = Card(Suit.HEARTS, CardValue.JACK)
  won_tricks = PlayerPair(
    one=[PlayerPair(Card(Suit.SPADES, CardValue.QUEEN),
                    Card(Suit.DIAMONDS, CardValue.JACK))],
    two=[PlayerPair(Card(Suit.CLUBS, CardValue.QUEEN),
                    Card(Suit.CLUBS, CardValue.KING)),
         PlayerPair(Card(Suit.CLUBS, CardValue.JACK),
                    Card(Suit.SPADES, CardValue.JACK)),
         PlayerPair(Card(Suit.SPADES, CardValue.KING),
                    Card(Suit.HEARTS, CardValue.ACE))])
  trick_points = PlayerPair(one=5, two=26)
  current_trick = PlayerPair(None, Card(Suit.SPADES, CardValue.TEN))
  return GameState(cards_in_hand=cards_in_hand, trump=trump_card.suit,
                   trump_card=trump_card, talon=[None], won_tricks=won_tricks,
                   trick_points=trick_points, current_trick=current_trick)


def get_game_state_for_forcing_the_issue_puzzle() -> GameState:
  """
  Generates a game view for the scenario described here:
  http://psellos.com/schnapsen/blog/2012/05/013-forcing-solution.html

  The game state is the following:
    * cards_in_hand: [X♠, Q♥, X♣, A♦, K♦] [X♥, K♥, X♦, Q♦, J♦]
    * trump: ♥
    * trump_card: J♥
    * talon: [A♣], closed
    * next_player: PlayerId.ONE
    * won_tricks: [(K♠, Q♠), (A♥, A♠)], [(J♠, K♣), (J♣, Q♣)]
    * marriage_suits: [], [♣]
    * trick_points: (29, 31)
    * current_trick: (None, J♦)
    * player_that_closed_the_talon: PlayerId.TWO
    * opponent_points_when_talon_was_closed: 29
  """
  cards_in_hand = PlayerPair(
    one=[Card(Suit.SPADES, CardValue.TEN),
         Card(Suit.HEARTS, CardValue.QUEEN),
         Card(Suit.CLUBS, CardValue.TEN),
         Card(Suit.DIAMONDS, CardValue.ACE),
         Card(Suit.DIAMONDS, CardValue.KING)],
    two=[Card(Suit.HEARTS, CardValue.TEN),
         Card(Suit.HEARTS, CardValue.KING),
         Card(Suit.DIAMONDS, CardValue.TEN),
         Card(Suit.DIAMONDS, CardValue.QUEEN),
         Card(Suit.DIAMONDS, CardValue.JACK)])
  trump_card = Card(Suit.HEARTS, CardValue.JACK)
  talon = [Card(Suit.CLUBS, CardValue.ACE)]
  won_tricks = PlayerPair(
    one=[PlayerPair(Card(Suit.SPADES, CardValue.KING),
                    Card(Suit.SPADES, CardValue.QUEEN)),
         PlayerPair(Card(Suit.HEARTS, CardValue.ACE),
                    Card(Suit.SPADES, CardValue.ACE))],
    two=[PlayerPair(Card(Suit.SPADES, CardValue.JACK),
                    Card(Suit.CLUBS, CardValue.KING)),
         PlayerPair(Card(Suit.CLUBS, CardValue.JACK),
                    Card(Suit.CLUBS, CardValue.QUEEN))])
  marriage_suits = PlayerPair(one=[], two=[Suit.CLUBS])
  trick_points = PlayerPair(one=29, two=31)
  game_state = GameState(cards_in_hand=cards_in_hand, trump=trump_card.suit,
                         trump_card=trump_card, talon=talon,
                         won_tricks=won_tricks, trick_points=trick_points,
                         marriage_suits=marriage_suits,
                         next_player=PlayerId.TWO)
  game_state.close_talon()
  game_state.current_trick.two = Card(Suit.DIAMONDS, CardValue.JACK)
  game_state.next_player = PlayerId.ONE
  return game_state


def get_game_view_for_the_last_trump_puzzle() -> GameState:
  """
  Generates a game view for the scenario described here:
  http://psellos.com/schnapsen/blog/2020/06/145-trump.html

  The game state is the following:
    * cards_in_hand: [X♠, X♥, A♣, K♣, J♣] [Q♦, None, None, None, None]
    * unseen_cards: K♠, A♥, Q♣, X♣, J♦
    * trump: ♠
    * trump_card: J♠
    * talon: [None]
    * next_player: PlayerId.ONE
    * won_tricks: [(A♠, A♦), (Q♠, Q♥)], [(J♥, K♦), (K♥, X♦)]
    * marriage_suits: [], [♦]
    * trick_points: (28, 40)
    * current_trick: (None, Q♦)
  """
  cards_in_hand = PlayerPair(
    one=[Card(Suit.SPADES, CardValue.TEN),
         Card(Suit.HEARTS, CardValue.TEN),
         Card(Suit.CLUBS, CardValue.ACE),
         Card(Suit.CLUBS, CardValue.KING),
         Card(Suit.CLUBS, CardValue.JACK)],
    two=[Card(Suit.DIAMONDS, CardValue.QUEEN), None, None, None, None])
  trump_card = Card(Suit.SPADES, CardValue.JACK)
  won_tricks = PlayerPair(
    one=[PlayerPair(Card(Suit.SPADES, CardValue.ACE),
                    Card(Suit.DIAMONDS, CardValue.ACE)),
         PlayerPair(Card(Suit.SPADES, CardValue.QUEEN),
                    Card(Suit.HEARTS, CardValue.QUEEN))],
    two=[PlayerPair(Card(Suit.HEARTS, CardValue.JACK),
                    Card(Suit.DIAMONDS, CardValue.KING)),
         PlayerPair(Card(Suit.HEARTS, CardValue.KING),
                    Card(Suit.DIAMONDS, CardValue.TEN))])
  trick_points = PlayerPair(one=28, two=40)
  marriage_suits = PlayerPair(one=[], two=[Suit.DIAMONDS])
  current_trick = PlayerPair(None, Card(Suit.DIAMONDS, CardValue.QUEEN))
  return GameState(cards_in_hand=cards_in_hand, trump=trump_card.suit,
                   trump_card=trump_card, talon=[None], won_tricks=won_tricks,
                   trick_points=trick_points, marriage_suits=marriage_suits,
                   current_trick=current_trick)


def get_game_state_for_know_your_opponent_puzzle() -> GameState:
  """
  Generates a game state for the scenario described here:
  http://psellos.com/schnapsen/blog/2020/09/147-know.html

  The game state is the following:
    * cards_in_hand: [K♠, J♠, K♥, A♣, K♣] [A♠, Q♠, A♥, X♣, Q♣]
    * trump: ♥
    * trump_card: Q♥
    * talon: [J♣], closed
    * next_player: PlayerId.ONE
    * won_tricks: [(X♥, X♦), (J♥, J♦)], [(Q♦, X♠), (K♦, A♦)]
    * marriage_suits: [], []
    * trick_points: (24, 28)
    * current_trick: (None, A♥)
    * player_that_closed_the_talon: PlayerId.TWO
    * opponent_points_when_talon_was_closed: 24
  """
  cards_in_hand = PlayerPair(
    one=[Card(Suit.SPADES, CardValue.KING),
         Card(Suit.SPADES, CardValue.JACK),
         Card(Suit.HEARTS, CardValue.KING),
         Card(Suit.CLUBS, CardValue.ACE),
         Card(Suit.CLUBS, CardValue.KING)],
    two=[Card(Suit.SPADES, CardValue.ACE),
         Card(Suit.SPADES, CardValue.QUEEN),
         Card(Suit.HEARTS, CardValue.ACE),
         Card(Suit.CLUBS, CardValue.TEN),
         Card(Suit.CLUBS, CardValue.QUEEN)])
  trump_card = Card(Suit.HEARTS, CardValue.QUEEN)
  talon = [Card(Suit.CLUBS, CardValue.JACK)]
  won_tricks = PlayerPair(
    one=[PlayerPair(Card(Suit.HEARTS, CardValue.TEN),
                    Card(Suit.DIAMONDS, CardValue.TEN)),
         PlayerPair(Card(Suit.HEARTS, CardValue.JACK),
                    Card(Suit.DIAMONDS, CardValue.JACK))],
    two=[PlayerPair(Card(Suit.DIAMONDS, CardValue.QUEEN),
                    Card(Suit.SPADES, CardValue.TEN)),
         PlayerPair(Card(Suit.DIAMONDS, CardValue.KING),
                    Card(Suit.DIAMONDS, CardValue.ACE))])
  trick_points = PlayerPair(one=24, two=28)
  game_state = GameState(cards_in_hand=cards_in_hand, trump=trump_card.suit,
                         trump_card=trump_card, talon=talon,
                         won_tricks=won_tricks, trick_points=trick_points,
                         next_player=PlayerId.TWO)
  game_state.close_talon()
  game_state.current_trick.two = Card(Suit.HEARTS, CardValue.ACE)
  game_state.next_player = PlayerId.ONE
  return game_state


def get_game_state_with_multiple_cards_in_the_talon_for_tests() -> GameState:
  game_state = get_game_state_for_tests()
  with GameStateValidator(game_state):
    trick = game_state.won_tricks[PlayerId.TWO].pop()
    game_state.trick_points[PlayerId.TWO] -= trick.one.card_value
    game_state.trick_points[PlayerId.TWO] -= trick.two.card_value
    game_state.talon.extend([trick.one, trick.two])
  return game_state


def get_actions_for_one_complete_game(first_player: PlayerId):
  """
  Returns a list of actions that will fully play a game if it is initialized
  using seed=2 and dealer=first_player.opponent().
  """
  player_a = first_player
  player_b = player_a.opponent()
  actions = [
    # Player A wins the first trick. Score: 0-6.
    PlayCardAction(player_a, Card(Suit.HEARTS, CardValue.JACK)),
    PlayCardAction(player_b, Card(Suit.CLUBS, CardValue.KING)),

    # Player A closes the talon.
    CloseTheTalonAction(player_a),

    # Player A wins the second trick. Score: 0-18.
    PlayCardAction(player_a, Card(Suit.DIAMONDS, CardValue.TEN)),
    PlayCardAction(player_b, Card(Suit.DIAMONDS, CardValue.JACK)),

    # Player A wins the third trick. Score: 0-31.
    PlayCardAction(player_a, Card(Suit.HEARTS, CardValue.TEN)),
    PlayCardAction(player_b, Card(Suit.SPADES, CardValue.QUEEN)),

    # Player B wins the forth trick. Score: 13-31.
    PlayCardAction(player_a, Card(Suit.CLUBS, CardValue.JACK)),
    PlayCardAction(player_b, Card(Suit.CLUBS, CardValue.ACE)),

    # Player A wins the fifth trick. Score: 13-52.
    PlayCardAction(player_b, Card(Suit.SPADES, CardValue.TEN)),
    PlayCardAction(player_a, Card(Suit.SPADES, CardValue.ACE)),

    # Player A wins the sixth trick. Score: 13-67.
    PlayCardAction(player_a, Card(Suit.HEARTS, CardValue.ACE)),
    PlayCardAction(player_b, Card(Suit.SPADES, CardValue.KING))
  ]
  return actions
