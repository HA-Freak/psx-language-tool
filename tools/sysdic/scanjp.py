import os,re,sys
sys.stdout.reconfigure(encoding='utf-8')
root=sys.argv[1]
J=re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]+[\u3040-\u30ff\u4e00-\u9fff\uff01-\uff5e・ー\w ]*')
for dp,_,fs in os.walk(root):
  for f in fs:
    p=os.path.join(dp,f)
    if f.lower().endswith(('.png','.bmp','.jpg','.ico','.pcm','.vag','.bin')): continue
    try: b=open(p,'rb').read()
    except: continue
    t=b.decode('utf-8','ignore')
    hits=[h for h in J.findall(t) if len(h)>=2]
    if hits:
      print(f'{len(hits):5d} {os.path.relpath(p,root)} :: {" | ".join(hits[:6])[:200]}')
