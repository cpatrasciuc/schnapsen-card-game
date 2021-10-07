#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import datetime
import logging
import time
import traceback
from typing import Callable


def _time_diff(start_time: float, end_time: float):
  return datetime.timedelta(seconds=end_time - start_time)


def main_wrapper(main: Callable[[], None], log_level=None) -> int:
  """
  Wrapper that can be used before calling a main() function to setup the logging
  level and measure its duration.
  """
  if log_level is None:
    if __debug__:
      log_level = logging.DEBUG
    else:
      log_level = logging.INFO
  logging.basicConfig(level=log_level)
  start_time = time.time()
  start_process_time = time.process_time()
  result = 0
  # noinspection PyBroadException
  try:
    main()
  except Exception:  # pylint: disable=broad-except
    traceback.print_exc()
    result = 1
  end_time = time.time()
  end_process_time = time.process_time()
  print(f"Duration (time): {_time_diff(start_time, end_time)}")
  process_time_diff = _time_diff(start_process_time, end_process_time)
  print(f"Duration (process_time): {process_time_diff}")
  return result
