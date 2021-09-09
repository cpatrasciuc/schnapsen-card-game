#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from ai.cython_mcts_player import run_primes


class PrimesTest(unittest.TestCase):
  def test(self):
    self.assertEqual([2, 3, 5, 7, 11, 13, 17, 19, 23, 29], run_primes(10))
