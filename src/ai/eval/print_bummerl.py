#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import pickle

from model.bummerl import Bummerl
from model.game_state import GameState


def print_bummerl(filename: str):
  with open(filename, "rb") as binary_file:
    bummerl: Bummerl = pickle.load(binary_file)
  for i, game in enumerate(bummerl.completed_games):
    print(f"===== Game #{i + 1} =======")
    print(f"Seed: {game.seed}")
    print(f"Dealer: {game.dealer}")
    game_state = GameState.new(game.dealer, game.seed)
    print("Player #1:", [str(card) for card in game_state.cards_in_hand.one])
    print("Player #2:", [str(card) for card in game_state.cards_in_hand.two])
    print()
    print(f"Trump card: {game_state.trump_card}")
    print("Talon:", [str(card) for card in game_state.talon])
    print()
    for action in game.actions:
      print(action)
    print(f"Trick points: {game.game_state.trick_points}")
    print(f"Game points: {game.game_state.game_points}, {bummerl.game_points}")
    print()


if __name__ == "__main__":
  print_bummerl("bummerl67.pickle")
