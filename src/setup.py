#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import platform

from setuptools import Extension, setup, find_packages
from Cython.Build import cythonize
from Cython.Compiler import Options

Options.fast_fail = True
Options.warning_errors = True
Options.error_on_unknown_names = True
Options.error_on_uninitialized = True

OPENMP_FLAG = "/openmp" if platform.system() == "Windows" else "-fopenmp"

ext_modules = [
  Extension(
    name="*",
    sources=[r"ai/cython_mcts_player/*.pyx"],
    extra_compile_args=[OPENMP_FLAG],
  )
]

setup(
  packages=find_packages(),
  package_data={r"ai/cython_mcts_player": ["*.pxd"]},
  ext_modules=cythonize(ext_modules,
                        compiler_directives={"embedsignature": True,
                                             "language_level": 3,
                                             "warn.maybe_uninitialized": True,
                                             "warn.unused": True,
                                             "always_allow_keywords": False,
                                             "cdivision": True,
                                             "cdivision_warnings": True},
                        annotate=True),
  zip_safe=False,
  include_package_data=True
)
