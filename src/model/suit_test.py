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

  def test_serialization(self):
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

  def test_from_char(self):
    self.assertEqual(Suit.HEARTS, Suit.from_char("h"))
    self.assertEqual(Suit.SPADES, Suit.from_char("s"))
    self.assertEqual(Suit.CLUBS, Suit.from_char("c"))
    self.assertEqual(Suit.DIAMONDS, Suit.from_char("d"))
    with self.assertRaisesRegex(KeyError, "z"):
      Suit.from_char("z")
    with self.assertRaisesRegex(AssertionError, "more_than_one_char"):
      Suit.from_char("more_than_one_char")
