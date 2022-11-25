#  Copyright (c) 2021 Cristian Patrasciuc. All rights reserved.
#  Use of this source code is governed by a BSD-style license that can be
#  found in the LICENSE file.

import logging
import os
import platform
import sys
from textwrap import dedent

os.environ["KIVY_GL_BACKEND"] = "angle_sdl2"

from PyInstaller.building.api import EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.datastruct import Tree
from PyInstaller.building.osx import BUNDLE

if platform.system() == "Windows":
  from kivy_deps import sdl2, angle
  dependencies = sdl2.dep_bins + angle.dep_bins
else:
  dependencies = []

sys.path.append(os.path.join(SPECPATH, "src"))

from ui import schnapsen_app

output_filename = f"schnapsen-card-game-{schnapsen_app.__version__}"

additional_exe_flags = {}


def _maybe_add_windows_version_info() -> None:
  if platform.system() != "Windows":
    return

  version = [int(x) for x in schnapsen_app.__version__.split(".")]
  assert len(version) <= 4, version
  while len(version) < 4:
    version.append(0)

  windows_version_file_name = os.path.join(SPECPATH, "windows_version_info.txt")

  with open(windows_version_file_name, "w") as windows_version_file:
    windows_version_file.write(dedent(f"""
      VSVersionInfo(
        ffi=FixedFileInfo(
          # filevers and prodvers should be always a tuple with four items:
          # (1, 2, 3, 4). Set not needed items to zero 0.
          filevers={str(tuple(version))},
          prodvers={str(tuple(version))},
          # Contains a bitmask that specifies the valid bits "flags"r
          mask=0x0,
          # Contains a bitmask that specifies the Boolean attributes of the file.
          flags=0x0,
          # The operating system for which this file was designed.
          # 0x4 - NT and there is no need to change it.
          OS=0x4,
          # The general type of file.
          # 0x1 - the file is an application.
          fileType=0x1,
          # The function of the file.
          # 0x0 - the function is not defined for this fileType
          subtype=0x0,
          # Creation date and time stamp.
          date=(0, 0)
        ),
        kids=[
          StringFileInfo(
            [
              StringTable(
                "040904b0",
                [StringStruct("CompanyName", "Cristian Patrasciuc"),
                 StringStruct("ProductName", "Schnapsen Card Game"),
                 StringStruct("ProductVersion",
                              "{".".join(str(x) for x in version)}"),
                 StringStruct("FileDescription", "Schnapsen Card Game"),
                 StringStruct("InternalName", "{output_filename}"),
                 StringStruct("OriginalFilename", "{output_filename}.exe")])
            ]),
          VarFileInfo([VarStruct("Translation", [1033, 1200])])
        ]
      )
      """))
    logging.info("Adding windows version info")
    additional_exe_flags["version"] = windows_version_file_name


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

_maybe_add_windows_version_info()

icon_file_name = "icon.icns" if platform.system() == "Darwin" else "icon.ico"
icon_path = os.path.join(SPECPATH, "src", "ui", "resources", icon_file_name)

exe = EXE(pyz,
          analysis.scripts,
          analysis.binaries,
          analysis.zipfiles,
          analysis.datas,
          ui_resources,
          *[Tree(p) for p in dependencies],
          exclude_binaries=False,
          name=output_filename,
          icon=icon_path,
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          **additional_exe_flags)

if platform.system() == "Darwin":
  app = BUNDLE(exe,
               name=f"{exe.name}.app",
               icon=icon_path,
               bundle_identifier=None,
               version=schnapsen_app.__version__)
