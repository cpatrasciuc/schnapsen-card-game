#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import functools
import multiprocessing
import os.path
import random
import time
from typing import List, Dict

import pandas
from pandas import DataFrame
from statsmodels.stats.proportion import proportion_confint

from ai.eval.players import PLAYER_NAMES
from ai.player import Player
from main_wrapper import main_wrapper
from model.bummerl import Bummerl
from model.game_state import GameState
from model.player_id import PlayerId
from model.player_pair import PlayerPair

MetricsDict = Dict[str, PlayerPair]

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
  if compute_ci and pair != PlayerPair(0, 0):
    ci_text = _prop_confidence_interval(pair)
  print(f"{label}: {pair.one}:{pair.two} {ci_text}")


def _print_metrics(metrics: MetricsDict):
  for metric_name, metric_value in metrics.items():
    compute_ci = metric_name in ["bummerls", "games", "bummerls_of_interest",
                                 "games_of_interest"]
    _print_pair(metric_name, metric_value, compute_ci)
  print()


def accumulate_metrics(acc_metrics: MetricsDict, metrics: MetricsDict):
  for metric_name in acc_metrics.keys():
    acc_metrics[metric_name].one += metrics[metric_name].one
    acc_metrics[metric_name].two += metrics[metric_name].two


def _request_next_action_and_time_it(game_view: GameState,
                                     game_points: PlayerPair[int],
                                     player: Player):
  start_perf = time.perf_counter()
  start_process = time.process_time()
  action = player.request_next_action(game_view, game_points)
  end_perf = time.perf_counter()
  end_process = time.process_time()
  return action, end_perf - start_perf, end_process - start_process


def evaluate_player_pair_in_process(num_bummerls: int,
                                    players: PlayerPair[str]) -> MetricsDict:
  # pylint: disable=too-many-locals,too-many-branches,too-many-statements

  players = PlayerPair(PLAYER_NAMES[players.one](PlayerId.ONE),
                       PLAYER_NAMES[players.two](PlayerId.TWO))

  # Initialize the metrics.
  bummerls = PlayerPair(0, 0)
  game_points = PlayerPair(0, 0)
  games = PlayerPair(0, 0)
  trick_points = PlayerPair(0, 0)

  bummerls_of_interest = PlayerPair(0, 0)
  games_of_interest = PlayerPair(0, 0)

  perf_counter_sum = PlayerPair(0, 0)
  process_time_sum = PlayerPair(0, 0)
  num_actions_requested = PlayerPair(0, 0)

  random_seed_generator = random.Random()

  # Simulate the games and update the metrics accordingly.
  for i in range(num_bummerls):
    print(f"\rSimulating bummerl {i} out of {num_bummerls} ({bummerls})...",
          end="")
    bummerl = Bummerl()
    is_bummerl_of_interest = False
    while not bummerl.is_over:
      bummerl.start_game(seed=random_seed_generator.random())
      players.one.game_of_interest = False
      players.two.game_of_interest = False
      game = bummerl.game
      while not game.game_state.is_game_over:
        player_id = game.game_state.next_player
        if players[player_id].cheater:
          game_view = game.game_state.next_player_view(
            allow_public_in_talon=True)
        else:
          game_view = game.game_state.next_player_view()
        action, perf_counter, process_time = _request_next_action_and_time_it(
          game_view, bummerl.game_points, players[player_id])
        game.play_action(action)
        perf_counter_sum[player_id] += perf_counter
        process_time_sum[player_id] += process_time
        num_actions_requested[player_id] += 1
      is_game_of_interest = \
        players.one.game_of_interest or players.two.game_of_interest or game.game_state.is_talon_closed
      if is_game_of_interest:
        is_bummerl_of_interest = True
      _accumulate_player_pair(trick_points, game.game_state.trick_points)
      last_game_points = game.game_state.game_points
      if last_game_points.one > 0:
        games.one += 1
        if is_game_of_interest:
          games_of_interest.one += 1
      else:
        games.two += 1
        if is_game_of_interest:
          games_of_interest.two += 1
      _accumulate_player_pair(game_points, last_game_points)
      bummerl.finalize_game()
    if bummerl.game_points.one > 6:
      bummerls.one += 1
      if is_bummerl_of_interest:
        bummerls_of_interest.one += 1
    else:
      bummerls.two += 1
      if is_bummerl_of_interest:
        bummerls_of_interest.two += 1

  print(end="\r")
  return {"bummerls": bummerls, "games": games, "game_points": game_points,
          "trick_points": trick_points,
          "bummerls_of_interest": bummerls_of_interest,
          "games_of_interest": games_of_interest,
          "perf_counter_sum": perf_counter_sum,
          "process_time_sum": process_time_sum,
          "num_actions_requested": num_actions_requested}


def evaluate_player_pair_in_parallel(players: PlayerPair[str],
                                     num_bummerls: int = 1000,
                                     num_processes: int = 4) -> MetricsDict:
  num_bummerls_per_process = num_bummerls // num_processes
  num_bummerls_to_run = [num_bummerls_per_process] * num_processes
  for i in range(num_bummerls % num_processes):
    num_bummerls_to_run[i] += 1
  print(f"Number of bummerls for each worker: {num_bummerls_to_run}")

  with multiprocessing.Pool(processes=num_processes) as pool:
    metrics_dicts = pool.map(
      functools.partial(evaluate_player_pair_in_process, players=players),
      num_bummerls_to_run)

  merged_metrics = metrics_dicts[0]
  for metric_dict in metrics_dicts[1:]:
    accumulate_metrics(merged_metrics, metric_dict)
  return merged_metrics


def evaluate_one_player_vs_opponent_list(player: str,
                                         opponents: List[str]) -> DataFrame:
  rows = []
  for opponent in opponents:
    print(f"Simulating {player} vs {opponent}")
    players = PlayerPair(player, opponent)
    metrics = evaluate_player_pair_in_parallel(players)
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


def main():
  dataframe = evaluate_all_player_pairs()
  # noinspection PyTypeChecker
  dataframe.to_csv(os.path.join(os.path.dirname(__file__), "eval_results.csv"),
                   index=False)


if __name__ == "__main__":
  main_wrapper(main)
