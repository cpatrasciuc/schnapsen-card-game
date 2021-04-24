#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from pickle import loads, dumps

from model.suit import Suit


class SuitTest(unittest.TestCase):
  def test_iterate_enum_elements(self):
    self.assertEqual(4, len(Suit))
    for suit in Suit:
      print(repr(suit), suit)

  def test_serializable(self):
    for suit in Suit:
      self.assertEqual(suit, loads(dumps(suit)))
