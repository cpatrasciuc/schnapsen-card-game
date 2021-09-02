#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from main_wrapper import main_wrapper


class MainWrapperTest(unittest.TestCase):
  @staticmethod
  def test_success():
    main_wrapper(lambda: print("Success"))

  @staticmethod
  def test_exception():
    main_wrapper(lambda: print(10 / 0))
