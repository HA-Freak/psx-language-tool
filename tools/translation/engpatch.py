"""Builds the English XMB folder from the original system files of the RepairBox package.

A file is split into pieces that end after every quote and line break, so a
changed text is one piece. The patch holds only the new pieces (the English
texts); for the replaced original pieces it stores just a checksum, so it
contains no Sony text.

make:   python engpatch.py make  SYSTEM_DIR ENG_DIR PREFIX OUT.patch
apply:  python engpatch.py apply SYSTEM_DIR OUT_DIR PREFIX IN.patch

SYSTEM_DIR  __system folder of the package (RepairBox-PSX1/PSX2-SystemFiles/__system)
PREFIX      path of the ENG folder inside __system ("" for the 5000 series,
            "xosd/packages/" for the 5500 series)

Patch lines:
  F <TAB> file <TAB> base file <TAB> sha1 of the result   one per output file
  @ <TAB> first piece <TAB> count <TAB> sha1 of those original pieces
  + <TAB> new piece                                        (follows its @ line)
Line breaks and tabs are written as <CR> <LF> <TAB>.
"""
import sys, os, re, shutil, hashlib, difflib

# a piece ends after a quote or a line break, so a changed text replaces only its own pieces
PIECE = re.compile(r'[^"\r\n]*(?:"|\r\n|\r|\n)|[^"\r\n]+\Z')


def enc(s):
    return s.replace('\r', '<CR>').replace('\n', '<LF>').replace('\t', '<TAB>')


def dec(s):
    return s.replace('<TAB>', '\t').replace('<LF>', '\n').replace('<CR>', '\r')


def load(p):
    return PIECE.findall(open(p, 'rb').read().decode('utf-8', errors='surrogateescape'))


def raw(lines):
    return ''.join(lines).encode('utf-8', errors='surrogateescape')


def sha(lines):
    return hashlib.sha1(raw(lines)).hexdigest()


def walk(root):
    for dp, _, fs in os.walk(root):
        for fn in sorted(fs):
            yield os.path.relpath(os.path.join(dp, fn), root).replace(os.sep, '/')


def best_base(system, prefix, rel, new):
    """for a file the package does not have: the most similar file in the same folder"""
    d = os.path.join(system, prefix + os.path.dirname(rel))
    best, score = None, -1
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        p = os.path.join(d, fn)
        if os.path.isfile(p) and os.path.getsize(p) < 4 << 20:
            r = difflib.SequenceMatcher(None, load(p), new, autojunk=False).ratio()
            if r > score:
                best, score = fn, r
    return (os.path.dirname(rel) + '/' + best).lstrip('/') if best else ''


def make(system, eng, prefix, out):
    res, added = [], 0
    for rel in sorted(walk(eng)):
        new = load(os.path.join(eng, rel))
        if any(e in x for x in new for e in ('<CR>', '<LF>', '<TAB>')):
            sys.exit(f'{rel}: contains an escape sequence, cannot be stored')
        base = rel if os.path.isfile(os.path.join(system, prefix + rel)) else best_base(system, prefix, rel, new)
        old = load(os.path.join(system, prefix + base)) if base else []
        res.append(f'F\t{rel}\t{base}\t{sha(new)}')
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
            if tag != 'equal':
                res.append(f'@\t{i1}\t{i2 - i1}\t{sha(old[i1:i2])}')
                res += ['+\t' + enc(x) for x in new[j1:j2]]
                added += j2 - j1
    with open(out, 'w', encoding='utf-8', errors='surrogateescape', newline='\n') as f:
        f.write(__doc__.split('\n')[0].replace('Builds', '# Patch: builds') + '\n')
        f.write('\n'.join(res) + '\n')
    print(f'{sum(r[0] == "F" for r in res)} files, {sum(r[0] == "@" for r in res)} changes, '
          f'{added} new pieces -> {out}')


def apply(system, out, prefix, patch):
    files, cur = [], None
    for ln, line in enumerate(open(patch, encoding='utf-8', errors='surrogateescape').read().split('\n'), 1):
        if not line or line[0] == '#':
            continue
        t, rest = line[0], line[2:]
        if t == 'F':
            rel, base, h = rest.split('\t')
            cur = (rel, base, h, [])
            files.append(cur)
        elif t == '@':
            i, n, h = rest.split('\t')
            cur[3].append([int(i), int(n), h, []])
        elif t == '+':
            cur[3][-1][3].append(dec(rest))
        else:
            sys.exit(f'{patch}:{ln}: unknown line')
    if os.path.exists(out):
        shutil.rmtree(out)
    bad = 0
    for rel, base, h, hunks in files:
        old = load(os.path.join(system, prefix + base)) if base else []
        for i, n, oh, new in reversed(hunks):          # from the end: line numbers stay valid
            if sha(old[i:i + n]) != oh:
                sys.exit(f'{rel}: original file differs from the expected one ({base} piece {i}) '
                         '- wrong package version?')
            old[i:i + n] = new
        if sha(old) != h:
            bad += 1
            print('DIFFERENT:', rel)
        p = os.path.join(out, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(raw(old))
    print(f'{len(files)} files written, {bad} different')
    if bad:
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) != 6 or sys.argv[1] not in ('make', 'apply'):
        sys.exit(__doc__)
    (make if sys.argv[1] == 'make' else apply)(*sys.argv[2:])
