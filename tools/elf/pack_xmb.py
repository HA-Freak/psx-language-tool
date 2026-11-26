"""Pack the XMB language mods into one zlib-compressed blob for the ELF.

usage: python pack_xmb.py PROJECT_DIR OUT.bin

All paths in the pack are relative to the hdd0:__system partition:
  DESR-5000 mod folder already starts with  xosd/packages/...
  DESR-5500 mod folder holds the package folders -> prefixed with xosd/packages/
Skipped: version_0/ (firmware version + EULA, left untouched) and stray
"... (2).xml" copies.

Layout (all integers u32 little endian):
  header  : 'PXMB' nsets nblobs npaths off_blobs off_paths off_sets off_files off_data
  blobs   : nblobs x (off csize rsize)          off relative to off_data
  paths   : npaths x (stroff)  then 0-terminated strings, stroff relative to off_paths
  sets    : nsets  x (series lang nfiles first probe)
            series 0 = DESR-5000/5100/7000/7100, 1 = DESR-5500/5700/7500/7700
            lang   0 = German, 1 = English, 2 = Polish
            first  = index into the file table, probe = path index used to
                     recognise which language is installed
  files   : n x (path_index blob_index)
  data    : compressed blobs
"""
import os, sys, struct, zlib, hashlib

proj, out = sys.argv[1:3]
SERIES = [('DESR-5000-5100-7000-7100', ''), ('DESR-5500-5700-7500-7700', 'xosd/packages/')]
LANGS = ['GER', 'ENG', 'POL']


def collect(root, prefix):
    res = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            rel = os.path.relpath(os.path.join(dp, f), root).replace('\\', '/')
            if rel.startswith('xosd/packages/version_0/') or ' (2)' in f:
                continue
            res[prefix + rel] = open(os.path.join(dp, f), 'rb').read()
    return res


blobs, blob_idx, paths, path_idx, sets, files = [], {}, [], {}, [], []


def bi(data):
    h = hashlib.sha1(data).digest()
    if h not in blob_idx:
        blob_idx[h] = len(blobs)
        blobs.append(data)
    return blob_idx[h]


def pi(p):
    if p not in path_idx:
        path_idx[p] = len(paths)
        paths.append(p)
    return path_idx[p]


for s, (name, prefix) in enumerate(SERIES):
    content = {l: collect(os.path.join(proj, f'{name} XMB {l}'), prefix) for l in LANGS}
    keys = sorted(content['ENG'])
    for l in LANGS:
        if sorted(content[l]) != keys:
            sys.exit(f'{name} {l}: file list differs from ENG')
    # probe: smallest text file whose content differs in all three languages
    probe = min((k for k in keys if len({content[l][k] for l in LANGS}) == 3),
                key=lambda k: len(content['ENG'][k]))
    for li, l in enumerate(LANGS):
        first = len(files)
        for k in keys:
            files.append((pi(k), bi(content[l][k])))
        sets.append((s, li, len(keys), first, pi(probe)))
    print(f'{name}: {len(keys)} files, probe {probe}')

comp = [zlib.compress(b, 9) for b in blobs]
hdr = 4 + 9 * 4
off_blobs = hdr
off_paths = off_blobs + 12 * len(blobs)
strs = b''
stroffs = []
base = 4 * len(paths)
for p in paths:
    stroffs.append(base + len(strs))
    strs += p.encode('utf-8') + b'\0'
ptab = struct.pack(f'<{len(paths)}I', *stroffs) + strs
ptab += b'\0' * (-len(ptab) % 4)
off_sets = off_paths + len(ptab)
off_files = off_sets + 20 * len(sets)
off_data = off_files + 8 * len(files)

o = bytearray(b'PXMB' + struct.pack('<9I', len(sets), len(blobs), len(paths), off_blobs,
                                    off_paths, off_sets, off_files, off_data, 0))
pos = 0
for c, b in zip(comp, blobs):
    o += struct.pack('<3I', pos, len(c), len(b))
    pos += len(c)
o += ptab
for st in sets:
    o += struct.pack('<5I', *st)
for f in files:
    o += struct.pack('<2I', *f)
assert len(o) == off_data
for c in comp:
    o += c
open(out, 'wb').write(o)
print(f'{len(blobs)} unique files, {sum(map(len, blobs))} bytes -> pack {len(o)} bytes')
