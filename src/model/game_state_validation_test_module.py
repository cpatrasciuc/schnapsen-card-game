#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

"""
Test module used by
ValidateGameStatesDecoratorTest.test_decorator_has_no_effect_in_non_debug_mode.
"""

from model.game_state_test_utils import get_game_state_for_tests
from model.game_state_validation import validate_game_states
from model.player_pair import PlayerPair


@validate_game_states
def func(game_state):
  game_state.trick_points = PlayerPair(0, 0)


def main():
  func(get_game_state_for_tests())
  print("Success")


if __name__ == "__main__":
  main()
