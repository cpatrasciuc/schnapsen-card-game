#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# pylint: disable=invalid-name

import itertools
import logging
import math
import random
from typing import List, Callable, Optional, Generator, TypeVar, Any

from model.card import Card

_T = TypeVar("_T")
Permutation = List[_T]


def distance(p1: Permutation, p2: Permutation, m: int, w: float = 2) -> float:
  """
  A metric used to measure the distance between two permutations. It has two
  components:
    * it checks how many elements are different in the first m elements, while
      discarding order;
    * it checks the differences in the remaining elements, while taking order
      into account and giving less weight to differences towards the end of the
      permutations.
  :param w: Weight used to balance the two components above in the final metric.
  """
  assert len(p1) == len(p2), (p1, p2)
  n = len(p1)
  if m > 0:
    diffs_in_first_m = m - len(set(p1[:m]).intersection(set(p2[:m])))
    first_term = diffs_in_first_m / m
  else:
    first_term = 0
  second_term = 0
  for i in range(m, n):
    if p1[i] == p2[i]:
      continue
    second_term += (2 ** math.ceil((n - 1 - i) / 2))
  second_term *= 1 / (4 * (2 ** ((n - m - 1) / 2)) - 3)
  final_metric = (w * first_term + 1 * second_term) / (w + 1)
  return final_metric


def dispersion(permutations: List[Permutation], m: int) -> float:
  """
  The arithmetic mean of the distances between all possible pairs of
  permutations from the given list, normalized to the interval [0, 1], with 1
  meaning that all pairs of permutations have the maximal distance of 1 and 0
  that all permutations are identical.
  :param permutations: The list of permutations on which to compute the metric.
  All permutations must have the same length.
  :param m: See the meaning of parameter m in distance().
  """
  assert len(set(len(permutation) for permutation in permutations)) == 1, \
    "Not all permutations have the same size"
  result = 0
  num_permutations = len(permutations)
  for i in range(num_permutations - 1):
    for j in range(i + 1, num_permutations):
      result += distance(permutations[i], permutations[j], m)
  return result * 2 / (num_permutations * (num_permutations - 1))


PermutationsGenerator = Callable[
  [List[Card], int, Optional[int]], List[List[Card]]]
"""
A function that receives the list of unknown cards, the number of unknown cards
in the opponent's hand (M) and an optional number of permutations requested (N).
It returns N permutations of unknown cards, where the first M are always sorted.
If N is None, it returns all possible permutations of unknown cards where the
first M are sorted.
"""


def random_perm_generator(cards_set: List[Card],
                          num_opponent_unknown_cards: int,
                          num_permutations_requested: Optional[int],
                          seed: Optional[Any] = None) -> List[
  Permutation[Card]]:
  """
  A simple implementation of a PermutationsGenerator. It generates permutations
  randomly where the first num_opponent_unknown_cards are sorted until it
  manages to generate num_permutations_requested unique examples.
  Advantages: High dispersion. Fast for a small number of permutations.
  Disadvantages: Slow for a high number of permutations requested (e.g., 1000).
  """
  assert num_opponent_unknown_cards <= len(cards_set)
  rng = random.Random(seed)
  permutations = set()
  if num_permutations_requested is None:
    num_unknown_cards = len(cards_set)
    num_permutations_requested = \
      math.comb(num_unknown_cards, num_opponent_unknown_cards) * \
      math.perm(num_unknown_cards - num_opponent_unknown_cards)
  while len(permutations) < num_permutations_requested:
    permutation = [card.copy() for card in cards_set]
    rng.shuffle(permutation)
    # noinspection PyTypeChecker
    permutation = sorted(permutation[:num_opponent_unknown_cards]) + \
                  permutation[num_opponent_unknown_cards:]
    permutations.add(tuple(permutation))
  permutations = list(list(p) for p in permutations)
  return permutations


def lexicographic_perm_generator(
    cards_set: List[Card],
    num_opponent_unknown_cards: int,
    num_permutations_requested: Optional[int]) -> List[Permutation[Card]]:
  """
  A PermutationsGenerator that generates permutations in lexicographic order:
  for each sorted combination of num_opponent_unknown_cards from cards_set, it
  generates all possible permutations of remaining cards. It stops as soon as
  it reaches num_permutations_requested, if num_permutations_requested is not
  None and smaller than the total number of permutations that can be generated.
  Advantages: Very fast, even for a high number of permutations requested.
  Disadvantages: Very very low dispersion.
  """
  assert num_opponent_unknown_cards <= len(cards_set)
  permutations = []
  for opponent_cards in itertools.combinations(cards_set,
                                               num_opponent_unknown_cards):
    remaining_cards = set(cards_set) - set(opponent_cards)
    for remaining_cards_permutation in itertools.permutations(remaining_cards):
      permutations.append(
        list(opponent_cards) + list(remaining_cards_permutation))
      if num_permutations_requested is not None:
        if len(permutations) >= num_permutations_requested:
          return permutations
  return permutations


def _is_relative_prime(x: int, y: int) -> bool:
  if x == 0 or y == 0:
    return False
  for d in range(2, math.isqrt(max(x, y)) + 1):
    if x % d == 0 and y % d == 0:
      return False
  return True


