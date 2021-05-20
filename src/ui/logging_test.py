#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest
from unittest.mock import Mock

from kivy import Logger, LOG_LEVELS


class LoggingTest(unittest.TestCase):
  @staticmethod
  def test_unused_log_messages_are_not_evaluated():
    mock = Mock()
    mock.__str__ = Mock(return_value="mock")

    Logger.setLevel(LOG_LEVELS["debug"])
    Logger.info("This is logged: Converts argument to string: %s", mock)
    mock.__str__.assert_called()
    mock.reset_mock()

    Logger.setLevel(LOG_LEVELS["error"])
    Logger.info(
      "This is not logged: Conversion to string should not happen: %s", mock)
    mock.__str__.assert_not_called()
