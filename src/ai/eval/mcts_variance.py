#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import matplotlib.pyplot as plt
import numpy as np
from pandas import DataFrame
from pandas.plotting import table

from ai.cython_mcts_player.mcts_debug import run_mcts_player_step_by_step, \
  run_mcts_and_collect_data
from ai.cython_mcts_player.player import CythonMctsPlayer
from ai.mcts_player_options import MctsPlayerOptions
from main_wrapper import main_wrapper
from model.game_state import GameState


def _is_ci_overlap(first_low: float, first_upp: float, second_low: float,
                   second_upp: float) -> bool:
  if first_low < second_low < first_upp:
    return True
  if first_low < second_upp < first_upp:
    return True
  if second_low < first_upp < second_upp:
    return True
  return False


def _get_dataframe(game_state: GameState, cheater: bool,
                   options: MctsPlayerOptions, num_samples: int) -> DataFrame:
  data = []
  game_view = game_state if cheater else game_state.next_player_view()
  for _ in range(num_samples):
    player = CythonMctsPlayer(game_state.next_player, cheater, options)
    actions_and_scores = player.get_actions_and_scores(game_view)
    for action, score in actions_and_scores:
      data.append((str(action), score))
  dataframe = DataFrame(data, columns=["action", "score"])
  dataframe = dataframe.pivot(columns=["action"], values=["score"])
  dataframe.columns = dataframe.columns.droplevel()
  return dataframe


def mcts_variance(game_state: GameState, cheater: bool,
                  options: MctsPlayerOptions, num_samples: int):
  dataframe = _get_dataframe(game_state, cheater, options, num_samples)
  print(dataframe.describe())
  dataframe.boxplot()
  details = dataframe.describe()
  details.columns = [""] * len(details.columns)
  table(plt.gca(), np.round(details, 2))
  plt.gca().xaxis.tick_top()
  plt.xticks(rotation=45, ha='left')
  plt.gcf().set_size_inches((5, 10))
  plt.tight_layout()
  plt.savefig("mcts_variance.png")


def mcts_variance_across_multiple_game_states(cheater: bool,
                                              options: MctsPlayerOptions,
                                              num_samples: int,
                                              num_game_states: int):
  data = []
  for seed in range(num_game_states):
    print(f"Evaluating on GameState.new(random_seed={seed})")
    dataframe = _get_dataframe(GameState.new(random_seed=seed),
                               cheater, options, num_samples)
    details = dataframe.describe().T.sort_values(by="mean", ascending=False)
    std_dev = list(details["std"].values)
    while len(std_dev) < 7:
      std_dev.append(np.nan)
    data.append(tuple(std_dev))
  dataframe = DataFrame(
    data, columns=["BestAction"] + [f"Action #{i}" for i in range(2, 8)])
  csv_path = "mcts_variance_across_game_states.csv"
  # noinspection PyTypeChecker
  dataframe.to_csv(csv_path, index=False)
  # dataframe = pandas.read_csv(csv_path)
  dataframe.boxplot()
  plt.xticks(rotation=45, ha='right')
  plt.gcf().set_size_inches((5, 5))
  plt.tight_layout()
  plt.savefig("mcts_variance_across_game_states.png")


