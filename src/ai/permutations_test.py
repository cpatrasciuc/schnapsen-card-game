#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# pylint: disable=invalid-name

import os
import random
import time
import unittest
from typing import List

import pandas
from matplotlib import pyplot as plt

from ai.permutations import random_perm_generator, lexicographic_perm_generator, \
  SimsTablePermGenerator, distance, dispersion, sims_table_perm_generator, \
  PermutationsGenerator
from model.card import Card


class RandomPermGeneratorTest(unittest.TestCase):
  def test(self):
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


class LexicographicPermGeneratorTest(unittest.TestCase):
  def test(self):
    all_cards = Card.get_all_cards()

    permutations = lexicographic_perm_generator(all_cards[:6], 0, 10)
    self.assertEqual(10, len(permutations))
    self.assertEqual(len(set(tuple(p) for p in permutations)),
                     len(permutations))

    permutations = lexicographic_perm_generator(all_cards[:6], 0, None)
    self.assertEqual(720, len(permutations))
    self.assertEqual(len(set(tuple(p) for p in permutations)),
                     len(permutations))

    permutations = lexicographic_perm_generator(all_cards[:6], 4, None)
    self.assertEqual(30, len(permutations))
    self.assertEqual(len(set(tuple(p) for p in permutations)),
                     len(permutations))
    for i, permutation in enumerate(permutations):
      # noinspection PyTypeChecker
      self.assertEqual(sorted(permutation[:4]), permutation[:4], msg=i)

    # The number of requested permutations is higher than the total number of
    # permutations that can be generated.
    self.assertEqual(permutations,
                     lexicographic_perm_generator(all_cards[:6], 4, 70))

    # Test that the permutations are generated in the expected order.
    index_permutations = [[0, 1, 2, 3, 4], [0, 1, 2, 4, 3], [0, 1, 3, 4, 2],
                          [0, 2, 3, 4, 1], [1, 2, 3, 4, 0]]
    expected_permutations = [[all_cards[index] for index in perm] for perm in
                             index_permutations]
    self.assertEqual(expected_permutations,
                     lexicographic_perm_generator(all_cards[:5], 4, None))

    with self.assertRaises(AssertionError):
      lexicographic_perm_generator(all_cards[:6], 20, 10)


