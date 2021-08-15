#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import copy
import itertools
import math
import random
from typing import List, Callable, Optional

from model.card import Card

PermutationsGenerator = Callable[
  [List[Card], int, Optional[int]], List[List[Card]]]
"""
A function that receives the list of unknown cards, the number of unknown cards
in the opponent's hand (M) and an optional number of permutations requested (N).
It returns N permutations of unknown cards, where the first M are always sorted.
If N is None, it returns all possible permutations of unknown cards where the
first M are sorted.
"""

Rng = Callable[[], float]
"""
A random number generator that receives no arguments and returns a random number
in [0, 1).
"""


def random_perm_generator(cards_set: List[Card],
                          num_opponent_unknown_cards: int,
                          num_permutations_requested: Optional[int],
                          rng: Optional[Rng] = None) -> List[List[Card]]:
  """
  A simple implementation of a PermutationsGenerator. It generates permutations
  randomly where the first num_opponent_unknown_cards are sorted until it
  manages to generate num_permutations_requested unique examples.
  """
  assert num_opponent_unknown_cards <= len(cards_set)
  rng = rng or random.random
  permutations = set()
  if num_permutations_requested is None:
    num_unknown_cards = len(cards_set)
    num_permutations_requested = \
      math.comb(num_unknown_cards, num_opponent_unknown_cards) * \
      math.perm(num_unknown_cards - num_opponent_unknown_cards)
  while len(permutations) < num_permutations_requested:
    permutation = copy.deepcopy(cards_set)
    random.shuffle(permutation, rng)  # pylint: disable=deprecated-argument
    # noinspection PyTypeChecker
    permutation = sorted(permutation[:num_opponent_unknown_cards]) + \
                  permutation[num_opponent_unknown_cards:]
    permutations.add(tuple(permutation))
  permutations = list(list(p) for p in permutations)
  return permutations


def lexicographic_perm_generator(
    cards_set: List[Card],
    num_opponent_unknown_cards: int,
    num_permutations_requested: Optional[int]) -> List[List[Card]]:
  """
  A PermutationsGenerator that generates permutations in lexicographic order:
  for each sorted combination of num_opponent_unknown_cards from cards_set, it
  generates all possible permutations of remaining cards. It stops as soon as
  it reaches num_permutations_requested, if num_permutations_requested is not
  None and smaller than the total number of permutations that can be generated.
  TODO(permutations): Add the advantages and disadvantages for each method.
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
