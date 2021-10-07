#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from main_wrapper import main_wrapper


class MainWrapperTest(unittest.TestCase):
  def test_success(self):
    self.assertEqual(0, main_wrapper(lambda: print("Success")))

  def test_exception(self):
    self.assertEqual(1, main_wrapper(lambda: print(10 / 0)))
