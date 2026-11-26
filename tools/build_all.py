"""Builds every language folder from your own copies of the source files.

The repository contains no Sony files. Put these into  sources/  (not in git):
  DESR-5000-5100-7000-7100 XMB ENG.7z   English community mod for firmware 1.31
  DESR-5500-5700-7500-7700 XMB ENG.7z   English community mod for firmware 2.11
  jp.dic                                original hdd0:__system/dic/jp.dic (2.11)
(instead of a .7z, an extracted folder with the same name works too)

usage: python tools/build_all.py [--sources DIR] [--no-check]
  -> DESR-... XMB ENG/GER/POL (both series), SYSTEM-DIC ENG/GER/POL,
     tools/elf/jp_original.dic
then:  sh tools/elf/build.sh   -> PSX_LANGUAGE_TOOL.ELF

Every generated file is compared with tools/expected.sha1, so a different
source archive is noticed at once. 7-Zip: set SEVENZIP if it is not in
C:/Program Files/7-Zip/7z.exe.
"""
import os, sys, shutil, hashlib, subprocess, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(ROOT, 'tools', 'translation')
S5000, S5500 = 'DESR-5000-5100-7000-7100', 'DESR-5500-5700-7500-7700'
# series, English table, German table, Polish table
SERIES = [(S5000, 'en5000.tsv', 'de5000.tsv', 'pl5000.tsv'),
          (S5500, 'en.tsv', 'de.tsv', 'pl.tsv')]

ap = argparse.ArgumentParser()
ap.add_argument('--sources', default=os.path.join(ROOT, 'sources'))
ap.add_argument('--no-check', action='store_true')
args = ap.parse_args()
work = os.path.join(ROOT, 'build', 'src')


def run(*cmd, cwd=TR):
    r = subprocess.run([sys.executable, *cmd], cwd=cwd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    out = [l for l in r.stdout.splitlines() if l.strip()]
    if r.returncode:
        sys.exit('\n'.join(out) + r.stderr)
    return out


def source_dir(series):
    """returns the folder holding the mod files (extracts the .7z if needed)"""
    name = f'{series} XMB ENG'
    folder = os.path.join(args.sources, name)
    if not os.path.isdir(folder):
        arc = folder + '.7z'
        if not os.path.isfile(arc):
            sys.exit(f'missing: {arc}  (or the extracted folder)')
        folder = os.path.join(work, series)
        shutil.rmtree(folder, ignore_errors=True)
        exe = os.environ.get('SEVENZIP', r'C:\Program Files\7-Zip\7z.exe')
        r = subprocess.run([exe, 'x', '-y', '-o' + folder, arc], capture_output=True, text=True)
        if r.returncode:
            sys.exit(f'7-Zip failed on {arc}:\n{r.stdout}{r.stderr}')
        folder = os.path.join(folder, name)
    # some archives contain the folder twice (name/name)
    inner = os.path.join(folder, name)
    return inner if os.path.isdir(inner) else folder


for series, en, de, pl in SERIES:
    src = source_dir(series)
    out = {l: os.path.join(ROOT, f'{series} XMB {l}') for l in ('ENG', 'GER', 'POL')}
    print(f'{series}: {run("build_lang.py", src, en, out["ENG"])[0]}')
    if series == S5500:
        print('  ' + run('fixups.py', 'apply', out['ENG'], 'fixups.tsv')[0])
    print(f'  GER {run("build_lang.py", out["ENG"], de, out["GER"])[0]}')
    print(f'  POL {run("build_lang.py", out["ENG"], pl, out["POL"], "--ascii")[0]}')

dic = os.path.join(args.sources, 'jp.dic')
if not os.path.isfile(dic):
    sys.exit(f'missing: {dic}  (original hdd0:__system/dic/jp.dic)')
run(os.path.join(ROOT, 'tools', 'sysdic', 'sysdic.py'), dic, ROOT)
shutil.copyfile(dic, os.path.join(ROOT, 'tools', 'elf', 'jp_original.dic'))
print('SYSTEM-DIC GER/ENG/POL and tools/elf/jp_original.dic written')

if not args.no_check:
    bad = n = 0
    for line in open(os.path.join(ROOT, 'tools', 'expected.sha1'), encoding='utf-8'):
        h, rel = line.rstrip('\n').split('  ', 1)
        p = os.path.join(ROOT, rel)
        n += 1
        if not os.path.isfile(p) or hashlib.sha1(open(p, 'rb').read()).hexdigest() != h:
            bad += 1
            if bad <= 20:
                print('DIFFERENT:', rel)
    print(f'check: {n - bad} of {n} files identical to the released build')
    sys.exit(1 if bad else 0)