def mcts_ci_widths_across_multiple_game_states(use_player: bool,
                                               options: MctsPlayerOptions,
                                               num_samples: int,
                                               num_game_states: int):
  data = []
  overlap_count = 0
  for seed in range(num_game_states):
    print(f"Evaluating on GameState.new(random_seed={seed})")
    for _ in range(num_samples):
      if use_player:
        dataframe = run_mcts_player_step_by_step(
          GameState.new(random_seed=seed).next_player_view(), options,
          options.max_iterations)
      else:
        dataframe = run_mcts_and_collect_data(
          GameState.new(random_seed=seed), options, options.max_iterations)
      dataframe["ci_width"] = dataframe["score_upp"] - dataframe["score_low"]
      dataframe = dataframe[
        dataframe.iteration.eq(dataframe.iteration.max())].sort_values(
        "score", ascending=False)
      if _is_ci_overlap(dataframe.iloc[0].score_low,
                        dataframe.iloc[0].score_upp,
                        dataframe.iloc[1].score_low,
                        dataframe.iloc[1].score_upp):
        overlap_count += 1
      ci_widths = list(dataframe["ci_width"].values)
      while len(ci_widths) < 7:
        ci_widths.append(np.nan)
      data.append(tuple(ci_widths))
  overlap_pct = np.round(overlap_count / num_samples / num_game_states * 100, 2)
  print(f"Overlap in the CIs for the best two actions in {overlap_count} "
        f"cases out of {num_samples * num_game_states} ({overlap_pct}%)")
  dataframe = DataFrame(
    data, columns=["BestAction"] + [f"Action #{i}" for i in range(2, 8)])
  suffix = "_player" if use_player else ""
  csv_path = f"mcts_ci_widths_across_game_states{suffix}.csv"
  # noinspection PyTypeChecker
  dataframe.to_csv(csv_path, index=False)
  # dataframe = pandas.read_csv(csv_path)
  dataframe.boxplot()
  plt.xticks(rotation=45, ha='right')
  plt.gcf().set_size_inches((5, 5))
  plt.tight_layout()
  plt.savefig(f"mcts_ci_widths_across_game_states{suffix}.png")


def mcts_ci_widths_and_permutations_across_multiple_game_states(
    options: MctsPlayerOptions,
    num_samples: int,
    num_game_states: int,
    keep_total_budget_constant: bool):
  data = []
  total_budget = options.max_iterations * options.max_permutations
  for seed in range(num_game_states):
    print(f"Evaluating on GameState.new(random_seed={seed})")
    for _ in range(num_samples):
      for permutations in [20, 50, 100, 200, 500, 1000]:
        options.max_permutations = permutations
        if keep_total_budget_constant:
          options.max_iterations = total_budget // permutations
        dataframe = run_mcts_player_step_by_step(
          GameState.new(random_seed=seed).next_player_view(), options,
          options.max_iterations)
        dataframe["ci_width"] = dataframe["score_upp"] - dataframe["score_low"]
        dataframe = dataframe[
          dataframe.iteration.eq(dataframe.iteration.max())].sort_values(
          "score", ascending=False)
        ci_widths = [permutations] + list(dataframe["ci_width"].values)
        while len(ci_widths) < 8:
          ci_widths.append(np.nan)
        data.append(tuple(ci_widths))
  dataframe = DataFrame(
    data, columns=["Permutations", "BestAction"] + [f"Action #{i}" for i in
                                                    range(2, 8)])
  csv_path = "mcts_ci_widths_and_perm_across_game_states.csv"
  # noinspection PyTypeChecker
  dataframe.to_csv(csv_path, index=False)
  # dataframe = pandas.read_csv(csv_path)
  dataframe[["Permutations", "BestAction"]].boxplot(by=["Permutations"])
  plt.xticks(rotation=45, ha='right')
  plt.gcf().set_size_inches((5, 5))
  if keep_total_budget_constant:
    plt.title(f"Total budget: {total_budget} iterations")
  else:
    plt.title(f"Constant iterations: {options.max_iterations} iterations")
  plt.tight_layout()
  plt.savefig("mcts_ci_widths_and_perm_across_game_states.png")


def main():
  cheater = False
  options = MctsPlayerOptions(num_processes=1,
                              max_iterations=1000,
                              max_permutations=100,
                              select_best_child=True,
                              save_rewards=True)
  num_samples = 1
  mcts_variance(GameState.new(random_seed=0), cheater, options, num_samples)
  mcts_ci_widths_and_permutations_across_multiple_game_states(
    options=options,
    num_samples=num_samples,
    num_game_states=30,
    keep_total_budget_constant=True)
  # mcts_variance_across_multiple_game_states(cheater, options, num_samples,
  #                                           num_game_states=3)
  # mcts_ci_widths_across_multiple_game_states(use_player=False,
  #                                            options=options,
  #                                            num_samples=num_samples,
  #                                            num_game_states=30)


if __name__ == "__main__":
  main_wrapper(main)
