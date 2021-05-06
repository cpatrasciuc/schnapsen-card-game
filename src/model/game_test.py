#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from pickle import loads, dumps

from model.card import Card
from model.card_value import CardValue
from model.game import Game
from model.player_action import PlayCardAction, CloseTheTalonAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit


class GameTest(unittest.TestCase):
  def test_play_a_full_game(self):
    game = Game(PlayerId.ONE, seed=2)
    self.assertEqual(Suit.DIAMONDS, game.game_state.trump)

    actions = [
      # Player TWO wins the first trick. Score: 0-6.
      PlayCardAction(PlayerId.TWO, Card(Suit.HEARTS, CardValue.JACK)),
      PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)),

      # Player TWO closes the talon.
      CloseTheTalonAction(PlayerId.TWO),

      # Player TWO wins the second trick. Score: 0-18.
      PlayCardAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.TEN)),
      PlayCardAction(PlayerId.ONE, Card(Suit.DIAMONDS, CardValue.JACK)),

      # Player TWO wins the third trick. Score: 0-31.
      PlayCardAction(PlayerId.TWO, Card(Suit.HEARTS, CardValue.TEN)),
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.QUEEN)),

      # Player ONE wins the forth trick. Score: 13-31.
      PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.JACK)),
      PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.ACE)),

      # Player TWO wins the fifth trick. Score: 13-52.
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)),
      PlayCardAction(PlayerId.TWO, Card(Suit.SPADES, CardValue.ACE)),

      # Player TWO wins the sixth trick. Score: 13-67.
      PlayCardAction(PlayerId.TWO, Card(Suit.HEARTS, CardValue.ACE)),
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING))
    ]
    for action in actions:
      game.play_action(action)

    self.assertTrue(game.game_state.is_game_over)
    self.assertEqual(PlayerPair(13, 67), game.game_state.trick_points)
    self.assertEqual(PlayerPair(0, 3), game.game_state.score())

  def test_pickling(self):
    game = Game(PlayerId.ONE, seed=2)
    self.assertEqual(Suit.DIAMONDS, game.game_state.trump)

    actions = [
      # Player TWO wins the first trick. Score: 0-6.
      PlayCardAction(PlayerId.TWO, Card(Suit.HEARTS, CardValue.JACK)),
      PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.KING)),

      # Player TWO closes the talon.
      CloseTheTalonAction(PlayerId.TWO),

      # Player TWO wins the second trick. Score: 0-18.
      PlayCardAction(PlayerId.TWO, Card(Suit.DIAMONDS, CardValue.TEN)),
      PlayCardAction(PlayerId.ONE, Card(Suit.DIAMONDS, CardValue.JACK)),

      # Player TWO wins the third trick. Score: 0-31.
      PlayCardAction(PlayerId.TWO, Card(Suit.HEARTS, CardValue.TEN)),
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.QUEEN)),

      # Player ONE wins the forth trick. Score: 13-31.
      PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.JACK)),
      PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.ACE)),

      # Player TWO wins the fifth trick. Score: 13-52.
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.TEN)),
      PlayCardAction(PlayerId.TWO, Card(Suit.SPADES, CardValue.ACE)),

      # Player TWO wins the sixth trick. Score: 13-67.
      PlayCardAction(PlayerId.TWO, Card(Suit.HEARTS, CardValue.ACE)),
      PlayCardAction(PlayerId.ONE, Card(Suit.SPADES, CardValue.KING))
    ]
    for action in actions[:8]:
      game.play_action(action)
    self.assertFalse(game.game_state.is_game_over)
    self.assertEqual(PlayerPair(0, 31), game.game_state.trick_points)
    self.assertFalse(game.game_state.is_to_lead(PlayerId.ONE))
    self.assertFalse(game.game_state.is_to_lead(PlayerId.TWO))

    unpickled_game: Game = loads(dumps(game))
    self.assertEqual(unpickled_game.game_state, game.game_state)
    self.assertFalse(unpickled_game.game_state.is_game_over)
    self.assertFalse(unpickled_game.game_state.is_to_lead(PlayerId.ONE))

    for action in actions[8:]:
      unpickled_game.play_action(action)

    self.assertTrue(unpickled_game.game_state.is_game_over)
    self.assertEqual(PlayerPair(13, 67), unpickled_game.game_state.trick_points)
    self.assertEqual(PlayerPair(0, 3), unpickled_game.game_state.score())
