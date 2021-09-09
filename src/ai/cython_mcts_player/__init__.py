#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# pylint: disable=no-name-in-module

from .primes import primes


def run_primes(n):
  print(primes.__doc__)
  return primes(n)
