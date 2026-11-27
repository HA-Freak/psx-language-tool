import os, re, sys, xml.dom.minidom as md
os.chdir(sys.argv[1])
BS = chr(92)
PAIRS = [(s + " XMB ENG", s + " XMB " + l)
         for s in ("DESR-5500-5700-7500-7700", "DESR-5000-5100-7000-7100")
         for l in ("GER", "POL", "ESP")]
for E, G in PAIRS:
    if not os.path.isdir(G):
        continue
    bad=0; q=0
    for root,_,fs in os.walk(G):
        for f in fs:
            g=os.path.join(root,f); e=g.replace(G,E,1)
            if f.endswith('.xml'):
                def ok(p):
                    try: md.parse(p); return True
                    except Exception: return False
                if ok(e) and not ok(g): bad+=1
            if f in ('jp.dic','en.dic'):
                t=open(g,encoding='utf-8',errors='replace').read()
                for m in re.finditer(r'^\{[^}]*\}\s*=\s*"(.*?)"\s*;',t,re.M|re.S):
                    v=m.group(1).replace(BS+'"','')
                    if '"' in v: q+=1; print('  ',g[len(G)+1:])
    print(G,'xml broken:',bad,'quote issues:',q)
