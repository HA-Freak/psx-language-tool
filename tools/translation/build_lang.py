"""Build a translated mod from the English mod (the base) and a language table.

usage: python build_lang.py ENG_DIR TABLE.tsv OUT_DIR [--ascii] [--list]
  German:  python build_lang.py ENG de.tsv GER
  Polish:  python build_lang.py ENG pl.tsv POL --ascii

--ascii  replaces letters the PSX system font (SGR_SCE.TTF) cannot show:
         a-ogonek c-acute e-ogonek l-stroke n-acute s-acute z-acute z-dot -> a c e l n s z z
         (o-acute is in the font and is kept).  pl.tsv itself keeps full Polish.

* Copies ENG_DIR to OUT_DIR and replaces every text listed in the table.
* A row is only applied if its English column still equals the text in ENG_DIR.
  If you changed an English text, the row is reported as STALE and the
  English text stays in the output - update the row (both columns) in the table.
* English-looking texts without a row are reported as UNTRANSLATED (informational:
  names, technical terms etc. are intentionally left English).
"""
import sys, os, re, shutil
from collections import Counter
from psxtext import files, kind, read, write, substitute, dec

eng, table, out = sys.argv[1:4]
ASCII = str.maketrans('ąćęłńśźżĄĆĘŁŃŚŹŻ', 'acelnszzACELNSZZ')
conv = (lambda t: t.translate(ASCII)) if '--ascii' in sys.argv else (lambda t: t)
rows = {}
for ln, line in enumerate(open(table, encoding='utf-8', errors='surrogateescape').read().split('\n'), 1):
    if not line or line.startswith('#'):
        continue
    parts = line.split('\t')
    if len(parts) != 4:
        sys.exit(f'{table}:{ln}: expected 4 tab-separated columns, got {len(parts)}')
    f, i, en, de = (dec(x) for x in parts)
    rows[(f, i)] = (en, de)

if os.path.exists(out):
    shutil.rmtree(out)
shutil.copytree(eng, out)

stats, stale, untranslated, used = Counter(), [], Counter(), set()
for rel, p in files(out):
    k = kind(os.path.basename(rel))
    text = read(p)

    def fn(i, val):
        r = rows.get((rel, i))
        if r is None:
            if re.search(r'[A-Za-z]{4}', val) and not val.startswith(('/', '{', 'pack:')):
                untranslated[val] += 1
            return None
        used.add((rel, i))
        en, de = r
        if en != val:
            stale.append(f'{rel} [{i}]\n      table: {en[:70]!r}\n      ENG:   {val[:70]!r}')
            return None
        stats[k] += 1
        return conv(de)

    new = substitute(text, k, fn)
    if new != text:
        write(p, new)
        stats['files'] += 1

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
print('applied:', dict(stats))
unused = [k for k in rows if k not in used]
if stale:
    print(f'\nSTALE rows ({len(stale)}) - English text changed, kept English:')
    for s in stale:
        print('  ' + s)
if unused:
    print(f'\nrows whose location no longer exists ({len(unused)}):')
    for f, i in unused[:50]:
        print(f'  {f} [{i}]')
print(f'\n{len(untranslated)} distinct English-looking texts without a row (see --list)')
if '--list' in sys.argv:
    for v, n in untranslated.most_common():
        print(f'  {n}x {v[:90]!r}')
