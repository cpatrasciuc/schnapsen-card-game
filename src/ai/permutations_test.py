#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import random
import time
import unittest
from typing import Callable, List

import pandas

from ai.permutations import random_perm_generator
from model.card import Card


class PermutationsTest(unittest.TestCase):
  def test_random_perm_generator(self):
    all_cards = Card.get_all_cards()
    rng = random.Random(1234)

    def rng_func():
      return rng.random()

    permutations = random_perm_generator(all_cards[:6], 0, 10, rng_func)
    self.assertEqual(10, len(permutations))
    self.assertEqual(len(set(tuple(p) for p in permutations)),
                     len(permutations))

    permutations = random_perm_generator(all_cards[:6], 0, None, rng_func)
    self.assertEqual(720, len(permutations))
    self.assertEqual(len(set(tuple(p) for p in permutations)),
                     len(permutations))

    permutations = random_perm_generator(all_cards[:6], 4, None, rng_func)
    self.assertEqual(30, len(permutations))
    self.assertEqual(len(set(tuple(p) for p in permutations)),
                     len(permutations))
    for i, permutation in enumerate(permutations):
      # noinspection PyTypeChecker
      self.assertEqual(sorted(permutation[:4]), permutation[:4], msg=i)

    with self.assertRaises(AssertionError):
      random_perm_generator(all_cards[:6], 20, 10)

    # Test the default RNG
    permutations = random_perm_generator(all_cards[:6], 0, 10)
    self.assertEqual(10, len(permutations))
    self.assertEqual(len(set(tuple(p) for p in permutations)),
                     len(permutations))


class PermutationsSpeedTest(unittest.TestCase):
  def _time_it(self, perm_gen: Callable[[], List[List[Card]]],
               num_runs: int) -> List[float]:
    timing_data = []
    for run_id in range(num_runs):
      if run_id % 10 == 0:
        print(".", end="", flush=True)
      start_time = time.process_time()
      permutations = perm_gen()
      end_time = time.process_time()
      self.assertGreater(len(permutations), 0)
      timing_data.append(end_time - start_time)
    return timing_data

  def test(self):
    cards = Card.get_all_cards()[:14]
    num_runs = 1000
    num_permutations_requested = 100
    permutations_generators = {
      "random_perm_generator":
        lambda: random_perm_generator(cards, 5, num_permutations_requested)
    }
    series = []
    for name, func in permutations_generators.items():
      timing_data = self._time_it(func, num_runs)
      timing_data = pandas.Series(timing_data)
      timing_data.name = name
      print(name)
      print(timing_data.describe())
      series.append(timing_data)

    dataframe = pandas.concat(series, axis=1)
    print(dataframe.describe())
