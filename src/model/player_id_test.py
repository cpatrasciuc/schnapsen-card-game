#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from model.player_id import PlayerId


class PlayerIdTest(unittest.TestCase):
  def test_creation_from_int(self):
    """Make sure you cannot create invalid player IDs through int args."""
    with self.assertRaisesRegex(ValueError, "0 is not a valid PlayerId"):
      PlayerId(0)
    PlayerId(1)
    PlayerId(2)
    with self.assertRaisesRegex(ValueError, "3 is not a valid PlayerId"):
      PlayerId(3)

  def test_opponent(self):
    self.assertEqual(PlayerId.ONE, PlayerId.TWO.opponent())
    self.assertEqual(PlayerId.TWO, PlayerId.ONE.opponent())
