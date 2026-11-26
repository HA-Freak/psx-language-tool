"""Create cleaned ENG folder + de/pl tables for the DESR-5000 mod."""
import sys,os,re,shutil
T=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/translation
sys.path.insert(0,T)
from psxtext import files,kind,read,write,substitute,enc,dec
src,eng,tdir,miss,tr=sys.argv[1:6]
# previous tables: English -> translation (by text)
old={'de':{},'pl':{}}
for lang in old:
    for l in open(os.path.join(T,lang+'.tsv'),encoding='utf-8').read().split('\n'):
        if l and l[0]!='#':
            f,i,e,x=[dec(p) for p in l.split('\t')]; old[lang].setdefault(e,x)
# new texts: number -> original english (from miss dump), number -> (clean, de, pl)
num={}
for l in open(miss,encoding='utf-8').read().split('\n'):
    if l and not l.startswith('## '):
        n,t=l.split('\t',1); num[int(n)]=dec(t)
new={}
for l in open(tr,encoding='utf-8').read().split('\n'):
    if not l: continue
    n,c,d,p=l.split('\t'); o=num[int(n)]
    def v(x,base): return '' if x=='<EMPTY>' else (base if x=='=' else dec(x))
    c2=v(c,o); new[o]=(c2,v(d,c2),v(p,c2))
if os.path.exists(eng): shutil.rmtree(eng)
shutil.copytree(src,eng)
rows={'de':[],'pl':[]}; miss_cnt=0
for rel,p in files(eng):
    k=kind(os.path.basename(rel)); text=read(p)
    def fn(i,val):
        global miss_cnt
        if val in new:
            c,d,pl=new[val]
        elif val in old['de']:
            c,d,pl=val,old['de'][val],old['pl'].get(val,val)
        else:
            if re.search('[A-Za-z]{2}',val): miss_cnt+=1
            return None
        if d!=c: rows['de'].append((rel,i,c,d))
        if pl!=c: rows['pl'].append((rel,i,c,pl))
        return c if c!=val else None
    nt=substitute(text,k,fn)
    if nt!=text: write(p,nt)
hdr={'de':'German','pl':'Polish (full diacritics; build strips them for the PSX font)'}
for lang,R in rows.items():
    with open(os.path.join(tdir,lang+'5000.tsv'),'w',encoding='utf-8',newline='\n') as f:
        f.write(f'# file\tid\tEnglish (must match DESR-5000 ENG folder)\t{hdr[lang]}\n')
        for r in R: f.write('\t'.join(enc(x) for x in r)+'\n')
    print(lang,len(R))
print('unmatched',miss_cnt)
