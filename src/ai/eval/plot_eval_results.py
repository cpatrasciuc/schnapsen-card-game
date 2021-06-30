#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import os
from typing import Tuple, Optional, Set, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from graphviz import Digraph
from matplotlib.colors import ListedColormap
from pandas import DataFrame
from statsmodels.stats.proportion import proportion_confint


def _get_metric(player_one: str, player_two: str, dataframe: DataFrame,
                metric_name: str) -> Optional[Tuple[int, int]]:
  filtered = dataframe[
    dataframe.player_one.eq(player_one) & dataframe.player_two.eq(player_two)]
  if len(filtered) > 0:
    assert len(filtered) == 1, "Duplicated player pair"
    filtered = filtered.iloc[0]
    return int(filtered[metric_name + "_one"]), \
           int(filtered[metric_name + "_two"])
  filtered = dataframe[
    dataframe.player_one.eq(player_two) & dataframe.player_two.eq(player_one)]
  if len(filtered) > 0:
    assert len(filtered) == 1, "Duplicated player pair"
    filtered = filtered.iloc[0]
    return int(filtered[metric_name + "_two"]), \
           int(filtered[metric_name + "_one"])
  return None


# Based on this page:
# https://matplotlib.org/stable/gallery/images_contours_and_fields/image_annotated_heatmap.html
def _render_colored_table(player_names, color, win_percentage):
  color_map = ListedColormap(["#dd7e6b", "#d9d9d9", "#93c47d"])
  plt.imshow(color, cmap=color_map)
  ax = plt.gca()

  # Show all ticks and label them with the player names.
  ax.set_xticks(range(len(player_names)))
  ax.set_yticks(range(len(player_names)))
  ax.set_xticklabels(player_names)
  ax.set_yticklabels(player_names)

  # Let the horizontal axes labeling appear on top.
  ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)

  # Rotate the tick labels and set their alignment.
  plt.setp(ax.get_xticklabels(), rotation=-30, ha="right",
           rotation_mode="anchor")

  # Turn spines off and create white grid.
  ax.spines[:].set_visible(False)
  ax.set_xticks(np.arange(len(player_names) + 1) - .5, minor=True)
  ax.set_yticks(np.arange(len(player_names) + 1) - .5, minor=True)
  ax.grid(which="minor", color="w", linestyle='-', linewidth=3)
  ax.tick_params(which="minor", bottom=False, left=False)

  # Annotate the heatmap with the win ratios.
  for i in range(len(player_names)):
    for j in range(len(player_names)):
      if np.isnan(win_percentage[i][j]):
        continue
      ax.text(j, i, "{:.2%}".format(win_percentage[i][j]), ha="center",
              va="center", color="k" if color[i][j] == 0.5 else "w")

  # Resize and layout.
  figure = plt.gcf()
  figure.set_size_inches(len(player_names), len(player_names))
  figure.tight_layout()

  # Save as PNG.
  plt.savefig(os.path.join(os.path.dirname(__file__), "data", "eval_table.png"))


def _render_graph(edges: Set[Tuple[str, str]]):
  # Add Graphviz binaries to the PATH environment variable.
  dirname = os.path.dirname
  graphviz_bin_path = os.path.join(dirname(dirname(dirname(dirname(__file__)))),
                                   "Graphviz",
                                   "bin")
  print(f"Using Graphviz bin path: {graphviz_bin_path}")
  env_path = os.environ.get("PATH", "")
  if env_path.find(graphviz_bin_path) < 0:
    print("Adding Graphviz bin path to $PATH")
    os.environ["PATH"] = env_path + os.pathsep + graphviz_bin_path

  # Render the graph as an SVG file.
  graph = Digraph()
  graph.edges(edges)
  graph.unflatten(stagger=3)
  graph.render(filename="player_rankings",
               directory=os.path.join(dirname(__file__)), format="svg",
               cleanup=True)


def plot_eval_results(dataframe: DataFrame):
  player_names = dataframe["player_one"].append(
    dataframe["player_two"]).drop_duplicates()
  num_players = len(player_names)

  # A matrix storing the win ratios for each player pair.
  win_percentage = np.ndarray((num_players, num_players))

  # A matrix storing the color to be used in the results table for each player
  # pair: 0 - red, 0.5 - gray, 1 - green.
  color = np.ndarray((num_players, num_players))

  # A list of player names pairs (A, B) where player A is significantly better
  # than player B.
  significantly_better: List[Tuple[str, str]] = []

  for i, player_one in enumerate(player_names):
    for j, player_two in enumerate(player_names):
      metric = _get_metric(player_one, player_two, dataframe, "bummerls")
      if metric is None:
        win_percentage[i][j] = np.nan
        color[i][j] = 0.5
        continue
      wins_one, wins_two = metric
      ci_low, ci_upp = proportion_confint(wins_one, wins_one + wins_two,
                                          method='wilson')
      win_percentage[i][j] = wins_one / (wins_one + wins_two)
      color[i][j] = 0.5
      if ci_low > 0.5:
        color[i][j] = 1.0
        significantly_better.append((player_one, player_two))
      if ci_upp < 0.5:
        color[i][j] = 0.0
  _render_colored_table(player_names, color, win_percentage)
  _render_graph(set(significantly_better))


if __name__ == "__main__":
  filename = os.path.join(os.path.dirname(__file__), "data", "eval_results.csv")
  plot_eval_results(pd.read_csv(filename))
