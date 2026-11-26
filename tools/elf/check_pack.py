"""Read a pack exactly like the ELF does and compare every file with the mod folders.
usage: python check_pack.py PROJECT_DIR PACK.bin"""
import os, sys, struct, zlib

proj, pack = sys.argv[1:3]
d = open(pack, 'rb').read()
assert d[:4] == b'PXMB'
nsets, nblobs, npaths, ob, op, os_, of, od, _ = struct.unpack_from('<9I', d, 4)
u = lambda off: struct.unpack_from('<I', d, off)[0]


def path(i):
    s = op + u(op + 4 * i)
    return d[s:d.index(b'\0', s)].decode()


def blob(i):
    off, cs, rs = struct.unpack_from('<3I', d, ob + 12 * i)
    r = zlib.decompress(d[od + off:od + off + cs])
    assert len(r) == rs
    return r


SER = ['DESR-5000-5100-7000-7100', 'DESR-5500-5700-7500-7700']
LANG = ['GER', 'ENG', 'POL']
bad = 0
for k in range(nsets):
    series, lang, n, first, probe = struct.unpack_from('<5I', d, os_ + 20 * k)
    root = os.path.join(proj, f'{SER[series]} XMB {LANG[lang]}')
    for j in range(n):
        pi, bi = struct.unpack_from('<2I', d, of + 8 * (first + j))
        rel = path(pi)
        if series == 1:
            rel = rel[len('xosd/packages/'):]
        if open(os.path.join(root, rel), 'rb').read() != blob(bi):
            bad += 1
            print('MISMATCH', rel)
    print(SER[series], LANG[lang], n, 'files ok' if not bad else 'ERRORS', 'probe', path(probe))
sys.exit(1 if bad else 0)
