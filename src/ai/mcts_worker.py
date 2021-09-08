#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import math
import multiprocessing
from multiprocessing import Queue

from ai.mcts_algorithm import MCTS
from ai.utils import populate_game_view
from model.player_id import PlayerId


class MctsWorker:

  # pylint: disable=too-many-arguments,too-few-public-methods

  def __init__(self, worker_id: int, input_queue: Queue, output_queue: Queue,
               player_id: PlayerId, max_iterations: int):
    self._input_queue = input_queue
    self._output_queue = output_queue
    self._player_id = player_id
    self._mcts = MCTS(player_id)
    self._id = worker_id
    self._max_iterations = max_iterations

  def run(self):
    while True:
      try:
        game_view, permutations = self._input_queue.get()
      except ValueError:
        break

      if game_view is None:
        break

      # TODO(optimization): Maybe send just the stats, not the whole tree.
      root_nodes = []
      for permutation in permutations:
        game_state = populate_game_view(game_view, permutation)
        root_node = self._mcts.build_tree(game_state, self._max_iterations)
        root_nodes.append(root_node)

      try:
        self._output_queue.put(root_nodes)
      except ValueError:
        break

    self._input_queue.close()
    self._output_queue.close()


def run_worker(worker_id, input_queue, output_queue, player_id,
               max_iterations):
  worker = MctsWorker(worker_id, input_queue, output_queue, player_id,
                      max_iterations)
  worker.run()


class WorkerPool:
  def __init__(self, num_workers: int, player_id: PlayerId,
               max_iterations: int):
    self._num_workers = num_workers
    self._input_queues = [Queue() for _ in range(num_workers)]
    self._output_queues = [Queue() for _ in range(num_workers)]
    self._workers = [multiprocessing.Process(target=run_worker, args=(
      i, self._input_queues[i], self._output_queues[i], player_id,
      max_iterations)) for i in
                     range(num_workers)]
    for worker in self._workers:
      worker.start()

  def map(self, game_view, permutations):
    batch_size = math.ceil(len(permutations) / self._num_workers)
    workers_used = self._num_workers if batch_size > 1 else len(permutations)
    for i, queue in enumerate(self._input_queues[:workers_used]):
      queue.put((game_view, permutations[i * batch_size:(i + 1) * batch_size]))
    root_nodes = []
    for queue in self._output_queues[:workers_used]:
      root_nodes.extend(queue.get())
    return root_nodes

  def stop(self):
    for queue in self._input_queues:
      queue.put((None, None))
      queue.close()
      queue.join_thread()
    for queue in self._output_queues:
      queue.close()
      queue.join_thread()
    for worker in self._workers:
      worker.join()
