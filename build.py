"""Builds everything with one command:

    python build.py [PACKAGE]

PACKAGE is the RepairBox EN package PSX_SystemFiles_EN_v1.3_Final.zip (or its extracted
folder). Without it the zip is looked for in sources/, the repository folder and the
Downloads folder. Steps:
  1. tools/build_all.py  - language folders (ENG/GER/POL/ESP) and button labels, checked
                           against tools/expected.sha1
  2. tools/elf/build.py  - PSX_LANGUAGE_TOOL.ELF (downloads the ps2dev toolchain once)
Options: --no-elf (only step 1), --no-check (skip the checksum comparison).
"""
import os, sys, subprocess, argparse

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = 'PSX_SystemFiles_EN_v1.3_Final'
LINK = 'https://drive.google.com/file/d/1FjzAhc510617HnPV5F-vRG8m4WtTbchO/view'

ap = argparse.ArgumentParser(description='builds all language folders and the installer ELF')
ap.add_argument('package', nargs='?', help=f'{NAME}.zip or its extracted folder')
ap.add_argument('--no-elf', action='store_true', help='only build the language folders')
ap.add_argument('--no-check', action='store_true', help='do not compare with tools/expected.sha1')
args = ap.parse_args()

pkg = args.package
if not pkg:
    places = [os.path.join(ROOT, 'sources'), ROOT, os.path.join(os.path.expanduser('~'), 'Downloads')]
    pkg = next((p for d in places for p in (os.path.join(d, NAME + '.zip'), os.path.join(d, NAME))
                if os.path.exists(p)), None)
if not pkg or not os.path.exists(pkg):
    sys.exit(f'{NAME}.zip not found.\n'
             f'Download the EN package of RepairBox-PSX-HDD-Setup:\n  {LINK}\n'
             f'and put it into sources/ (or pass its path: python build.py PATH).')
print('package:', pkg, flush=True)

cmd = [sys.executable, os.path.join(ROOT, 'tools', 'build_all.py'), '--package', pkg]
if args.no_check:
    cmd.append('--no-check')
if subprocess.run(cmd).returncode:
    sys.exit('language build failed')
if not args.no_elf:
    if subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'elf', 'build.py')]).returncode:
        sys.exit('ELF build failed')
print('\ndone. ELF-INSTALLER/ holds the installer, the DESR-* and SYSTEM-DIC * folders the files.')
