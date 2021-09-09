#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from setuptools import setup
from Cython.Build import cythonize

# TODO(cython): Read the doc and maybe add more compiler directives.
setup(
  ext_modules=cythonize(r"ai\cython_mcts_player\primes.pyx",
                        compiler_directives={"embedsignature": True,
                                             "language_level": 3},
                        annotate=True)
)
