#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from model.player_id import PlayerId
from model.player_pair import PlayerPair


class PlayerPairTest(unittest.TestCase):
  def test_pair_of_ints(self):
    p: PlayerPair[int] = PlayerPair()
    self.assertIsNone(p.one)
    self.assertIsNone(p.two)
    p.one = 100
    self.assertEqual(100, p.one)
    self.assertIsNone(p.two)
    p.two = 200
    self.assertEqual(100, p.one)
    self.assertEqual(200, p.two)
    p2: PlayerPair[int] = PlayerPair()
    self.assertIsNone(p2.one)
    self.assertIsNone(p2.two)
    self.assertEqual(100, p.one)
    self.assertEqual(200, p.two)
    p2.one = 300
    self.assertEqual(300, p2.one)
    self.assertIsNone(p2.two)
    self.assertEqual(100, p.one)
    self.assertEqual(200, p.two)

  def test_pair_of_lists(self):
    p: PlayerPair[list[int]] = PlayerPair()
    self.assertIsNone(p.one)
    self.assertIsNone(p.two)
    p.one = [1, 2, 3]
    self.assertEqual([1, 2, 3], p.one)
    self.assertIsNone(p.two)
    p.two = [2, 3, 4]
    self.assertEqual([1, 2, 3], p.one)
    self.assertEqual([2, 3, 4], p.two)
    p2: PlayerPair[int] = PlayerPair()
    self.assertIsNone(p2.one)
    self.assertIsNone(p2.two)
    self.assertEqual([1, 2, 3], p.one)
    self.assertEqual([2, 3, 4], p.two)
    p2.one = [10, 20, 30]
    self.assertEqual([10, 20, 30], p2.one)
    self.assertIsNone(p2.two)
    self.assertEqual([1, 2, 3], p.one)
    self.assertEqual([2, 3, 4], p.two)

  def test_index_by_player_id(self):
    p: PlayerPair[int] = PlayerPair(123, 345)
    self.assertEqual(123, p.one)
    self.assertEqual(123, p[PlayerId.ONE])
    self.assertEqual(345, p.two)
    self.assertEqual(345, p[PlayerId.TWO])
    p[PlayerId.ONE] = 678
    self.assertEqual(678, p.one)
    self.assertEqual(678, p[PlayerId.ONE])
    self.assertEqual(345, p.two)
    self.assertEqual(345, p[PlayerId.TWO])
    p[PlayerId.TWO] = 90
    self.assertEqual(678, p.one)
    self.assertEqual(678, p[PlayerId.ONE])
    self.assertEqual(90, p.two)
    self.assertEqual(90, p[PlayerId.TWO])

  def test_cannot_index_by_other_types(self):
    p: PlayerPair[int] = PlayerPair(123, 345)
    with self.assertRaisesRegex(TypeError, "Keys must be of type PlayerId"):
      print(p[1])
    with self.assertRaisesRegex(TypeError, "Keys must be of type PlayerId"):
      p[1] = 100
    with self.assertRaisesRegex(TypeError, "Keys must be of type PlayerId"):
      print(p["string key"])
    with self.assertRaisesRegex(TypeError, "Keys must be of type PlayerId"):
      p["string key"] = 100
