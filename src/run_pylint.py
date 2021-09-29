#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import os
import subprocess
import sys

from main_wrapper import main_wrapper


def get_all_python_files():
  py_files = []
  for root, _, files in os.walk("."):
    for file in files:
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
  generated_members = [
    r"kivy.*setter",
    r"ui\..*(Widget|Layout|ScoreView)\.bind",
    r"ui\..*(Widget|Layout)\.dispatch",
    r"ui\..*(Widget|Layout)\.fbind",
    r"ui\..*(Widget|Layout)\.register_event_type",
    r"ui\..*(Widget|Layout)\.setter",
    r"ui\.game_options\.GameOptions\..*",
  ]
  extension_pkgs = [
    "ai.cython_mcts_player.mcts_debug",
    "ai.cython_mcts_player.player",
  ]
  pylint_opts = [
    "--indent-string='  '",
    "--ignore-imports=yes",
    "--generated-members=" + ",".join(generated_members),
    "-j 0",  # Run in parallel on all available processors
    "--disable=" + ",".join(disabled_checks),
    "--good-names=i,j,k,q,n,ex,Run,_,ax",
    "--extension-pkg-allow-list=" + ",".join(extension_pkgs)
  ]

  # Call pylint in a subprocess since it's licensed under GPL. Do not import it.
  cmd = [sys.executable, "-m", "pylint"] + pylint_opts + get_all_python_files()
  subprocess.run(cmd, check=True)


if __name__ == "__main__":
  main_wrapper(run_pylint)
