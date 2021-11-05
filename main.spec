#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import os
import sys

os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

from PyInstaller.building.api import EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.datastruct import Tree
from kivy_deps import sdl2, angle

sys.path.append(os.path.join(SPECPATH, "src"))

from ui import schnapsen_app

block_cipher = None

cython_hidden_imports = [
  "ai.cython_mcts_player.card",
  "ai.cython_mcts_player.game_state",
  "ai.cython_mcts_player.mcts",
  "ai.cython_mcts_player.player",
  "ai.cython_mcts_player.player_action",
  "ai.mcts_player",
]

hidden_modules = ["ui.schnapsen_app"] + cython_hidden_imports

ui_resources = Tree("src/ui/", "ui/", excludes=["*.pyx", "*.py", "*.pyc"])

analysis = Analysis(["src/main.py"],
                    pathex=[],
                    binaries=[],
                    datas=[],
                    hiddenimports=hidden_modules,
                    hookspath=[],
                    hooksconfig={},
                    runtime_hooks=[],
                    excludes=[],
                    win_no_prefer_redirects=False,
                    win_private_assemblies=False,
                    cipher=block_cipher,
                    noarchive=False)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          analysis.scripts,
          analysis.binaries,
          analysis.zipfiles,
          analysis.datas,
          ui_resources,
          *[Tree(p) for p in (sdl2.dep_bins + angle.dep_bins)],
          exclude_binaries=False,
          name=f"schnapsen-card-game-{schnapsen_app.__version__}",
          icon=os.path.join(SPECPATH, "src", "ui", "resources", "icon.ico"),
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None)
