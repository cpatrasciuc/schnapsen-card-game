#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import os

import pylint.lint


def get_all_python_files():
  py_files = []
  for root, _, files in os.walk("."):
    for file in files:
      # TODO(uidemo): Remove this up after deleting the UI demo.
      if os.path.basename(root) == "uidemo":
        continue
      if file.endswith(".py"):
        py_files.append(os.path.join(root, file))
  return py_files


def run_pylint():
  disabled_checks = [
    "missing-module-docstring",
    "missing-class-docstring",
    "missing-function-docstring",
    "fixme",
    "locally-disabled"
  ]
  pylint_opts = [
    "--indent-string='  '",
    "-j 0",  # Run in parallel on all available processors
    "--disable=" + ",".join(disabled_checks),
  ]
  pylint.lint.Run(pylint_opts + get_all_python_files())


if __name__ == "__main__":
  run_pylint()