class SimsTablePermGeneratorTest(unittest.TestCase):
  def test_convert_to_mixed_radix(self):
    generator = SimsTablePermGenerator(3)
    self.assertEqual([0, 0, 0], generator.convert_to_mixed_radix(0))
    self.assertEqual([0, 1, 0], generator.convert_to_mixed_radix(1))
    self.assertEqual([0, 0, 1], generator.convert_to_mixed_radix(2))
    self.assertEqual([0, 1, 1], generator.convert_to_mixed_radix(3))
    self.assertEqual([0, 0, 2], generator.convert_to_mixed_radix(4))
    self.assertEqual([0, 1, 2], generator.convert_to_mixed_radix(5))

    generator = SimsTablePermGenerator(5, 2)
    self.assertEqual([0, 0, 0], generator.convert_to_mixed_radix(0))
    self.assertEqual([1, 0, 0], generator.convert_to_mixed_radix(1))
    self.assertEqual([0, 1, 0], generator.convert_to_mixed_radix(3))
    self.assertEqual([0, 0, 1], generator.convert_to_mixed_radix(12))
    self.assertEqual([0, 1, 1], generator.convert_to_mixed_radix(15))
    self.assertEqual([0, 0, 2], generator.convert_to_mixed_radix(24))
    self.assertEqual([0, 1, 2], generator.convert_to_mixed_radix(27))
    self.assertEqual([1, 3, 4], generator.convert_to_mixed_radix(58))
    self.assertEqual([2, 3, 4], generator.convert_to_mixed_radix(59))

  def test_generate_permutation(self):
    generator = SimsTablePermGenerator(3)
    self.assertEqual([0, 1, 2], generator.generate_permutation(0))
    self.assertEqual([1, 0, 2], generator.generate_permutation(1))
    self.assertEqual([0, 2, 1], generator.generate_permutation(2))
    self.assertEqual([2, 0, 1], generator.generate_permutation(3))
    self.assertEqual([2, 1, 0], generator.generate_permutation(4))
    self.assertEqual([1, 2, 0], generator.generate_permutation(5))

    generator = SimsTablePermGenerator(5, 2)
    test_cases = [(0, [0, 1, 2, 3, 4]),
                  (1, [0, 2, 1, 3, 4]),
                  (3, [0, 1, 3, 2, 4]),
                  (12, [0, 1, 2, 4, 3]),
                  (15, [0, 1, 4, 2, 3]),
                  (24, [0, 1, 4, 3, 2]),
                  (27, [0, 1, 3, 4, 2]),
                  (58, [3, 2, 1, 4, 0]),
                  (59, [2, 1, 3, 4, 0])]
    for c, expected_permutation in test_cases:
      self.assertEqual(expected_permutation,
                       generator.generate_permutation(c, False))

    generator = SimsTablePermGenerator(5, 2)
    test_cases = [(0, [0, 1, 2, 3, 4]),
                  (1, [0, 2, 1, 3, 4]),
                  (3, [0, 1, 3, 2, 4]),
                  (12, [0, 1, 2, 4, 3]),
                  (15, [0, 1, 4, 2, 3]),
                  (24, [0, 1, 4, 3, 2]),
                  (27, [0, 1, 3, 4, 2]),
                  (58, [2, 3, 1, 4, 0]),
                  (59, [1, 2, 3, 4, 0])]
    for c, expected_permutation in test_cases:
      self.assertEqual(expected_permutation,
                       generator.generate_permutation(c, True))

  def test_permutations(self):
    generator = SimsTablePermGenerator(3, counter=0, increment=1)
    self.assertEqual(
      [[0, 1, 2], [1, 0, 2], [0, 2, 1], [2, 0, 1], [2, 1, 0], [1, 2, 0]],
      list(generator.permutations()))
    generator = SimsTablePermGenerator(n=5, m=2, counter=14, increment=17)
    self.assertEqual([[1, 2, 0, 4, 3],
                      [0, 4, 3, 1, 2],
                      [1, 4, 2, 3, 0],
                      [1, 3, 0, 2, 4],
                      [2, 4, 1, 0, 3],
                      [0, 4, 3, 2, 1],
                      [2, 3, 4, 1, 0]],
                     list(generator.permutations(7)))
    generator = SimsTablePermGenerator(n=5, m=5, counter=14, increment=17)
    self.assertEqual([[0, 1, 2, 3, 4]], list(generator.permutations()))
    self.assertEqual([[0, 1, 2, 3, 4]], list(generator.permutations(7)))
    generator = SimsTablePermGenerator(n=5, m=5)
    self.assertEqual([[0, 1, 2, 3, 4]], list(generator.permutations()))
    self.assertEqual([[0, 1, 2, 3, 4]], list(generator.permutations(7)))

  def test_distance(self):
    self.assertAlmostEqual(0.47, distance([0, 1, 2, 3, 4], [0, 2, 1, 3, 4], 2),
                           places=2)
    self.assertAlmostEqual(0.47, distance([1, 0, 2, 3, 4], [0, 2, 1, 3, 4], 2),
                           places=2)
    self.assertAlmostEqual(1.0, distance([0, 1, 2, 3, 4], [3, 2, 1, 4, 0], 2),
                           places=2)
    self.assertAlmostEqual(0, distance([0, 1, 2, 3, 4], [0, 1, 2, 3, 4], 2),
                           places=2)
    self.assertAlmostEqual(0, distance([1, 0, 2, 3, 4], [0, 1, 2, 3, 4], 2),
                           places=2)
    with self.assertRaises(AssertionError):
      distance([0, 1, 2], [0, 1, 2, 3], 2)

  def test_dispersion(self):
    self.assertEqual(0, dispersion([[1, 0, 2, 3, 4], [0, 1, 2, 3, 4]], 2))
    self.assertEqual(1, dispersion([[0, 1, 2, 3, 4], [3, 2, 1, 4, 0]], 2))

    # TODO(tests): Find out why the numbers here don't match the numbers from
    #  the paper: 0.284 for counter=0 and increment=0, 0.662 for counter=14 and
    #  increment = 17.
    self.assertAlmostEqual(0.724, dispersion([[2, 1, 0, 4, 3],
                                              [0, 4, 3, 1, 2],
                                              [4, 1, 2, 3, 0],
                                              [3, 1, 0, 2, 4],
                                              [4, 2, 1, 0, 3],
                                              [0, 4, 3, 2, 1]], 2), places=3)
    generator = SimsTablePermGenerator(n=5, m=2, counter=0, increment=1)
    self.assertAlmostEqual(0.551,
                           dispersion(list(generator.permutations(6)), 2),
                           places=3)
    generator = SimsTablePermGenerator(n=5, m=2, counter=14, increment=17)
    self.assertAlmostEqual(0.724,
                           dispersion(list(generator.permutations(6)), 2),
                           places=3)

    with self.assertRaisesRegex(AssertionError,
                                "Not all permutations have the same size"):
      dispersion([[0, 1, 2, 3, 4], [0, 1, 2]], 2)

  @unittest.skip("Should only be run manually for debugging")
  @staticmethod
  def test_best_increment():
    increments = list(range(1, 60))
    m = 0
    generators = [SimsTablePermGenerator(n=5, m=m, counter=0, increment=inc) for
                  inc in increments]
    first_6_permutations = [
      list(generator.permutations(6)) for generator in generators]
    dispersions = [dispersion(permutations, m) for permutations in
                   first_6_permutations]
    dispersion_and_increment = list(zip(dispersions, increments))
    dispersion_and_increment.sort()
    print(dispersion_and_increment)
    print()
    print(first_6_permutations[dispersion_and_increment[0][1]])
    print()
    print(first_6_permutations[dispersion_and_increment[-1][1]])

  def test_sims_table_permutations(self):
    all_cards = Card.get_all_cards()

    permutations = sims_table_perm_generator(all_cards[:6], 0, 10)
    self.assertEqual(10, len(permutations))
    self.assertEqual(len(set(tuple(p) for p in permutations)),
                     len(permutations))

    permutations = sims_table_perm_generator(all_cards[:6], 0, None)
    self.assertEqual(720, len(permutations))
    self.assertEqual(len(set(tuple(p) for p in permutations)),
                     len(permutations))

    permutations = sims_table_perm_generator(all_cards[:6], 4, None)
    self.assertEqual(30, len(permutations))
    self.assertEqual(len(set(tuple(p) for p in permutations)),
                     len(permutations))
    for i, permutation in enumerate(permutations):
      # noinspection PyTypeChecker
      self.assertEqual(sorted(permutation[:4]), permutation[:4], msg=i)

    # The number of requested permutations is higher than the total number of
    # permutations that can be generated.
    self.assertEqual(set(tuple(p) for p in permutations),
                     set(tuple(p) for p in
                         sims_table_perm_generator(all_cards[:6], 4, 70)))

    with self.assertRaises(AssertionError):
      sims_table_perm_generator(all_cards[:6], 20, 10)


