#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import pickle
from typing import Optional, Tuple, List

from ai.cython_mcts_player.player import CythonMctsPlayer
from ai.mcts_player_options import MctsPlayerOptions
from ai.merge_scoring_infos_func import average_score_with_tiebreakers
from main_wrapper import main_wrapper
from model.bummerl import Bummerl
from model.game_state import GameState
from model.player_action import PlayerAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair

EvalResult = Tuple[str, str, PlayerAction, float, List[PlayerAction]]
EvalResults = List[EvalResult]


def evaluate_game(game, players, bummerl_score, bummerl_id, game_id):
  eval_results = []
  game_state = GameState.new(game.dealer, game.seed)
  for evaluated_action in game.actions:
    player = players[game_state.next_player]
    mcts_actions_and_scores = player.get_actions_and_scores(
      game_state.next_player_view(),
      bummerl_score)
    if len(mcts_actions_and_scores) == 1:
      # The player didn't have to make a decision. There is only one valid
      # action at this point.
      eval_results.append(
        (bummerl_id, str(game_id), evaluated_action, None, []))
    else:
      evaluated_action_score = None
      max_score = max(score for action, score in mcts_actions_and_scores)
      max_actions = [action for action, score in mcts_actions_and_scores if
                     score == max_score]
      if isinstance(max_score, tuple):
        max_score = max_score[0]
      for action, score in mcts_actions_and_scores:
        if action == evaluated_action:
          evaluated_action_score = score
          if isinstance(evaluated_action_score, tuple):
            evaluated_action_score = evaluated_action_score[0]
          break
      eval_results.append(
        (bummerl_id, str(game_id), evaluated_action,
         3 * (evaluated_action_score - max_score), max_actions))
    game_state = evaluated_action.execute(game_state)
  return eval_results


def evaluate_bummerl(bummerl: Bummerl,
                     bummerl_id: str = "0",
                     options: Optional[
                       MctsPlayerOptions] = None) -> EvalResults:
  options = options or MctsPlayerOptions(
    num_processes=1, max_permutations=150, max_iterations=667,
    merge_scoring_info_func=average_score_with_tiebreakers)
  players = PlayerPair(CythonMctsPlayer(PlayerId.ONE, False, options),
                       CythonMctsPlayer(PlayerId.TWO, False, options))
  bummerl_score = PlayerPair(0, 0)
  eval_results = []
  for game_id, game in enumerate(bummerl.completed_games):
    eval_results.extend(
      evaluate_game(game, players, bummerl_score, bummerl_id, game_id))
    bummerl_score.one += game.game_state.game_points.one
    bummerl_score.two += game.game_state.game_points.two
  return eval_results


def _get_column_widths(eval_results: EvalResults) -> List[int]:
  column_widths = [0, 0, 0]
  for eval_result in eval_results:
    for index in range(3):
      item_length = len(str(eval_result[index]))
      column_widths[index] = max(item_length, column_widths[index])
  return column_widths


def _print_with_width(message: str, width: int, align: str) -> None:
  print(("{:" + align + str(width) + "}").format(message), end="")


def _print_eval_result(eval_result: EvalResult,
                       column_widths: List[int]) -> None:
  spacing = " "
  _print_with_width(eval_result[0], column_widths[0], ">")
  print(spacing, end="")
  _print_with_width(eval_result[1], column_widths[1], ">")
  print(spacing, end="")
  _print_with_width(str(eval_result[2]), column_widths[2], "<")
  print(spacing, end="")
  score = eval_result[3]
  no_decision_str = "NO DECISION"
  score = "{:.5f}".format(score) if score is not None else no_decision_str
  _print_with_width(score, len(no_decision_str) + 2, ">")
  if eval_result[3] is None or round(eval_result[3], 5) == 0.0:
    print()
  else:
    print("   " + str(eval_result[4]))


def print_eval_results(eval_results: EvalResults,
                       restrict_to_player_id: Optional[PlayerId]):
  column_widths = _get_column_widths(eval_results)
  num_actions = PlayerPair(0, 0)
  sum_scores = PlayerPair(0, 0)
  for eval_result in eval_results:
    player_id = eval_result[2].player_id
    if restrict_to_player_id is not None and player_id != restrict_to_player_id:
      continue
    _print_eval_result(eval_result, column_widths)
    if eval_result[3] is not None:
      num_actions[player_id] += 1
      sum_scores[player_id] += eval_result[3]
  print()
  print("Overall performance:")
  if num_actions.one != 0:
    print("\tONE:\t" + ("{:.5f}".format(sum_scores.one / num_actions.one)))
  if num_actions.two != 0:
    print("\tTWO:\t" + ("{:.5f}".format(sum_scores.two / num_actions.two)))


def _main():
  # filename = "../autosave_bummerl.pickle"
  # with open(filename, "rb") as input_file:
  #   bummerl = pickle.load(input_file)
  # results = evaluate_bummerl(bummerl)
  # print_eval_results(results, None)

  options = MctsPlayerOptions(
    num_processes=1, max_permutations=150, max_iterations=667,
    merge_scoring_info_func=average_score_with_tiebreakers)
  players = PlayerPair(CythonMctsPlayer(PlayerId.ONE, False, options),
                       CythonMctsPlayer(PlayerId.TWO, False, options))
  bummerl_score = PlayerPair(0, 0)
  with open("../autosave_game.pickle", "rb") as input_file:
    game = pickle.load(input_file)
  print_eval_results(evaluate_game(game, players, bummerl_score, "0", "0"),
                     None)


if __name__ == "__main__":
  main_wrapper(_main)
