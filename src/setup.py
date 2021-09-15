#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import os

from Cython.Build import cythonize
from Cython.Compiler import Options
from setuptools import Extension, setup, find_packages

Options.fast_fail = True
Options.warning_errors = True
Options.error_on_unknown_names = True
Options.error_on_uninitialized = True

ENABLE_PROFILING = False

ext_modules = [
  Extension(
    name="*",
    sources=[os.path.join("ai", "cython_mcts_player", "*.pyx")],
    define_macros=[("CYTHON_TRACE_NOGIL", "1")] if ENABLE_PROFILING else []
  )
]

setup(
  packages=find_packages(),
  package_data={os.path.join("ai", "cython_mcts_player"): ["*.pxd"]},
  ext_modules=cythonize(ext_modules,
                        compiler_directives={
                          "embedsignature": True,
                          "language_level": 3,
                          "warn.maybe_uninitialized": True,
                          "warn.unused": True,
                          "always_allow_keywords": False,
                          "cdivision": True,
                          "cdivision_warnings": True,
                          "nonecheck": False,
                          "boundscheck": False,
                          "wraparound": False,
                          "profile": ENABLE_PROFILING,
                          "linetrace": ENABLE_PROFILING,
                        },
                        force=True,
                        annotate=True),
  zip_safe=False,
  include_package_data=True
)
