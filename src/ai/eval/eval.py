#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import os.path
from typing import List, Dict

import pandas
from pandas import DataFrame
from statsmodels.stats.proportion import proportion_confint

from ai.eval.players import PLAYER_NAMES
from ai.player import Player
from model.bummerl import Bummerl
from model.player_id import PlayerId
from model.player_pair import PlayerPair

_DATAFRAME_METRICS = ["bummerls", "games", "game_points", "trick_points"]


def _get_metrics_column_names():
  columns = []
  for metric_name in _DATAFRAME_METRICS:
    columns.extend([f"{metric_name}_one", f"{metric_name}_two"])
  return columns


def _get_results_row(metrics):
  row = []
  for metric_name in _DATAFRAME_METRICS:
    metric_value = metrics.get(metric_name, PlayerPair(None, None))
    row.extend([metric_value.one, metric_value.two])
  return row


def _accumulate_player_pair(acc: PlayerPair[int], other: PlayerPair[int]):
  acc.one += other.one
  acc.two += other.two


def _prop_confidence_interval(pair: PlayerPair[int]):
  nobs = pair.one + pair.two
  count = pair.one
  ci_low, ci_upp = proportion_confint(count, nobs, alpha=0.05, method='wilson')
  begin = ""
  if ci_low > 0.5:
    begin = "\033[92m"  # green
  elif ci_upp < 0.5:
    begin = "\033[91m"  # red
  end = "\033[0m" if begin != "" else ""
  low = "{:.2%}".format(ci_low)
  upp = "{:.2%}".format(ci_upp)
  mean = "{:.2%}".format(count / nobs)
  return f"{begin}{mean} [{low}, {upp}]{end}"


def _print_pair(label: str, pair: PlayerPair, compute_ci: bool = True):
  ci_text = ""
  if compute_ci:
    ci_text = _prop_confidence_interval(pair)
  print(f"{label}: {pair.one}:{pair.two} {ci_text}")


def _print_metrics(metrics: Dict[str, PlayerPair]):
  for metric_name, metric_value in metrics.items():
    compute_ci = metric_name in ["bummerls", "games"]
    _print_pair(metric_name, metric_value, compute_ci)
  print()


def evaluate_player_pair(players: PlayerPair[Player],
                         num_bummerls: int = 2500) -> Dict[str, PlayerPair]:
  # Initialize the metrics.
  bummerls = PlayerPair(0, 0)
  game_points = PlayerPair(0, 0)
  games = PlayerPair(0, 0)
  trick_points = PlayerPair(0, 0)

  # Simulate the games and update the metrics accordingly.
  for i in range(num_bummerls):
    if i % 100 == 0:
      print(f"\rSimulating bummerl {i} out of {num_bummerls}...", end="")
    bummerl = Bummerl()
    while not bummerl.is_over:
      bummerl.start_game()
      game = bummerl.game
      while not game.game_state.is_game_over:
        player = players[game.game_state.next_player]
        action = player.request_next_action(game.game_state)
        game.play_action(action)
      _accumulate_player_pair(trick_points, game.game_state.trick_points)
      last_game_points = game.game_state.game_points
      if last_game_points.one > 0:
        games.one += 1
      else:
        games.two += 1
      _accumulate_player_pair(game_points, last_game_points)
      bummerl.finalize_game()
    if bummerl.game_points.one > 6:
      bummerls.one += 1
    else:
      bummerls.two += 1
  print(end="\r")
  return {"bummerls": bummerls, "games": games, "game_points": game_points,
          "trick_points": trick_points}


def evaluate_one_player_vs_opponent_list(player: str,
                                         opponents: List[str]) -> DataFrame:
  rows = []
  for opponent in opponents:
    print(f"Simulating {player} vs {opponent}")
    players = PlayerPair(PLAYER_NAMES[player](PlayerId.ONE),
                         PLAYER_NAMES[opponent](PlayerId.TWO))
    metrics = evaluate_player_pair(players)
    _print_metrics(metrics)
    rows.append([player, opponent] + _get_results_row(metrics))
  columns = ["player_one", "player_two"] + _get_metrics_column_names()
  return pandas.DataFrame(rows, columns=columns)


def evaluate_all_player_pairs(player_names: List[str] = None) -> DataFrame:
  dataframes = []
  player_names = player_names or list(PLAYER_NAMES)
  for i, player_to_evaluate in enumerate(player_names):
    dataframes.append(evaluate_one_player_vs_opponent_list(
      player_to_evaluate, player_names[:i + 1]))
  return pandas.concat(dataframes)


if __name__ == "__main__":
  dataframe = evaluate_all_player_pairs()
  dataframe.to_csv(os.path.join(os.path.dirname(__file__), "eval_results.csv"),
                   index=False)
