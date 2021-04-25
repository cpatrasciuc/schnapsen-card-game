#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from model.card_value import CardValue


class CardValueTest(unittest.TestCase):
  def test_enumerate_card_values(self):
    self.assertEqual(5, len(list(CardValue)))
    for card_value in CardValue:
      print(repr(card_value), card_value)

  def test_serialization(self):
    from pickle import dumps, loads
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