class PermutationsEval(unittest.TestCase):
  @staticmethod
  def _time_it(perm_gen: PermutationsGenerator,
               cards_set: List[Card],
               num_opponent_unknown_cards: int,
               num_permutations_requested: int,
               num_runs: int) -> List[float]:
    timing_data = []
    for run_id in range(num_runs):
      if run_id % 10 == 0:
        print(".", end="", flush=True)
      start_time = time.process_time()
      permutations = perm_gen(cards_set, num_opponent_unknown_cards,
                              num_permutations_requested)
      end_time = time.process_time()
      assert len(permutations) > 0
      timing_data.append(end_time - start_time)
    return timing_data

  @staticmethod
  def _compute_metric(metric_name, func):
    # pylint: disable=too-many-locals
    cards = Card.get_all_cards()[:14]
    num_runs = 10
    permutations_generators = [random_perm_generator,
                               lexicographic_perm_generator,
                               sims_table_perm_generator]
    num_generators = len(permutations_generators)
    generator_columns = []
    series = []
    test_scenarios = [10, 20, 50, 100, 200, 500, 1000]
    for perm_generator in permutations_generators:
      name = perm_generator.__name__
      generator_columns.append(name)
      all_timing_data = []
      for num_permutations_requested in test_scenarios:
        timing_data = func(perm_generator, cards, 5, num_permutations_requested,
                           num_runs)
        all_timing_data.extend(timing_data)
      all_timing_data = pandas.Series(all_timing_data)
      all_timing_data.name = name
      series.append(all_timing_data)

    series_description = []
    for num_permutations_requested in test_scenarios:
      series_description.extend([num_permutations_requested] * num_runs)
    series.append(
      pandas.Series(data=series_description, name="test_scenarios"))

    dataframe = pandas.concat(series, axis=1)

    eval_data_folder = os.path.join(os.path.dirname(__file__), "eval", "data")
    # noinspection PyTypeChecker
    dataframe.to_csv(
      os.path.join(eval_data_folder, f"permutations_{metric_name}.csv"),
      index=False)

    dataframe.boxplot(column=generator_columns, by="test_scenarios",
                      layout=(1, num_generators),
                      figsize=(5 * num_generators, 5))
    plt.suptitle(f"{metric_name} data based on {num_runs} runs for each " +
                 "test_scenarios")
    plt.savefig(
      os.path.join(eval_data_folder, f"permutations_{metric_name}.png"))

  @unittest.skip("Should only be run manually for eval purposes")
  def test_time(self):
    self._compute_metric("time", self._time_it)

  @staticmethod
  def _measure_dispersion(perm_gen: PermutationsGenerator,
                          cards_set: List[Card],
                          num_opponent_unknown_cards: int,
                          num_permutations_requested: int,
                          num_runs: int) -> List[float]:
    dispersion_data = []
    for run_id in range(num_runs):
      if run_id % 10 == 0:
        print(".", end="", flush=True)
      permutations = perm_gen(cards_set, num_opponent_unknown_cards,
                              num_permutations_requested)
      dispersion_data.append(
        dispersion(permutations, num_opponent_unknown_cards))
    return dispersion_data

  @unittest.skip("Should only be run manually for eval purposes")
  def test_dispersion(self):
    self._compute_metric("dispersion", self._measure_dispersion)
