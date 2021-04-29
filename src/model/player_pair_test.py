#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from typing import List

from model.player_id import PlayerId
from model.player_pair import PlayerPair


class PlayerPairTest(unittest.TestCase):
  def test_pair_of_ints(self):
    test_pair: PlayerPair[int] = PlayerPair()
    self.assertIsNone(test_pair.one)
    self.assertIsNone(test_pair.two)
    test_pair.one = 100
    self.assertEqual(100, test_pair.one)
    self.assertIsNone(test_pair.two)
    test_pair.two = 200
    self.assertEqual(100, test_pair.one)
    self.assertEqual(200, test_pair.two)
    another_test_pair: PlayerPair[int] = PlayerPair()
    self.assertIsNone(another_test_pair.one)
    self.assertIsNone(another_test_pair.two)
    self.assertEqual(100, test_pair.one)
    self.assertEqual(200, test_pair.two)
    another_test_pair.one = 300
    self.assertEqual(300, another_test_pair.one)
    self.assertIsNone(another_test_pair.two)
    self.assertEqual(100, test_pair.one)
    self.assertEqual(200, test_pair.two)

  def test_pair_of_lists(self):
    test_pair: PlayerPair[List[int]] = PlayerPair()
    self.assertIsNone(test_pair.one)
    self.assertIsNone(test_pair.two)
    test_pair.one = [1, 2, 3]
    self.assertEqual([1, 2, 3], test_pair.one)
    self.assertIsNone(test_pair.two)
    test_pair.two = [2, 3, 4]
    self.assertEqual([1, 2, 3], test_pair.one)
    self.assertEqual([2, 3, 4], test_pair.two)
    another_test_pair: PlayerPair[List[int]] = PlayerPair()
    self.assertIsNone(another_test_pair.one)
    self.assertIsNone(another_test_pair.two)
    self.assertEqual([1, 2, 3], test_pair.one)
    self.assertEqual([2, 3, 4], test_pair.two)
    another_test_pair.one = [10, 20, 30]
    self.assertEqual([10, 20, 30], another_test_pair.one)
    self.assertIsNone(another_test_pair.two)
    self.assertEqual([1, 2, 3], test_pair.one)
    self.assertEqual([2, 3, 4], test_pair.two)

  def test_index_by_player_id(self):
    test_pair: PlayerPair[int] = PlayerPair(123, 345)
    self.assertEqual(123, test_pair.one)
    self.assertEqual(123, test_pair[PlayerId.ONE])
    self.assertEqual(345, test_pair.two)
    self.assertEqual(345, test_pair[PlayerId.TWO])
    test_pair[PlayerId.ONE] = 678
    self.assertEqual(678, test_pair.one)
    self.assertEqual(678, test_pair[PlayerId.ONE])
    self.assertEqual(345, test_pair.two)
    self.assertEqual(345, test_pair[PlayerId.TWO])
    test_pair[PlayerId.TWO] = 90
    self.assertEqual(678, test_pair.one)
    self.assertEqual(678, test_pair[PlayerId.ONE])
    self.assertEqual(90, test_pair.two)
    self.assertEqual(90, test_pair[PlayerId.TWO])

  def test_cannot_index_by_other_types(self):
    test_pair: PlayerPair[int] = PlayerPair(123, 345)
    with self.assertRaisesRegex(TypeError, "Keys must be of type PlayerId"):
      # noinspection PyTypeChecker
      print(test_pair[1])
    with self.assertRaisesRegex(TypeError, "Keys must be of type PlayerId"):
      # noinspection PyTypeChecker
      test_pair[1] = 100
    with self.assertRaisesRegex(TypeError, "Keys must be of type PlayerId"):
      # noinspection PyTypeChecker
      print(test_pair["string key"])
    with self.assertRaisesRegex(TypeError, "Keys must be of type PlayerId"):
      # noinspection PyTypeChecker
      test_pair["string key"] = 100
