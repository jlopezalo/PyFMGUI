# -*- mode: python ; coding: utf-8 -*-

import sys
import subprocess

block_cipher = None

a = Analysis(['main.py'],
             pathex=['.'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='main',
          debug=True,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='main')

app = BUNDLE(coll,
            name='pyAFMRheo.app',
            bundle_identifier = None,
            info_plist = {'NSHighResolutionCapable' : 'True'}
            )

# I use the library https://github.com/sindresorhus/create-dmg written with javascript to generate the MacOs DMG.
subprocess.run("create-dmg --overwrite './dist/pyAFMRheo.app' ./dist", shell=True, check=True)
