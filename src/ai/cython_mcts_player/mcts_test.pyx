#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import random
import unittest

from ai.cython_mcts_player.card cimport Card, CardValue, Suit
from ai.cython_mcts_player.game_state cimport GameState, is_game_over, \
  from_python_game_state, game_points, Points
from ai.cython_mcts_player.player_action cimport ActionType, PlayerAction, \
  execute, from_python_player_action
from ai.cython_mcts_player.mcts cimport build_tree, Node, MAX_CHILDREN, \
  debug_str, best_actions_for_tests, delete_tree
from model.card import Card as PyCard
from model.card_value import CardValue as PyCardValue
from model.game_state_test_utils import \
  get_game_state_for_you_first_no_you_first_puzzle, \
  get_game_state_for_elimination_play_puzzle, \
  get_game_state_for_playing_to_win_the_last_trick_puzzle, \
  get_game_state_for_tempo_puzzle, get_game_state_for_who_laughs_last_puzzle, \
  get_game_state_for_forcing_the_issue_puzzle
from model.player_action import PlayCardAction
from model.player_id import PlayerId as PyPlayerId
from model.suit import Suit as PySuit


class MctsTest(unittest.TestCase):
  def test_you_first_no_you_first(self):
    cdef GameState game_state = from_python_game_state(
      get_game_state_for_you_first_no_you_first_puzzle())
    cdef Node *root_node = build_tree(&game_state, max_iterations=-1,
                                      exploration_param=0,
                                      select_best_child=False)
    self.assertTrue(root_node.parent == NULL)
    self.assertFalse(root_node.terminal)
    self.assertEqual(0, root_node.player)
    self.assertFalse(root_node.fully_simulated)
    cdef int i
    for i in range(MAX_CHILDREN):
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
    delete_tree(root_node)

  def test_elimination_play_player_one(self):
    cdef GameState game_state = from_python_game_state(
      get_game_state_for_elimination_play_puzzle())
    cdef Node *root_node = build_tree(&game_state, max_iterations=-1,
                                      exploration_param=0,
                                      select_best_child=False)
    cdef int i
    for i in range(MAX_CHILDREN):
      if root_node.actions[i].action_type == ActionType.NO_ACTION:
        break
      if root_node.children[i] == NULL:
        continue
      print(root_node.actions[i], " --> ", debug_str(root_node.children[i]))
      self.assertTrue(root_node.children[i].fully_simulated)
      self.assertEqual(1, root_node.children[i].player)
      self.assertAlmostEqual(
        0.33 if root_node.actions[i].card.suit == Suit.HEARTS else -0.33,
        root_node.children[i].ucb, delta=0.01, msg=str(root_node.actions[i]))
    delete_tree(root_node)

  def test_elimination_play_player_two(self):
    cdef GameState game_state = from_python_game_state(
      get_game_state_for_elimination_play_puzzle())
    cdef PlayerAction action = PlayerAction(ActionType.PLAY_CARD, 0,
                                            Card(Suit.CLUBS, CardValue.JACK))
    game_state = execute(&game_state, action)
    action = PlayerAction(ActionType.PLAY_CARD, 1,
                          Card(Suit.CLUBS, CardValue.KING))
    game_state = execute(&game_state, action)
    self.assertEqual(34, game_state.trick_points[0])
    self.assertEqual(40, game_state.trick_points[1])
    cdef Node *root_node = build_tree(&game_state, max_iterations=-1,
                                      exploration_param=0,
                                      select_best_child=False)
    cdef int i
    for i in range(MAX_CHILDREN):
      if root_node.actions[i].action_type == ActionType.NO_ACTION:
        break
      if root_node.children[i] == NULL:
        continue
      print(root_node.actions[i], " --> ", debug_str(root_node.children[i]))
      self.assertTrue(root_node.children[i].fully_simulated)
      self.assertEqual(0, root_node.children[i].player)
      self.assertAlmostEqual(0.33, root_node.children[i].ucb, delta=0.01,
                             msg=action)
    delete_tree(root_node)

  def _assert_player_one_always_wins(self, py_game_state):
    cdef GameState game_state = from_python_game_state(py_game_state)
    cdef Node *root_node
    cdef int i
    while not is_game_over(&game_state):
      root_node = build_tree(&game_state, max_iterations=-1,
                             exploration_param=0, select_best_child=False)
      print()
      for i in range(MAX_CHILDREN):
        if root_node.actions[i].action_type == ActionType.NO_ACTION:
          break
        if root_node.children[i] == NULL:
          continue
        print(root_node.actions[i], " --> ", debug_str(root_node.children[i]))
        self.assertTrue(root_node.children[i].fully_simulated,
                        msg=str(root_node.actions[i]))
      best_action = random.choice(best_actions_for_tests(root_node))
      print(f"{game_state.next_player}: {best_action}")
      game_state = execute(&game_state, best_action)
      delete_tree(root_node)
    cdef Points score_p1, score_p2
    score_p1, score_p2 = game_points(&game_state)
    self.assertEqual(0, score_p2)
    self.assertGreater(score_p1, 0)

  def test_elimination_play_player_one_always_wins(self):
    game_state = get_game_state_for_elimination_play_puzzle()
    self._assert_player_one_always_wins(game_state)

  def test_playing_to_win_the_last_trick_player_one_always_wins(self):
    game_state = get_game_state_for_playing_to_win_the_last_trick_puzzle()
    self._assert_player_one_always_wins(game_state)

  def test_tempo_player_one_always_wins(self):
    game_state = get_game_state_for_tempo_puzzle()
    self._assert_player_one_always_wins(game_state)

  def test_who_laughs_last_part_two_player_one_always_wins(self):
    py_game_state = get_game_state_for_who_laughs_last_puzzle()
    cdef GameState game_state = from_python_game_state(py_game_state)
    cdef Node *root_node = build_tree(&game_state, max_iterations=-1,
                                      exploration_param=0,
                                      select_best_child=False)
    cdef list actions = best_actions_for_tests(root_node)
    cdef int i
    for i in range(MAX_CHILDREN):
      if root_node.actions[i].action_type == ActionType.NO_ACTION:
        break
      if root_node.children[i] == NULL:
        continue
      print(root_node.actions[i], " --> ", debug_str(root_node.children[i]))
    py_action = PlayCardAction(PyPlayerId.ONE,
                               PyCard(PySuit.HEARTS, PyCardValue.KING))
    self.assertEqual([from_python_player_action(py_action)], actions)
    game_state = execute(&game_state, actions[0])
    self.assertEqual([19, 26], game_state.trick_points)
    py_game_state = py_action.execute(py_game_state)
    self._assert_player_one_always_wins(py_game_state)
    delete_tree(root_node)

  def test_forcing_the_issue_player_one_always_wins(self):
    game_state = get_game_state_for_forcing_the_issue_puzzle()
    self._assert_player_one_always_wins(game_state)
