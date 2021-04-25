#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from model.suit import Suit


class SuitTest(unittest.TestCase):
  def test_iterate_enum_elements(self):
    self.assertEqual(4, len(Suit))
    for suit in Suit:
      print(repr(suit), suit)

  def test_serialization(self):
    from pickle import dumps, loads
    for suit in Suit:
      self.assertEqual(suit, loads(dumps(suit)))

  def test_creation_from_int(self):
    with self.assertRaisesRegex(ValueError, "0 is not a valid Suit"):
      Suit(0)
    self.assertEqual(4, len(Suit))
    Suit(1)
    Suit(2)
    Suit(3)
    Suit(4)
    with self.assertRaisesRegex(ValueError, "5 is not a valid Suit"):
      Suit(5)
