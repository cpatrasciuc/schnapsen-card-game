#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import multiprocessing
import os
import sys

from kivy.logger import Logger

if __name__ == "__main__":
  multiprocessing.freeze_support()
  root_dir = os.path.dirname(os.path.abspath(__file__))
  Logger.info("Main: Adding root dir to python path: %s", root_dir)
  sys.path.append(root_dir)

  from ui.schnapsen_app import SchnapsenApp

  SchnapsenApp().run()
