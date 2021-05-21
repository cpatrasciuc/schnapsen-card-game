#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import os
import subprocess
import sys
import unittest


class DebuggableWidgetTest(unittest.TestCase):
  def _run_test_module_with_debug_mode(self, debug_mode=True):
    # pylint: disable=subprocess-run-check
    file_name = os.path.join(
      os.path.dirname(__file__), "debuggable_widget_test_module.py")

    if debug_mode:
      args = [sys.executable, file_name]
    else:
      args = [sys.executable, "-O", file_name]
    completed_process = subprocess.run(args, capture_output=True)

    print(str(completed_process.stdout))
    print(str(completed_process.stderr))

    self.assertEqual(0, completed_process.returncode, msg=completed_process)
    self.assertNotRegex(str(completed_process.stderr), "Exception")
    self.assertRegex(str(completed_process.stdout), "SUCCESS")

  def test_works_in_debug_mode(self):
    self._run_test_module_with_debug_mode(True)

  def test_works_in_non_debug_mode(self):
    self._run_test_module_with_debug_mode(False)
