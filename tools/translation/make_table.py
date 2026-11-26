"""Create de.tsv by pairing every text location of the ENG folder with the GER folder.

usage: python make_table.py ENG_DIR GER_DIR de.tsv
Rows: file <TAB> id <TAB> English <TAB> German   (only where the two differ)
"""
import sys, os
from psxtext import files, kind, read, texts, enc

eng, ger, out = sys.argv[1:4]
rows, problems = [], []
for rel, p in files(eng):
    q = os.path.join(ger, rel)
    if not os.path.exists(q):
        problems.append(f'missing in GER: {rel}')
        continue
    k = kind(os.path.basename(rel))
    a, b = texts(read(p), k), texts(read(q), k)
    if [i for i, _ in a] != [i for i, _ in b]:
        problems.append(f'structure differs: {rel}')
        continue
    for (i, en), (_, de) in zip(a, b):
        if en != de:
            rows.append((rel, i, en, de))

with open(out, 'w', encoding='utf-8', errors='surrogateescape', newline='\n') as f:
    f.write('# file\tid\tEnglish (must match ENG folder)\tGerman\n')
    for r in rows:
        f.write('\t'.join(enc(x) for x in r) + '\n')
print(f'{len(rows)} rows -> {out}')
for x in problems:
    print('  ' + x)
