#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# cython: warn.maybe_uninitialized=False, warn.unused=False

import unittest

cimport openmp

from cython.parallel cimport prange, threadid

cdef (int, int) _test_openmp():
  cdef int num_threads = 0
  cdef int sum_thread_ids = 0
  cdef int i
  for i in prange(10, nogil=True, num_threads=10):
    num_threads = openmp.omp_get_num_threads()
    sum_thread_ids += threadid()
  return num_threads, sum_thread_ids


class OpenMPTest(unittest.TestCase):
  def test_openmp_support(self):
    cdef int num_threads, sum_thread_ids
    num_threads, sum_thread_ids = _test_openmp()
    print(f"Num threads: {num_threads}, sum_thread_ids: {sum_thread_ids}")
    self.assertEqual(10, num_threads)
    self.assertEqual(45, sum_thread_ids)
