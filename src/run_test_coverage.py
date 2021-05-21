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
  tests_file_pattern = "*_test.py"
  cov = coverage.Coverage(branch=True, source=["./model", "./ui"],
                          omit=[tests_file_pattern,
                                "model/game_state_validation_test_module.py",
                                "ui/debuggable_widget_test_module.py"])
  cov.exclude("def __repr__", "exclude")
  cov.exclude('if __name__ == "__main__"', "exclude")
  cov.exclude("if __name__ == '__main__'", "exclude")
  cov.start()

  # Discover and run all tests.
  loader = unittest.TestLoader()
  tests = loader.discover(os.getcwd(), pattern=tests_file_pattern)
  test_runner = unittest.runner.TextTestRunner()
  result = test_runner.run(tests)
  if not result.wasSuccessful():
    print(result.errors)
    print(result.failures)
    print("\nTests failed. Coverage report will not be generated.")
    return -1

  cov.stop()
  cov.save()

  # Generate the html report.
  html_report_dir = "htmlcov"
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