def _next_relative_prime(i: int, r: int) -> int:
  """
  Takes integers i, r as input and returns the smallest integer i' ≥ i, which is
  relative prime to r.
  """
  while not _is_relative_prime(i, r):
    i += 1
  if i >= r:
    i = i % r
    assert _is_relative_prime(i, r)
  return i


MixedRadixNumber = List[int]
"""The order of digits is from the least significant to the most significant."""


class SimsTablePermGenerator:
  def __init__(self, n: int, m: int = 0, counter: Optional[int] = None,
               increment: Optional[int] = None):
    """
    A permutation generator based on Sims tables. This is described here:
    https://psellos.com/schnapsen/blog/2012/07/sims.html
    http://doi.ieeecomputersociety.org/10.1109/ICTAI.2010.76

    It generates permutations of [0, 1, ..., n-1], where the order of the first
    m entries doesn't matter.

    :param counter: If given, it is used as a seed that defines the first
    permutation that will be generated. If not given, it will be initialized
    randomly.
    :param increment: An integer used to define the order in which the
    following permutations are generated. If None, it will be initialized with a
    value that maximizes the dispersion.
    """
    assert 0 <= m <= n, (n, m)
    self._n = n
    self._m = m
    self._r = math.factorial(self._n) // math.factorial(self._m)
    self._counter = counter if m != n else 0
    if counter is None:
      self._counter = random.randint(0, self._r - 1)
    # TODO(optimization): Maybe precompute this for all (n, m) combinations in a
    #  game of Schnapsen.
    self._increment = increment or self._find_best_increment()
    assert self._increment > 0, self._increment

  def _find_best_increment(self, max_searches: int = 100) -> int:
    if self._n in (self._m, 1):
      return 1  # It doesn't matter. There will be only one permutation.
    num_searches = min(self._r - 1, max_searches)
    possible_increments = list(
      set(_next_relative_prime(random.randint(0, self._r - 1), self._r) for _ in
          range(num_searches)))

    def dispersion_of_first_6_permutations(inc):
      first_6_permutations = \
        [self.generate_permutation(x) for x in
         [(self._counter + k * inc) % self._r for k in range(6)]]
      return dispersion(first_6_permutations, self._m)

    dispersion_and_increments = \
      [(dispersion_of_first_6_permutations(inc), inc) for inc in
       possible_increments]
    dispersion_and_increments.sort()
    best_dispersion, best_increment = dispersion_and_increments[-1]
    # pylint: disable=logging-not-lazy
    logging.info("SimsTablePermGenerator: For n=%s, m=%s, r=%s, counter=%s, " +
                 "the best increment found was %s with dispersion %.3f.",
                 self._n, self._m, self._r, self._counter, best_increment,
                 best_dispersion)
    # pylint: enable=logging-not-lazy
    return best_increment

  def convert_to_mixed_radix(self, c: int) -> MixedRadixNumber:
    """
    Converts a decimal number (mod r) in the mixed radix number format, with
    radices [n-1, n-2, ..., m].
    :param c: Decimal number to be converted.
    """
    assert c < self._r, (c, self._r)
    mixed_radix_number = []
    for i in range(self._m, self._n):
      mixed_radix_number.append(c % (i + 1))
      c = c // (i + 1)
    return mixed_radix_number

  def generate_permutation(self, c: int,
                           sort_first_m: bool = True) -> List[int]:
    """
    Takes an integer c (mod r) as input and returns the corresponding
    permutation. It does so by converting c into the mixed radix number and
    multiplying the respective permutations from the Sims table.
    """
    mixed_radix_number = self.convert_to_mixed_radix(c)
    permutation = list(range(self._n))
    for radix, radix_index in enumerate(reversed(mixed_radix_number)):
      sims_after = self._n - 1 - radix
      sims_before = sims_after - radix_index
      tmp = permutation[sims_after]
      permutation[sims_after] = permutation[sims_before]
      permutation[sims_before] = tmp
    if not sort_first_m:
      return permutation
    return list(sorted(permutation[:self._m])) + permutation[self._m:]

  def permutations(self, num_requested: Optional[int] = None) -> Generator[
    Permutation[int], None, None]:
    """
    Generates all the permutations.
    :param num_requested: If given, this method will only generate the first
    num_requested permutations.
    """
    num_permutations_generated = 0
    num_permutations_to_generate = min(self._r, num_requested or self._r)
    while num_permutations_generated < num_permutations_to_generate:
      yield self.generate_permutation(self._counter)
      self._counter = (self._counter + self._increment) % self._r
      num_permutations_generated += 1


# TODO(optimization): Find out where do we spend most of the CPU time in
#  sims_table_perm_generator.
def sims_table_perm_generator(
    cards_set: List[Card],
    num_opponent_unknown_cards: int,
    num_permutations_requested: Optional[int]) -> List[Permutation[Card]]:
  """
  A PermutationsGenerator that tries to generate the permutations in an order
  that maximizes dispersion.
  Advantages: High dispersion. Faster than random_perm_generator for a high
  number of permutations requested.
  Disadvantages: Slower than random_perm_generator for a small number of
  permutations requested, without providing a lot more dispersion.
  """
  assert num_opponent_unknown_cards <= len(cards_set)
  perm_generator = SimsTablePermGenerator(len(cards_set),
                                          num_opponent_unknown_cards)
  permutations = list(perm_generator.permutations(num_permutations_requested))
  return [[cards_set[i] for i in permutation] for permutation in permutations]
