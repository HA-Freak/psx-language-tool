"""Builds every language folder from the RepairBox PSX system files package.

The repository contains no Sony files. Download the EN package of
RepairBox-PSX-HDD-Setup (https://github.com/DanielFergisz/RepairBox-PSX-HDD-Setup)
and put it into  sources/  (not in git):
  PSX_SystemFiles_EN_v1.3_Final.zip     (the extracted folder works too)

usage: python tools/build_all.py [--package ZIP_OR_DIR] [--no-check]
  -> DESR-... XMB ENG/GER/POL (both series), SYSTEM-DIC ENG/GER/POL,
     tools/elf/jp_original.dic
then:  sh tools/elf/build.sh   -> PSX_LANGUAGE_TOOL.ELF

The English folders are made from the original system files in the package
with tools/translation/eng5000.patch and eng5500.patch, German and Polish from
the English folders with the de/pl tables. Every generated file is compared
with tools/expected.sha1, so a different package version is noticed at once.
"""
import os, sys, glob, shutil, hashlib, subprocess, argparse, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(ROOT, 'tools', 'translation')
PKG_NAME = 'PSX_SystemFiles_EN_v1.3_Final'
# series, folder in the package, ENG folder inside __system, patch, German table, Polish table
SERIES = [('DESR-5000-5100-7000-7100', 'RepairBox-PSX1-SystemFiles', '', 'eng5000.patch', 'de5000.tsv', 'pl5000.tsv'),
          ('DESR-5500-5700-7500-7700', 'RepairBox-PSX2-SystemFiles', 'xosd/packages/', 'eng5500.patch', 'de.tsv', 'pl.tsv')]

ap = argparse.ArgumentParser()
ap.add_argument('--package', help=f'package .zip or extracted folder (default: sources/{PKG_NAME}[.zip])')
ap.add_argument('--no-check', action='store_true')
args = ap.parse_args()


def run(*cmd, cwd=TR):
    r = subprocess.run([sys.executable, *cmd], cwd=cwd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    out = [l for l in r.stdout.splitlines() if l.strip()]
    if r.returncode:
        sys.exit('\n'.join(out) + r.stderr)
    return out


def package():
    """returns the folder that holds RepairBox-PSX1/PSX2-SystemFiles (extracts the zip if needed)"""
    src = args.package or next((p for p in (os.path.join(ROOT, 'sources', PKG_NAME),
                                            os.path.join(ROOT, 'sources', PKG_NAME + '.zip'))
                                if os.path.exists(p)), None)
    if not src or not os.path.exists(src):
        sys.exit(f'missing: sources/{PKG_NAME}.zip  (RepairBox EN package, see README.md)')
    if os.path.isdir(src):
        hits = glob.glob(os.path.join(src, '**', SERIES[1][1]), recursive=True)
        if not hits:
            sys.exit(f'{src}: no {SERIES[1][1]} folder inside')
        return os.path.dirname(hits[0])
    dst = os.path.join(ROOT, 'build', 'package')
    shutil.rmtree(dst, ignore_errors=True)
    n = 0
    with zipfile.ZipFile(src) as z:
        for m in z.namelist():
            parts = m.split('/')
            # only the two __system folders are needed (the zip may have a top folder)
            for i, p in enumerate(parts[:-1]):
                if p in (SERIES[0][1], SERIES[1][1]) and parts[i + 1:i + 2] == ['__system']:
                    if not m.endswith('/'):
                        out = os.path.join(dst, *parts[i:])
                        os.makedirs(os.path.dirname(out), exist_ok=True)
                        with z.open(m) as f, open(out, 'wb') as o:
                            shutil.copyfileobj(f, o)
                        n += 1
                    break
    if not n:
        sys.exit(f'{src}: no RepairBox system files inside')
    print(f'{n} system files extracted from {os.path.basename(src)}')
    return dst


pkg = package()
for series, folder, prefix, patch, de, pl in SERIES:
    system = os.path.join(pkg, folder, '__system')
    out = {l: os.path.join(ROOT, f'{series} XMB {l}') for l in ('ENG', 'GER', 'POL')}
    print(f'{series}: ENG {run("engpatch.py", "apply", system, out["ENG"], prefix, patch)[-1]}')
    print(f'  GER {run("build_lang.py", out["ENG"], de, out["GER"])[0]}')
    print(f'  POL {run("build_lang.py", out["ENG"], pl, out["POL"], "--ascii")[0]}')

dic = os.path.join(pkg, SERIES[1][1], '__system', 'dic', 'jp.dic')
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
