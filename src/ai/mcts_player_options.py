#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import dataclasses
import multiprocessing
from typing import Optional

from ai.merge_scoring_infos_func import max_average_ucb, MergeScoringInfosFunc
from ai.permutations import PermutationsGenerator, sims_table_perm_generator


@dataclasses.dataclass
class MctsPlayerOptions:
  """The set of parameters used to configure an MctsPlayer."""

  # TODO(mcts): Find a good default value.
  max_iterations: Optional[int] = 1
  """
  The maximum number of Mcts iterations run for one permutation. The total
  number of iterations is max_iterations x max_permutations, spread across
  multiple processes (num_processes).
  """

  max_permutations: int = multiprocessing.cpu_count()
  """
  The player converts an imperfect-information game to a perfect-information
  game by using a random permutation of the unseen cards set. This parameter
  controls how many such permutations are used in the given computational
  budget. The player then picks the most common best action across all the
  simulated scenarios. If max_permutations is not a multiple of num_processes it
  will be rounded up to the next multiple.
  """

  num_processes: int = multiprocessing.cpu_count()
  """
  The number of processes to be used in the pool to process the permutations in
  parallel.
  """

  perm_generator: Optional[PermutationsGenerator] = sims_table_perm_generator
  """
  The function that generates the permutations of the unseen cards set that will
  be processed when request_next_action() is called.
  """

  merge_scoring_info_func: Optional[MergeScoringInfosFunc] = max_average_ucb
  """
  The function that merges all the ScoringInfos across all the processed
  permutations.
  """
