#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import os
import unittest

import coverage


def run_all_tests_with_coverage() -> float:
  """
  Runs all tests with code coverage generates an HTML and a text report.
  Based on this: https://coverage.readthedocs.io/en/coverage-5.5/api.html#api
  :return The coverage percentage.
  """
  current_dir = os.getcwd()
  tests_file_pattern = "*_test.py"
  current_file = os.path.basename(__file__)
  cov = coverage.Coverage(branch=True, source=[current_dir],
                          omit=[tests_file_pattern, current_file])
  cov.start()

  # Discover and run all tests.
  loader = unittest.TestLoader()
  tests = loader.discover(current_dir, pattern=tests_file_pattern)
  test_runner = unittest.runner.TextTestRunner()
  test_runner.run(tests)

  cov.stop()
  cov.save()

  # Generate the html report.
  html_report_dir = os.path.join(current_dir, "htmlcov")
  cov.html_report(directory=html_report_dir)
  html_path = "file:///%s/index.html" % "/".join(
    os.path.abspath(html_report_dir).split("\\"))

  # Print a text report to stdout.
  print()
  pct_covered = cov.report(skip_empty=True, skip_covered=True,
                           show_missing=True)
  print("\nOutput saved to: %s" % html_path)
  
  return pct_covered


if __name__ == "__main__":
  run_all_tests_with_coverage()
