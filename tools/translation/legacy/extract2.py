import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1]
ENTRY = re.compile(r'^(\{[^}\n]*\}[ \t]*=[ \t]*")(.*?)("[ \t]*;)', re.S | re.M)

known = set()
with open(os.path.join(HERE, 'src.txt'), encoding='utf-8', errors='surrogateescape') as f:
    for line in f.read().split('\n'):
        if line:
            known.add(line.split('\t', 1)[1])

new = {}
for root, _, files in os.walk(SRC):
    for fn in files:
        p = os.path.join(root, fn)
        if fn in ('jp.dic', 'en.dic'):
            t = open(p, encoding='utf-8-sig', errors='surrogateescape').read()
            for m in ENTRY.finditer(t):
                v = m.group(2)
                if v not in known and re.search(r'[A-Za-z]{2}', v) and not v.startswith('{'):
                    new.setdefault(v, p)
        elif fn.endswith('.sys'):
            for line in open(p, encoding='utf-8-sig', errors='surrogateescape').read().splitlines():
                m = re.match(r'^(title\d*|uninstallmes\d+)\s*=\s*(.*?)\s*$', line)
                if m and m.group(2) and m.group(2) not in known:
                    new.setdefault(m.group(2), p)
out = open(os.path.join(HERE, 'src2.txt'), 'w', encoding='utf-8', errors='surrogateescape')
for i, (v, p) in enumerate(sorted(new.items())):
    out.write(f'{i}\t{v.replace(chr(13), "").replace(chr(10), "<NL>")}\t{os.path.relpath(p, SRC)}\n')
print(len(new))
