import os, re, json, sys

SRC = sys.argv[1]
OUT = sys.argv[2]

DIC_RE = re.compile(r'^(\s*\{[^}]*\}\s*=\s*")(.*)(";?\s*)$')
STR_RE = re.compile(r'(\b(?:str|label)=")([^"]*)(")')


def translatable(s):
    t = s.strip()
    if not re.search(r'[A-Za-z]{2}', t):
        return False
    if t.startswith('{') or re.match(r'^-?\d+,\{', t):
        return False
    if re.fullmatch(r'(&#x?[0-9a-fA-F]+;)+', t):
        return False
    if re.fullmatch(r'Text\d+', t):
        return False
    return True


strings = {}
for root, _, files in os.walk(SRC):
    for f in files:
        p = os.path.join(root, f)
        if f == 'jp.dic':
            with open(p, encoding='utf-8-sig', errors='surrogateescape') as fh:
                for line in fh.read().splitlines():
                    m = DIC_RE.match(line)
                    if m and translatable(m.group(2)):
                        strings.setdefault(m.group(2), 0)
                        strings[m.group(2)] += 1
        elif f.endswith('.xml'):
            with open(p, encoding='utf-8-sig', errors='surrogateescape') as fh:
                for m in STR_RE.finditer(fh.read()):
                    if translatable(m.group(2)):
                        strings.setdefault(m.group(2), 0)
                        strings[m.group(2)] += 1

keys = sorted(strings)
with open(OUT, 'w', encoding='utf-8') as fh:
    json.dump(keys, fh, ensure_ascii=True, indent=0)
print(len(keys), sum(len(k) for k in keys))
