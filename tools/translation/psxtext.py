"""Shared helpers: find every translatable text in a PSX XMB mod folder.

A text location is identified by (relative file path, id):
  dic files (jp.dic / en.dic):  id = "KEY" or "KEY#n" for the n-th duplicate key
  xml files:                    id = "s<n>"  (n-th str="..."/label="..." attribute)
  sys files:                    id = "title" / "uninstallmes1" ... (line key)
"""
import os, re

ENTRY = re.compile(r'^(\{([^}\n]*)\}[ \t]*=[ \t]*")(.*?)("[ \t]*;)', re.S | re.M)
STR_RE = re.compile(r'(\b(?:str|label)=")([^"]*)(")')
SYS_RE = re.compile(r'^(title\d*|uninstallmes\d+)(\s*=\s*)(.*?)(\s*)$', re.M)


def kind(fn):
    if fn in ('jp.dic', 'en.dic'):
        return 'dic'
    if fn.endswith('.xml'):
        return 'xml'
    if fn.endswith('.sys'):
        return 'sys'
    return None


def read(p):
    return open(p, 'rb').read().decode('utf-8', errors='surrogateescape')


def write(p, text):
    open(p, 'wb').write(text.encode('utf-8', errors='surrogateescape'))


def files(root):
    for dp, _, fs in os.walk(root):
        for fn in sorted(fs):
            if kind(fn):
                p = os.path.join(dp, fn)
                yield os.path.relpath(p, root).replace('\\', '/'), p


def substitute(text, k, fn):
    """Call fn(id, value) for each text location; it returns the new value
    (or None to keep).  Returns the rewritten text."""
    if k == 'dic':
        seen = {}
        def rep(m):
            key = m.group(2)
            n = seen.get(key, 0)
            seen[key] = n + 1
            new = fn(key if n == 0 else f'{key}#{n}', m.group(3))
            return m.group(0) if new is None else m.group(1) + new + m.group(4)
        return ENTRY.sub(rep, text)
    if k == 'xml':
        cnt = [0]
        def rep(m):
            cnt[0] += 1
            new = fn(f's{cnt[0]}', m.group(2))
            return m.group(0) if new is None else m.group(1) + new + m.group(3)
        return STR_RE.sub(rep, text)
    def rep(m):
        new = fn(m.group(1), m.group(3))
        return m.group(0) if new is None else m.group(1) + m.group(2) + new + m.group(4)
    return SYS_RE.sub(rep, text)


def texts(text, k):
    out = []
    substitute(text, k, lambda i, v: out.append((i, v)))
    return out


# TSV cell escaping: real line breaks and tabs only (keeps \n, \" etc. readable)
def enc(s):
    return s.replace('\r\n', '<CRLF>').replace('\n', '<LF>').replace('\t', '<TAB>')


def dec(s):
    return s.replace('<CRLF>', '\r\n').replace('<LF>', '\n').replace('<TAB>', '\t')
