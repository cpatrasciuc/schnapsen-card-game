#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import logging
import os
import pickle
import unittest
from typing import List

from ai.mcts_algorithm import MCTS, Node
from model.card import Card
from model.card_value import CardValue
from model.game_state import GameState
from model.game_state_test_utils import get_game_state_with_all_tricks_played, \
  get_game_state_for_you_first_no_you_first_puzzle, \
  get_game_state_for_elimination_play_puzzle, \
  get_game_state_for_playing_to_win_the_last_trick_puzzle, \
  get_game_state_for_tempo_puzzle
from model.game_state_validation import GameStateValidator
from model.player_action import PlayCardAction
from model.player_id import PlayerId
from model.player_pair import PlayerPair
from model.suit import Suit


class _TestNode(Node[int, int]):
  """
  Implementation of the Node class that expands to the tree in this image:
  https://miro.medium.com/max/500/1*OpJz2LcElVB_XPEYAvK87Q.jpeg

  The states are numbered in BFS order (left to right on the same level).
  The actions are integers, representing the index of the children.
  """

  _tree = {
    0: [1, 2, 3],
    1: [4, 5],
    3: [6, 7],
    5: [8, 9]
  }

  @property
  def terminal(self) -> bool:
    return self.state not in _TestNode._tree

  def _get_available_actions(self) -> List[int]:
    return list(range(len(_TestNode._tree[self.state])))

  def _get_reward_for_terminal_node(self) -> PlayerPair[float]:
    rewards = {
      2: PlayerPair(0, 0),
      4: PlayerPair(0, 0),
      6: PlayerPair(0, 0),
      7: PlayerPair(1, 0),
      8: PlayerPair(0, 0),
      9: PlayerPair(1, 0),
    }
    return rewards[self.state]

  def _player(self) -> PlayerId:
    return PlayerId.ONE

  def _get_next_state(self, action: int) -> int:
    return _TestNode._tree[self.state][action]


class MCTSAlgorithmTest(unittest.TestCase):
  def test_fully_expanded_tree(self):
    mcts = MCTS(PlayerId.ONE, _TestNode)
    root_node = mcts.build_tree(0)
    nodes = [root_node]
    index = 0
    while index < len(nodes):
      node = nodes[index]
      if node.children is not None:
        actions = list(sorted(node.children.keys()))
        for action in actions:
          child = node.children[action]
          nodes.append(child)
          self.assertEqual(node, child.parent)
      index += 1
    self.assertEqual(10, len(nodes))
    self.assertEqual([(2, 6), (1, 3), (1, 2), (1, 2)],
                     [(node.q, node.n) for node in nodes if not node.terminal])
    self.assertEqual([1, 0, 1, 0, 1, 0, 1, 0, 1],
                     [node.ucb for node in nodes[1:]])
    for node in nodes:
      if node != root_node:
        self.assertTrue(node.fully_expanded, msg=node)
        self.assertTrue(node.fully_simulated, msg=node)


def _get_game_state_with_one_card_left() -> GameState:
  game_state = get_game_state_with_all_tricks_played()
  with GameStateValidator(game_state):
    trick = game_state.won_tricks.one.pop(-1)
    game_state.trick_points.one -= trick.one.card_value
    game_state.trick_points.one -= trick.two.card_value
    game_state.cards_in_hand.one.append(trick.one)
    game_state.cards_in_hand.two.append(trick.two)
    game_state.next_player = PlayerId.ONE
  return game_state


