#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import os


class GameOptions:
  def __init__(self, **kwargs):
    """
    Creates a new GameOptions instance. It starts with a set of default options.
    These defaults can be overridden using **kwargs.
    :param kwargs: A list of key=value pairs used to override default options.
    """
    default_resource_path = os.path.join(os.path.dirname(__file__), "resources")

    # The default options.
    options = {
      # Image folders.
      "resource_path": default_resource_path,
      "cards_path": os.path.join(default_resource_path, "cards"),

      # Animation parameters.
      "enable_animations": True,
      "animation_duration_multiplier": 1,
      "play_card_duration": 0.5,
      "exchange_trump_duration": 1.5,
      "close_talon_duration": 0.5,
      "trick_completed_duration": 0.5,
      "draw_cards_duration": 0.5,

      # UI Options.
      "computer_cards_visible": False,
    }

    # Maybe override the default options based on kwargs.
    for key, value in kwargs.items():
      assert key in options, f"No default value for option: {key}"
      options[key] = value

    self.__dict__.update(options)

  @property
  def play_card_duration(self) -> float:
    return self.__dict__["play_card_duration"] * \
           self.animation_duration_multiplier

  @property
  def exchange_trump_duration(self) -> float:
    return self.__dict__["exchange_trump_duration"] * \
           self.animation_duration_multiplier

  @property
  def close_talon_duration(self) -> float:
    return self.__dict__["close_talon_duration"] * \
           self.animation_duration_multiplier

  @property
  def trick_completed_duration(self) -> float:
    return self.__dict__["trick_completed_duration"] * \
           self.animation_duration_multiplier

  @property
  def draw_cards_duration(self) -> float:
    return self.__dict__["draw_cards_duration"] * \
           self.animation_duration_multiplier
