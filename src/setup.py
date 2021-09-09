#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import os

from setuptools import setup, find_packages
from Cython.Build import cythonize


def _get_all_pyx_files():
  pyx_files = []
  for root, _, files in os.walk(r".\ai\cython_mcts_player"):
    for file in files:
      if file.endswith(".pyx"):
        pyx_files.append(os.path.join(root, file))
  return pyx_files


# TODO(cython): Read the doc and maybe add more compiler directives.
setup(
  packages=find_packages(),
  package_data={r"ai\cython_mcts_player": ["*.pxd"]},
  ext_modules=cythonize(_get_all_pyx_files(),
                        compiler_directives={"embedsignature": True,
                                             "language_level": 3},
                        annotate=True),
  zip_safe=False,
  include_package_data=True
)