class SchnapsenMCTSAlgorithmTest(unittest.TestCase):
  def test_leaf_node(self):
    game_state = _get_game_state_with_one_card_left()
    play_jack_clubs = PlayCardAction(PlayerId.ONE,
                                     Card(Suit.CLUBS, CardValue.JACK))
    play_jack_clubs.execute(game_state)
    mcts = MCTS(PlayerId.TWO)
    root_node = mcts.build_tree(game_state)

    self.assertIsNone(root_node.parent)
    self.assertEqual(1, len(root_node.children))
    self.assertEqual([], root_node.untried_actions)
    self.assertTrue(root_node.fully_expanded)
    self.assertFalse(root_node.terminal)
    self.assertEqual(PlayerId.TWO, root_node.player)
    self.assertFalse(root_node.fully_simulated)

    action = list(root_node.children.keys())[0]
    self.assertEqual(
      PlayCardAction(PlayerId.TWO, Card(Suit.SPADES, CardValue.JACK)), action)
    leaf: Node = root_node.children[action]
    self.assertIs(root_node, leaf.parent)
    self.assertIsNone(leaf.children)
    self.assertIsNone(leaf.untried_actions)
    self.assertTrue(leaf.fully_expanded)
    self.assertTrue(leaf.terminal)
    self.assertEqual(PlayerId.ONE, leaf.player)
    self.assertAlmostEqual(0.33, leaf.ucb, delta=0.01)
    self.assertTrue(leaf.fully_simulated)

  def test_one_card_left_for_each_player(self):
    game_state = _get_game_state_with_one_card_left()
    mcts = MCTS(PlayerId.ONE)
    root_node = mcts.build_tree(game_state)

    self.assertIsNone(root_node.parent)
    self.assertEqual(1, len(root_node.children))
    self.assertEqual([], root_node.untried_actions)
    self.assertTrue(root_node.fully_expanded)
    self.assertFalse(root_node.terminal)
    self.assertEqual(PlayerId.ONE, root_node.player)
    self.assertFalse(root_node.fully_simulated)

    action = list(root_node.children.keys())[0]
    self.assertEqual(
      PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.JACK)), action)
    player_two_node: Node = root_node.children[action]
    print(str(player_two_node))
    self.assertIs(root_node, player_two_node.parent)
    self.assertEqual(1, len(player_two_node.children))
    self.assertEqual([], player_two_node.untried_actions)
    self.assertTrue(player_two_node.fully_expanded)
    self.assertFalse(player_two_node.terminal)
    self.assertEqual(PlayerId.TWO, player_two_node.player)
    self.assertAlmostEqual(-0.33, player_two_node.ucb, delta=0.01)
    self.assertTrue(player_two_node.fully_simulated)

    action = list(player_two_node.children.keys())[0]
    self.assertEqual(
      PlayCardAction(PlayerId.TWO, Card(Suit.SPADES, CardValue.JACK)), action)
    leaf: Node = player_two_node.children[action]
    self.assertIs(player_two_node, leaf.parent)
    self.assertIsNone(leaf.children)
    self.assertIsNone(leaf.untried_actions)
    self.assertTrue(leaf.fully_expanded)
    self.assertTrue(leaf.terminal)
    self.assertEqual(PlayerId.ONE, leaf.player)
    self.assertAlmostEqual(0.33, leaf.ucb, delta=0.01)
    self.assertTrue(leaf.fully_simulated)

  def test_you_first_no_you_first(self):
    game_state = get_game_state_for_you_first_no_you_first_puzzle()
    mcts = MCTS(PlayerId.ONE)
    root_node = mcts.build_tree(game_state)
    self.assertIsNone(root_node.parent)
    self.assertEqual(5, len(root_node.children))
    self.assertEqual([], root_node.untried_actions)
    self.assertTrue(root_node.fully_expanded)
    self.assertFalse(root_node.terminal)
    self.assertEqual(PlayerId.ONE, root_node.player)
    self.assertFalse(root_node.fully_simulated)

    for action, child in root_node.children.items():
      print(action, child)

    for action, child in root_node.children.items():
      self.assertTrue(child.fully_simulated)
      self.assertEqual(PlayerId.TWO, child.player)
      self.assertAlmostEqual(
        0.33 if action.card.suit == Suit.HEARTS else -0.33, child.ucb,
        delta=0.01, msg=action)

  def test_elimination_play_player_one(self):
    game_state = get_game_state_for_elimination_play_puzzle()
    mcts = MCTS(PlayerId.ONE)
    root_node = mcts.build_tree(game_state)
    for action, child in root_node.children.items():
      print(action, child)
    for action, child in root_node.children.items():
      self.assertTrue(child.fully_simulated)
      self.assertEqual(PlayerId.TWO, child.player)
      self.assertAlmostEqual(
        0.33 if action.card.suit == Suit.HEARTS else -0.33, child.ucb,
        delta=0.01, msg=action)

  def test_elimination_play_player_two(self):
    game_state = get_game_state_for_elimination_play_puzzle()
    action = PlayCardAction(PlayerId.ONE, Card(Suit.CLUBS, CardValue.JACK))
    action.execute(game_state)
    action = PlayCardAction(PlayerId.TWO, Card(Suit.CLUBS, CardValue.KING))
    action.execute(game_state)
    self.assertEqual(34, game_state.trick_points.one)
    self.assertEqual(40, game_state.trick_points.two)
    mcts = MCTS(PlayerId.TWO)
    root_node = mcts.build_tree(game_state)
    for action, child in root_node.children.items():
      print(action, child)
    for action, child in root_node.children.items():
      self.assertTrue(child.fully_simulated)
      self.assertEqual(PlayerId.ONE, child.player)
      self.assertAlmostEqual(0.33, child.ucb, delta=0.01, msg=action)

  def _assert_trees_equal(self, node1: Node, node2: Node):
    self.assertEqual(node1.ucb, node2.ucb)
    self.assertEqual(node1.terminal, node2.terminal)
    self.assertEqual(node1.player, node2.player)
    self.assertEqual(node1.fully_expanded, node2.fully_expanded)
    self.assertEqual(node1.fully_simulated, node2.fully_simulated)
    if node1.terminal:
      return
    self.assertEqual(set(node1.untried_actions), set(node2.untried_actions))
    self.assertEqual(set(node1.children.keys()), set(node2.children.keys()))
    for action, child1 in node1.children.items():
      self._assert_trees_equal(child1, node2.children[action])

  def test_elimination_play_fully_simulated_tree(self):
    # TODO(tests): Maybe do this for more game states that can be fully
    #  simulated.
    game_state = get_game_state_for_elimination_play_puzzle()
    mcts = MCTS(game_state.next_player)
    root_node = mcts.build_tree(game_state)
    golden_data_file = os.path.join(os.path.dirname(__file__), "test_data",
                                    "elimination_play_tree.pickle")
    # Uncomment this to save a golden version of the tree:
    # with open(golden_data_file, "wb") as output_file:
    #   pickle.dump(root_node, output_file)
    with open(golden_data_file, "rb") as input_file:
      expected_tree = pickle.load(input_file)
    self._assert_trees_equal(expected_tree, root_node)

  def _assert_player_one_always_wins(self, game_state: GameState):
    while not game_state.is_game_over:
      mcts = MCTS(game_state.next_player)
      root_node = mcts.build_tree(game_state)
      print()
      for action, child in root_node.children.items():
        print(action, child)
        self.assertTrue(child.fully_simulated, msg=action)
      best_action = root_node.best_action()
      logging.debug("MCTSAlgorithmTest: Player %s plays %s",
                    game_state.next_player, best_action)
      best_action.execute(game_state)
    self.assertEqual(PlayerPair(1, 0), game_state.game_points)

  def test_elimination_play_player_one_always_wins(self):
    game_state = get_game_state_for_elimination_play_puzzle()
    self._assert_player_one_always_wins(game_state)

  def test_playing_to_win_the_last_trick_player_one_always_wins(self):
    game_state = get_game_state_for_playing_to_win_the_last_trick_puzzle()
    self._assert_player_one_always_wins(game_state)

  def test_tempo_player_one_always_wins(self):
    game_state = get_game_state_for_tempo_puzzle()
    self._assert_player_one_always_wins(game_state)
