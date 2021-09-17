#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from typing import List, Tuple

from pandas import DataFrame

from model.game_state import GameState
from model.player_action import get_available_actions, PlayCardAction, \
  AnnounceMarriageAction, PlayerAction


def play_one_trick(game_state: GameState) -> GameState:
  for _ in range(2):
    actions = get_available_actions(game_state)
    actions = [action for action in actions if
               isinstance(action, (PlayCardAction, AnnounceMarriageAction))]
    game_state = actions[0].execute(game_state)
  return game_state


def get_dataframe_from_actions_and_scores(
    actions_and_scores: List[Tuple[PlayerAction, float]]) -> DataFrame:
  dataframe = DataFrame(
    [(score, str(action)) for action, score in actions_and_scores],
    columns=["score", "action"])
  dataframe["rank"] = dataframe["score"].sort_values().rank(method="min",
                                                            ascending=False)
  return dataframe
