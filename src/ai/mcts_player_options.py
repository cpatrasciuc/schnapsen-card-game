#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import dataclasses
import multiprocessing
from typing import Optional

from ai.merge_scoring_infos_func import average_ucb, MergeScoringInfosFunc
from ai.permutations import PermutationsGenerator, sims_table_perm_generator


@dataclasses.dataclass
class MctsPlayerOptions:
  """The set of parameters used to configure an MctsPlayer."""

  # pylint: disable=too-many-instance-attributes

  # TODO(mcts): Find a good default value.
  max_iterations: Optional[int] = 1
  """
  The maximum number of Mcts iterations run for one permutation. The total
  number of iterations is max_iterations x max_permutations, spread across
  multiple processes (num_processes). If None, the Mcts algorithm will run until
  the entire game tree is expanded.
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

  # TODO(mcts): Eval this parameter.
  perm_generator: Optional[PermutationsGenerator] = sims_table_perm_generator
  """
  The function that generates the permutations of the unseen cards set that will
  be processed when request_next_action() is called.
  """

  merge_scoring_info_func: Optional[MergeScoringInfosFunc] = average_ucb
  """
  The function that merges all the ScoringInfos across all the processed
  permutations.
  """

  select_best_child: bool = True
  """
  If True, during the selection step, the Mcts algorithm will always select the
  child with the highest UCB among the not-fully-simulated children. If there
  are more such children, one of them is selected randomly. If this field is
  False, during the selection step, the Mcts algorithm will pick a random child.
  """

  # TODO(mcts): After all other tuning ideas are explored revisit sqrt(2) here.
  exploration_param: float = 1
  """
  Parameter that balances exploration vs exploitation. It is used only if
  select_best_child is True. If exploration_param is zero, during the selection
  phase of the Mcts algorithm, one of the best children will always be selected.
  Higher values of exploration_param will increase the probability that one of
  the least selected children will be preferred.
  """

  save_rewards: bool = False
  """
  If True, the children of the root node in the Mcts algorithm will save all the
  individual rewards obtained on paths that pass through them. This list can be
  used to obtain a better score/estimate, measure the confidence of the score,
  debug the algorithm, etc.
  """

  reallocate_computational_budget: bool = True
  """
  The total computational budget is given by max_permutations * max_iterations.
  If this field is True and the actual number of permutations to process is
  smaller than max_permutations (e.g., the talon is empty, so all cards are
  known), the player will increase the number of iterations per permutation such
  that the total computational budget stays constant. This means that:
  actual_permutations * actual_iterations = max_permutations * max_iterations.
  """

  # TODO(mcts): Evaluate this.
  use_game_points: bool = True
  """
  If True, the player takes into account the game points. This can change the
  trade-offs towards the end of a bummerl, where winning/losing 3 points must
  be the same as winning/losing 1 point, because the bummerl will be over. This
  means that the break-even point changes, so the player will be more
  conservative if it's leading and more aggressive if it's behind.
  """

  use_heuristic: bool = False
  """
  If True, when a node is expanded for the first time during the Mcts algorithm,
  we expand the action deemed best by the HeuristicPlayer for that game state.
  If False, one of the not-yet-expanded actions will be picked randomly.
  If the node was already expanded once in one of the previous Mcts iterations,
  this option has no effect.
  """
