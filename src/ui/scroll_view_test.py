#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from unittest.mock import Mock

from model.player_pair import PlayerPair
from ui.score_view import ScoreView
from ui.test_utils import GraphicUnitTest


class ScoreViewTest(GraphicUnitTest):
  def test_one_game(self):
    score_history = [(PlayerPair(78, 32), PlayerPair(2, 0))]
    score_view = ScoreView(score_history)
    score_view.open()
    self.render(score_view)
    score_view.dismiss()

  def test_one_bummerl(self):
    score_history = [
      (PlayerPair(78, 32), PlayerPair(2, 0)),
      (PlayerPair(42, 67), PlayerPair(0, 1)),
      (PlayerPair(52, 40), PlayerPair(3, 0)),
      (PlayerPair(62, 58), PlayerPair(0, 1)),
      (PlayerPair(10, 85), PlayerPair(0, 2)),
      (PlayerPair(66, 50), PlayerPair(1, 0)),
      (PlayerPair(0, 82), PlayerPair(0, 3)),
    ]
    score_view = ScoreView(score_history)
    score_view.open()
    self.render(score_view)
    score_view.dismiss()

  def test_maximum_number_of_games(self):
    score_history = [
      (PlayerPair(60, 60), PlayerPair(1, 0)),
      (PlayerPair(60, 60), PlayerPair(0, 1)),
      (PlayerPair(60, 60), PlayerPair(1, 0)),
      (PlayerPair(60, 60), PlayerPair(0, 1)),
      (PlayerPair(60, 60), PlayerPair(1, 0)),
      (PlayerPair(60, 60), PlayerPair(0, 1)),
      (PlayerPair(60, 60), PlayerPair(1, 0)),
      (PlayerPair(60, 60), PlayerPair(0, 1)),
      (PlayerPair(60, 60), PlayerPair(1, 0)),
      (PlayerPair(60, 60), PlayerPair(0, 1)),
      (PlayerPair(60, 60), PlayerPair(1, 0)),
      (PlayerPair(60, 60), PlayerPair(0, 1)),
      (PlayerPair(60, 60), PlayerPair(1, 0)),
    ]
    score_view = ScoreView(score_history)
    score_view.open()
    self.render(score_view)
    score_view.dismiss()

  def test_show_score_view(self):
    score_history = [
      (PlayerPair(78, 32), PlayerPair(2, 0)),
      (PlayerPair(42, 67), PlayerPair(0, 1)),
      (PlayerPair(52, 40), PlayerPair(3, 0)),
      (PlayerPair(62, 58), PlayerPair(0, 1)),
      (PlayerPair(10, 85), PlayerPair(0, 2)),
      (PlayerPair(66, 50), PlayerPair(1, 0)),
      (PlayerPair(0, 82), PlayerPair(0, 3)),
    ]
    dismiss_callback = Mock()
    score_view = ScoreView.show_score_view(score_history, dismiss_callback)
    self.render(score_view)
    dismiss_callback.assert_not_called()
    score_view.dismiss()
    dismiss_callback.assert_called_once()
