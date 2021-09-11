#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import unittest

from ai.cython_mcts_player.card cimport Suit
from ai.cython_mcts_player.game_state cimport GameState, from_python_game_state
from ai.cython_mcts_player.player_action cimport ActionType
from ai.cython_mcts_player.mcts cimport build_tree, Node, MAX_CHILDREN, \
  debug_str
from model.game_state_test_utils import \
  get_game_state_for_you_first_no_you_first_puzzle


class MctsTest(unittest.TestCase):
  def test_you_first_no_you_first(self):
    cdef GameState game_state = from_python_game_state(
      get_game_state_for_you_first_no_you_first_puzzle())
    cdef Node *root_node = build_tree(&game_state, -1, 0)
    self.assertTrue(root_node.parent == NULL)
    self.assertFalse(root_node.terminal)
    self.assertEqual(0, root_node.player)
    self.assertFalse(root_node.fully_simulated)
    cdef int i
    for i in range(7):
      if root_node.actions[i].action_type == ActionType.NO_ACTION:
        break
      if root_node.children[i] == NULL:
        continue
      print(root_node.actions[i], " --> ", debug_str(root_node.children[i]))
      self.assertTrue(root_node.children[i].fully_simulated)
      self.assertEqual(1, root_node.children[i].player)
      self.assertAlmostEqual(
        0.33 if root_node.actions[i].card.suit == Suit.HEARTS else -0.33,
        root_node.children[i].ucb,
        delta=0.01, msg=str(root_node.actions[i]))
