#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

# Import all Cython tests so they are discovered by unittest.

# pylint: disable=no-name-in-module,unused-import,wildcard-import

from ai.cython_mcts_player.card_test import *
from ai.cython_mcts_player.game_state_test import *
from ai.cython_mcts_player.mcts_test import *
from ai.cython_mcts_player.player_action_test import *
