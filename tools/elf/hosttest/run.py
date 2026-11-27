"""Scenario test: runs test.exe (gui.c on the PC) against copies of the RepairBox system dumps."""
import os, sys, shutil, hashlib, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, 'test.exe')
PROJ = os.path.abspath(os.path.join(HERE, '..', '..', '..'))   # project root with the built folders
# RepairBox EN package (contains RepairBox-PSX1/PSX2-SystemFiles), extracted by tools/build_all.py
DUMPS = os.environ.get('PSX_DUMPS', os.path.join(PROJ, 'build', 'package'))
WORK = os.path.join(HERE, 'work')
SER = [('DESR-5000-5100-7000-7100', '', 'RepairBox-PSX1-SystemFiles'),
       ('DESR-5500-5700-7500-7700', 'xosd/packages/', 'RepairBox-PSX2-SystemFiles')]
LANGS = ['GER', 'ENG', 'POL', 'ESP']
fails = 0

def tree(root):
    r = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(dp, f)
            r[os.path.relpath(p, root).replace(os.sep, '/')] = hashlib.sha1(open(p, 'rb').read()).hexdigest()
    return r

def mod(s, l):
    name, prefix, _ = SER[s]
    root = os.path.join(PROJ, f'{name} XMB {LANGS[l]}')
    r = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            rel = os.path.relpath(os.path.join(dp, f), root).replace(os.sep, '/')
            if rel.startswith('xosd/packages/version_0/') or ' (2)' in f:
                continue
            r[prefix + rel] = hashlib.sha1(open(os.path.join(dp, f), 'rb').read()).hexdigest()
    return r

def run(root, action, *extra):
    env = dict(os.environ, PFSROOT=root)
    out = subprocess.run([EXE, action, *extra], env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print(f'  $ {action} {" ".join(extra)}  (rc {out.returncode})')
    for ln in out.stdout.splitlines():
        print('    ' + ln)
    if out.returncode:
        print(out.stderr)
    return out.stdout

def check(cond, what):
    global fails
    print(('  OK   ' if cond else '  FAIL ') + what)
    fails += not cond

def fresh(s, tag):
    dst = os.path.join(WORK, f'{s}_{tag}')
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(os.path.join(DUMPS, SER[s][2], '__system'), dst)
    return dst

def ignore_tool(t):
    return {k: v for k, v in t.items() if not k.startswith('langtool_bak/') and k != 'dic/jp.dic.bak'}

def installed_ok(root, s, l, orig):
    t = tree(root)
    m = mod(s, l)
    bad = [k for k in m if t.get(k) != m[k]]
    other = [k for k in orig if k not in m and k != 'dic/jp.dic' and t.get(k) != orig[k]]
    return bad, other, t

for s in (0, 1):
    print(f'\n##### {SER[s][0]}')
    orig = tree(os.path.join(DUMPS, SER[s][2], '__system'))
    m_eng = mod(s, 1)
    print(f'  pack files {len(m_eng)}, already on disk {sum(k in orig for k in m_eng)}, new {sum(k not in orig for k in m_eng)}')
    root = fresh(s, 'main')
    o = run(root, 'status')
    check(f'series={s}' in o, 'model detected')
    for l, act in ((0, 'ger'), (2, 'pol'), (3, 'esp'), (1, 'eng')):
        o = run(root, act)
        bad, other, t = installed_ok(root, s, l, orig)
        check(not bad and not other and 'ERRORS' not in o and f'xmb={["German","English","Polish","Spanish"][l]}' in o.split('after')[1],
              f'{act}: all {len(m_eng)} files correct, nothing else touched ({len(bad)} bad, {len(other)} other)')
        bak = {k[len('langtool_bak/'):]: v for k, v in t.items() if k.startswith('langtool_bak/') and k != 'langtool_bak/manifest.txt'}
        check(bak == {k: orig[k] for k in m_eng if k in orig}, f'{act}: backup = original files ({len(bak)})')
        if s == 1:
            dic = 'SYSTEM-DIC ' + LANGS[l]
            ref = hashlib.sha1(open(os.path.join(PROJ, dic, 'jp.dic'), 'rb').read()).hexdigest()
            check(t['dic/jp.dic'] == ref, f'{act}: jp.dic = {dic}')
            check(t.get('dic/jp.dic.bak') == orig['dic/jp.dic'], f'{act}: jp.dic.bak = original')
    man1 = open(os.path.join(root, 'langtool_bak/manifest.txt'), 'rb').read()
    o = run(root, 'mkbak')
    check(open(os.path.join(root, 'langtool_bak/manifest.txt'), 'rb').read() == man1 and 'already exists' in o, 'mkbak does not overwrite')
    o = run(root, 'restore')
    t = tree(root)
    diff = [k for k in set(orig) | set(ignore_tool(t)) if orig.get(k) != t.get(k)]
    check(not diff and 'ERRORS' not in o, f'restore: identical to original ({len(diff)} differences) {diff[:5]}')
    o = run(root, 'restore')
    t = tree(root)
    diff = [k for k in set(orig) | set(ignore_tool(t)) if orig.get(k) != t.get(k)]
    check(not diff and 'ERRORS' not in o, 'restore twice: still identical')
    if s == 1:
        run(root, 'pol')
        o = run(root, 'jpn')
        t = tree(root)
        check(t['dic/jp.dic'] == orig['dic/jp.dic'], 'jpn: original jp.dic written')

    # write failure during the backup -> nothing installed, no manifest
    root = fresh(s, 'failbak')
    o = run(root, 'ger', 'failwrite', '30')
    t = tree(root)
    check('backup failed' in o and 'langtool_bak/manifest.txt' not in t and ignore_tool(t) == orig,
          'write error in backup: aborted, system unchanged, no manifest')
    o = run(root, 'ger')
    bad, other, t = installed_ok(root, s, 0, orig)
    check(not bad and not other and 'ERRORS' not in o, 'retry after failed backup installs fine')
    bak = {k[len('langtool_bak/'):]: v for k, v in t.items() if k.startswith('langtool_bak/') and k != 'langtool_bak/manifest.txt'}
    check(bak == {k: orig[k] for k in m_eng if k in orig}, 'retry: backup = original files')
    run(root, 'restore')
    check(ignore_tool(tree(root)) == orig, 'restore after retry: identical to original')

    # write failure during install -> error reported, restore repairs
    root = fresh(s, 'failinst')
    n_exist = sum(k in orig for k in m_eng)
    o = run(root, 'pol', 'failwrite', str(n_exist + 2 + (1 if s == 1 else 0) + 20))
    check('ERRORS' in o, 'write error in install is reported')
    run(root, 'restore')
    check(ignore_tool(tree(root)) == orig, 'restore after failed install: identical to original')

    # screen size
    o = run(root, 'draw')

# model detection negatives
print('\n##### detection')
for tag, mk in (('empty', []), ('dic_only', ['dic']), ('both', ['dic', 'xosd/packages/Config_0'])):
    r = os.path.join(WORK, 'det_' + tag)
    shutil.rmtree(r, ignore_errors=True)
    os.makedirs(r)
    for d in mk:
        os.makedirs(os.path.join(r, d))
    o = run(r, 'status')
    check('series=-1' in o and 'menu=2' in o, f'{tag}: not recognised, only 2 menu items')
print('\nFAILS:', fails)
