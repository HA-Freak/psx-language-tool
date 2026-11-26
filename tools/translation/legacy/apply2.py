"""Build a translated copy of the PSX XMB folder.

usage: apply2.py SRC DST LANG   (LANG = de | en)
Uses src.txt + LANG_*.txt (by id), extra_LANG.txt (literal EN<TAB>X pairs),
and key-based overrides for entries whose English text is ambiguous.
"""
import os, re, sys, glob, shutil
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, DST, LANG = sys.argv[1], sys.argv[2], sys.argv[3]

src = {}
with open(os.path.join(HERE, 'src.txt'), encoding='utf-8', errors='surrogateescape') as f:
    for line in f.read().split('\n'):
        if line:
            i, s = line.split('\t', 1)
            src[int(i)] = s

def fix(en, x):
    x = x.replace('„', "'").replace('“', "'").replace('–', '-')
    lead = re.match(r'^[ 　]*', en).group(0)
    trail = re.search(r'[ 　]*$', en).group(0)
    return lead + x.strip(' 　') + trail

mapping = {}
for p in sorted(glob.glob(os.path.join(HERE, LANG + '_*.txt'))):
    for line in open(p, encoding='utf-8').read().split('\n'):
        if line.strip():
            i, s = line.split('\t', 1)
            en = src[int(i)]
            mapping[en] = fix(en, s)
extra = os.path.join(HERE, f'extra_{LANG}.txt')
if os.path.exists(extra):
    for line in open(extra, encoding='utf-8').read().split('\n'):
        if line.strip():
            en, x = line.split('\t', 1)
            mapping[en] = fix(en, x)

WEEK = {'de': ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'],
        'en': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']}[LANG]
KEY_OVERRIDE = {}
for n in range(7):
    for k in (f'dow{n}', f'WeekStr_{n}', f'VIDEO_TEXT_WEEK{n}'):
        KEY_OVERRIDE[k] = WEEK[n]
KEY_OVERRIDE['Genre.16'] = 'Soul'
KEY_OVERRIDE['Message_Warning1'] = {
    'de': 'Video{NL}Musik{NL}Fotos{NL}Spiele, die die Festplatte nutzen{NL}Programmführer-Daten',
    'en': 'Videos{NL}Music{NL}Photos{NL}Games that use the hard disk{NL}Program guide data'}[LANG]
# malformed lines in the original files -> repaired
LINE_FIX = {
    '{mongon_str15} = "DVD burner;': '{mongon_str15} = "%s";' % {'de': 'DVD-Brenner', 'en': 'DVD burner'}[LANG],
    '{BACK} = Back";': '{BACK} = "%s";' % {'de': 'Zurück', 'en': 'Back'}[LANG],
}

ENTRY = re.compile(r'^(\{([^}\n]*)\}[ \t]*=[ \t]*")(.*?)("[ \t]*;)', re.S | re.M)
STR_RE = re.compile(r'(\b(?:str|label)=")([^"]*)(")')
SYS_RE = re.compile(r'^(title\d*|uninstallmes\d+)(\s*=\s*)(.*?)(\s*)$')

if os.path.exists(DST):
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
stats = Counter()
missing = Counter()

for root, _, files in os.walk(DST):
    for fn in files:
        p = os.path.join(root, fn)
        is_dic = fn in ('jp.dic', 'en.dic')
        if not (is_dic or fn.endswith('.xml') or fn.endswith('.sys')):
            continue
        raw = open(p, 'rb').read()
        text = raw.decode('utf-8', errors='surrogateescape')
        nl = '\r\n' if '\r\n' in text else '\n'
        if is_dic:
            if fn == 'jp.dic' and os.path.basename(os.path.dirname(root)) == 'pvrBurn_0' and '{Form_Err4}' not in text:
                add = {'de': r'Diese Disc ist eine DVD+R.\nSie wird im +VR-Format beschrieben.\nSind Sie sicher?',
                       'en': r'This disc is a DVD+R.\nIt will be written in +VR format.\nAre you sure?'}[LANG]
                m = re.search(r'^\{Form_Err3\}[^\n]*\n', text, re.M)
                text = text[:m.end()] + '{Form_Err4} = "' + add + '";' + nl + text[m.end():]
                text = re.sub(r'size="(\d+)"', lambda z: 'size="%d"' % (int(z.group(1)) + 1), text, count=1)
                stats['added'] += 1
            for bad, good in LINE_FIX.items():

                if bad in text:
                    text = text.replace(bad, good); stats['linefix'] += 1
            def rep(m):
                key, val = m.group(2), m.group(3)
                if key in KEY_OVERRIDE:
                    stats['key'] += 1
                    return m.group(1) + KEY_OVERRIDE[key].replace('{NL}', nl) + m.group(4)
                if val in mapping:
                    stats['dic'] += 1
                    return m.group(1) + mapping[val] + m.group(4)
                if re.search(r'[a-z]{3}', val) and not val.startswith(('/', '{')):
                    missing[val] += 1
                return m.group(0)
            text = ENTRY.sub(rep, text)
        elif fn.endswith('.xml'):
            out = []
            for line in text.split('\n'):
                if 'name="EnglishSelect"' not in line:
                    def rx(m):
                        if m.group(2) in mapping:
                            stats['xml'] += 1
                            return m.group(1) + mapping[m.group(2)] + m.group(3)
                        return m.group(0)
                    line = STR_RE.sub(rx, line)
                out.append(line)
            text = '\n'.join(out)
        else:
            out = []
            for line in text.split('\n'):
                m = SYS_RE.match(line)
                if m and m.group(3) in mapping:
                    line = m.group(1) + m.group(2) + mapping[m.group(3)] + m.group(4)
                    stats['sys'] += 1
                out.append(line)
            text = '\n'.join(out)
        new = text.encode('utf-8', errors='surrogateescape')
        if new != raw:
            open(p, 'wb').write(new)
            stats['files'] += 1
print(dict(stats))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
print('untranslated dic values (sample):')
for v, n in missing.most_common(60):
    print(f'  {n}x {v[:90]!r}')
