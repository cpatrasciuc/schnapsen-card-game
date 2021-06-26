#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from pickle import loads, dumps

from model.card_value import CardValue


class CardValueTest(unittest.TestCase):
  def test_enumerate_card_values(self):
    self.assertEqual(5, len(list(CardValue)))
    for card_value in CardValue:
      print(repr(card_value), card_value)

  def test_serialization(self):
    for card_value in CardValue:
      self.assertEqual(card_value, loads(dumps(card_value)))

  def test_creation_by_value(self):
    self.assertEqual(CardValue.ACE, CardValue(11))
    self.assertEqual(CardValue.TEN, CardValue(10))
    self.assertEqual(CardValue.KING, CardValue(4))
    self.assertEqual(CardValue.QUEEN, CardValue(3))
    self.assertEqual(CardValue.JACK, CardValue(2))
    with self.assertRaisesRegex(ValueError, "5 is not a valid CardValue"):
      CardValue(5)
    with self.assertRaisesRegex(ValueError, "0 is not a valid CardValue"):
      CardValue(0)

  def test_from_char(self):
    self.assertEqual(CardValue.ACE, CardValue.from_char("a"))
    self.assertEqual(CardValue.TEN, CardValue.from_char("t"))
    self.assertEqual(CardValue.KING, CardValue.from_char("k"))
    self.assertEqual(CardValue.QUEEN, CardValue.from_char("q"))
    self.assertEqual(CardValue.JACK, CardValue.from_char("j"))
    with self.assertRaisesRegex(KeyError, "m"):
      CardValue.from_char("m")
    with self.assertRaisesRegex(AssertionError, "k_multiple_chars"):
      CardValue.from_char("k_multiple_chars")
