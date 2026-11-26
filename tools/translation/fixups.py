"""Line fixes for files whose structure changed (not just text), e.g. repaired quotes.

make:   python fixups.py make  ORIG_DIR FIXED_DIR fixups.tsv FILE [FILE ...]
apply:  python fixups.py apply DIR fixups.tsv

Rows: file <TAB> first line (0-based) <TAB> old lines <TAB> new lines
(line endings kept, written as <CRLF>/<LF>). A row is only applied if the old
lines still match exactly, otherwise the script stops.
"""
import sys, os, difflib
from psxtext import read, write, enc, dec


def lines(p):
    return read(p).splitlines(keepends=True)


def make(orig, fixed, out, names):
    rows = []
    for n in names:
        a, b = lines(os.path.join(orig, n)), lines(os.path.join(fixed, n))
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if tag != 'equal':
                rows.append((n, str(i1), ''.join(a[i1:i2]), ''.join(b[j1:j2])))
    with open(out, 'w', encoding='utf-8', errors='surrogateescape', newline='\n') as f:
        f.write('# file\tfirst line\told lines\tnew lines\n')
        for r in rows:
            f.write('\t'.join(enc(x) for x in r) + '\n')
    print(f'{len(rows)} fixups -> {out}')


def apply(root, table):
    by_file = {}
    for line in open(table, encoding='utf-8', errors='surrogateescape').read().split('\n'):
        if line and not line.startswith('#'):
            f, i, old, new = (dec(x) for x in line.split('\t'))
            by_file.setdefault(f, []).append((int(i), old, new))
    for f, fixes in by_file.items():
        p = os.path.join(root, f)
        a = lines(p)
        for i, old, new in sorted(fixes, reverse=True):      # from the end: indices stay valid
            n = len(old.splitlines(keepends=True))
            if ''.join(a[i:i + n]) != old:
                sys.exit(f'fixup does not match: {f} line {i + 1}')
            a[i:i + n] = new.splitlines(keepends=True)
        write(p, ''.join(a))
    print(f'fixups applied to {len(by_file)} files')


if __name__ == '__main__':
    if sys.argv[1] == 'make':
        make(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
    else:
        apply(sys.argv[2], sys.argv[3])
