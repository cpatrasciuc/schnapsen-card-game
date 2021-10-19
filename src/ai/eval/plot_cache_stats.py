#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# pylint: disable=no-member,unsubscriptable-object,
# pylint: disable=too-many-locals,too-many-statements

import os

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from main_wrapper import main_wrapper


def _percentage_formatter(value: float):
  if value == 0:
    return ""
  return "{:.0f}%".format(value)


def _absolute_number_formatter(value: float):
  value = int(value)
  if value == 0:
    return ""
  if value >= 1000000:
    return f"{value // 1000000}M"
  if value >= 1000:
    return f"{value // 1000}K"
  return str(value)


def _plot_heatmap(ax, data, string_formatter):
  heatmap = ax.imshow(data, cmap="YlGn")

  ax.set_xticks(np.arange(data.shape[1]))
  ax.set_yticks(np.arange(data.shape[0]))

  ax.set_xticklabels([str(step) for step in range(1, data.shape[1] + 1)])
  ax.set_yticklabels(
    reversed(["Misses"] + [f"Hit from step={step}" for step in
                           range(1, data.shape[0])]))

  ax.spines[:].set_visible(False)
  ax.set_xticks(np.arange(data.shape[1] + 1) - .5, minor=True)
  ax.set_yticks(np.arange(data.shape[0] + 1) - .5, minor=True)
  ax.grid(which="minor", color="w", linestyle='-', linewidth=3)
  ax.tick_params(which="minor", bottom=False, left=False)

  kwargs = dict(horizontalalignment="center", verticalalignment="center")
  texts = []
  text_colors = ("black", "white")
  for i in range(data.shape[0]):
    for j in range(data.shape[1]):
      kwargs.update(color=text_colors[int(heatmap.norm(data[i, j]) > 0.5)])
      text = heatmap.axes.text(j, i, string_formatter(data[i, j]), **kwargs)
      texts.append(text)


def plot_cache_stats():
  file_template = os.path.join("data", "cache_stats_100_bummerls_vs_heuristic")
  dataframe = pd.read_csv(f"{file_template}.csv")
  max_step = dataframe.step.max()

  fig, ax = plt.subplots(nrows=2, ncols=3, squeeze=False)

  # Percentages heatmap
  index_columns = ["bummerl_id", "game_id", "step"]
  data = np.zeros(shape=(max_step + 1, max_step))
  for step in range(1, max_step + 1):
    df_step = dataframe[dataframe.step.eq(step)]
    calls = df_step[df_step.metric_name.eq("calls")]
    calls = calls.set_index(index_columns)
    misses = df_step[df_step.metric_name.eq("misses")]
    misses = misses.set_index(index_columns)
    miss_pct = misses.metric_value.sum() / calls.metric_value.sum() * 100
    if not np.isnan(miss_pct):
      data[max_step][step - 1] = miss_pct
    for hit in range(1, step + 1):
      hits = df_step[df_step.metric_name.eq(str(hit))]
      hits = hits.set_index(index_columns)
      hits_pct = hits.metric_value.sum() / calls.metric_value.sum() * 100
      if not np.isnan(hits_pct):
        data[max_step - hit][step - 1] = hits_pct
  _plot_heatmap(ax[0, 1], data, _percentage_formatter)
  ax[0, 1].set_xlabel("Step when the cache call was performed")
  ax[0, 1].set_ylabel("Fraction from total calls at each step\n"
                      "(Columns sum up to 100%)")

  # Absolute numbers heatmap
  data = np.zeros(shape=(max_step + 1, max_step))
  for step in range(1, max_step + 1):
    df_step = dataframe[dataframe.step.eq(step)]
    misses = df_step[df_step.metric_name.eq("misses")].metric_value.mean()
    data[max_step][step - 1] = misses
    for hit in range(1, step + 1):
      hits = df_step[df_step.metric_name.eq(str(hit))].metric_value
      if len(hits) > 0:
        data[max_step - hit][step - 1] = hits.mean()
  _plot_heatmap(ax[0, 2], data, _absolute_number_formatter)
  ax[0, 2].set_xlabel("Step when the cache call was performed")
  ax[0, 2].set_ylabel("Average number of calls")

  # Cache size at each step
  data = dataframe[dataframe.metric_name.eq("size")]
  data.boxplot(column="metric_value", by="step", ax=ax[1, 0])
  ax[1, 0].set_xlabel("Step")
  ax[1, 0].set_ylabel("Number of cache entries")
  ax[1, 0].set_title("")

  # Number of calls at each step
  calls = dataframe[dataframe.metric_name.eq("calls")]
  calls.boxplot(column="metric_value", by="step", ax=ax[1, 1])
  ax[1, 1].set_xlabel("Step")
  ax[1, 1].set_ylabel("Number of cache calls")
  ax[1, 1].set_title("")

  # Number of hits at each step
  misses = dataframe[dataframe.metric_name.eq("misses")]
  misses = misses.set_index(index_columns)
  calls = calls.set_index(index_columns)
  hits = calls[["metric_value"]] - misses[["metric_value"]]
  hits.boxplot(column="metric_value", by="step", ax=ax[1, 2])
  ax[1, 2].set_xlabel("Step")
  ax[1, 2].set_ylabel("Number of cache hits")
  ax[1, 2].set_title("")

  # Line plot
  hits_from_same_step = \
    dataframe[dataframe.step.astype(str) == dataframe.metric_name]
  hits_from_same_step = hits_from_same_step.set_index(index_columns)
  hits_from_prev_steps = hits - hits_from_same_step[["metric_value"]]

  calls = calls.groupby("step").mean()
  ax[0, 0].plot(calls.index, calls.metric_value, "o-", color="b",
                label="Calls")
  hits = hits.groupby("step").mean()
  ax[0, 0].plot(hits.index, hits.metric_value, "o-", color="r",
                label="All Hits")
  hits_from_prev_steps = hits_from_prev_steps.groupby("step").mean()
  ax[0, 0].plot(hits_from_prev_steps.index, hits_from_prev_steps.metric_value,
                "o-", color="g", label="Hits from previous steps")
  ax[0, 0].set_xlabel("Step")
  ax[0, 0].legend(loc=0)

  fig.suptitle("Cache stats (100 bummerls Mcts vs Heuristic)")

  plt.gcf().set_size_inches((20, 12))
  plt.tight_layout()
  plt.savefig(f"{file_template}.png")


if __name__ == "__main__":
  main_wrapper(plot_cache_stats)
