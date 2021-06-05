#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

from textwrap import dedent
from typing import List, Tuple, Callable

from kivy.base import runTouchApp, stopTouchApp
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView

from model.player_pair import PlayerPair

Builder.load_string(dedent("""
  <_LabelWithBorder@Label>:
    font_size: self.height / 3
    markup: True
    canvas:
      Color:
        rgba: 0.5, 0.5, 0.5, 1
      Line:
        rectangle: self.x + 5, self.y + 5, self.width - 10, self.height - 10
  
  <ScoreView>:
    auto_dismiss: False
    size_hint: 0.8, 0.8
    BoxLayout:
      orientation: 'vertical'
      padding: 0.1 * self.width, 0.1 * self.height
      
      GridLayout:
        id: score_grid
        cols: 2
        rows: 1
        row_force_default: True
        row_default_height: self.height / self.rows 
        
        Button:
          text: "[b]You[/b]"
          font_size: self.height / 3
          markup: True
        Button:
          text: "[b]Computer[/b]"
          font_size: self.height / 3
          markup: True

      Button:
        text: "OK"
        size_hint_y: 0.2
        font_size: self.height / 3
        on_release: root.dismiss()
  """))


class _LabelWithBorder(Label):
  pass


def _create_score_label(trick_points: int,
                        game_points: int, winner=False) -> _LabelWithBorder:
  color = "ffffff" if winner else "999999"
  label = _LabelWithBorder()
  label.text = f"[color={color}]{trick_points} ({max(0, game_points)})[/color]"
  return label


ScoreHistory = List[Tuple[PlayerPair[int], PlayerPair[int]]]
"""A list of tuples in the format: (trick_points, game_points)."""


class ScoreView(ModalView):
  """
  A model view used to display the score at the end of a game of Schnapsen.
  """

  def __init__(self, score_history: ScoreHistory, **kwargs):
    """
    Instantiates a new ScoreView.
    :param score_history: A list of tuples in the format (trick_points,
    game_points) for each completed game in a Bummerl.
    """
    super().__init__(**kwargs)
    self.ids.score_grid.rows = 1 + max(5, len(score_history))
    total_game_points = PlayerPair(7, 7)
    for trick_points, game_points in score_history:
      total_game_points.one -= game_points.one
      total_game_points.two -= game_points.two
      label = _create_score_label(trick_points.one, total_game_points.one,
                                  winner=game_points.one > 0)
      self.ids.score_grid.add_widget(label)
      label = _create_score_label(trick_points.two, total_game_points.two,
                                  winner=game_points.two > 0)
      self.ids.score_grid.add_widget(label)

  @staticmethod
  def show_score_view(score_history: ScoreHistory,
                      dismiss_callback: Callable[[], None]) -> "ScoreView":
    """
    Static method that can be passed as a ScoreViewCallback to a GameController.
    """
    score_view = ScoreView(score_history)
    score_view.bind(on_dismiss=lambda _: dismiss_callback())
    score_view.open()
    return score_view


if __name__ == "__main__":
  runTouchApp(ScoreView.show_score_view(
    [(PlayerPair(85, 20), PlayerPair(2, 0)),
     (PlayerPair(30, 24), PlayerPair(0, 3)),
     (PlayerPair(85, 20), PlayerPair(2, 0)),
     (PlayerPair(30, 24), PlayerPair(0, 3)),
     (PlayerPair(85, 20), PlayerPair(2, 0)),
     (PlayerPair(30, 24), PlayerPair(0, 3))],
    stopTouchApp))
