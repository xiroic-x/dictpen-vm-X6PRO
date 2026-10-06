import os, io, re, fnmatch, gzip, lzma, subprocess, tarfile, shutil

DEBS = 'vm/work/debs'
ROOT = 'vm/work/weston-root'
OUT = 'vm/dist/x6pro-pack/licenses'
PAYLOAD = 'vm/packs/x6pro/weston.tar'
ZSTD = 'vm/tools/zstd/zstd.exe'
WESTON = {'weston', 'libweston-10-0'}

# 证据化覆盖：二进制路径匹配不到源码目录时，按库名 + 版权文件原文定案
OVERRIDE = {
    'libblkid1': ('LGPL-2.1+', 'Files: libblkid/* -> License: LGPL-2.1+'),
    'libmount1': ('LGPL-2.1+', 'Files: libmount/* -> License: LGPL-2.1+'),
    'libuuid1': ('BSD-3-clause', 'Files: libuuid/* -> License: BSD-3-clause'),
    'libaudit1': ('LGPL-2.1', 'Files: lib/* -> License: LGPL-2.1 (Files: * 为 GPL-2，库取 LGPL)'),
    'libgcrypt20': ('LGPL-2.1+', '版权文件原文 License (library): LGPLv2.1+（manual and tools 为 GPLv2+）'),
}

def ar_members(path):
    data = open(path, 'rb').read()
    if data[:8] != b'!<arch>\n':
        return []
    pos, out = 8, []
    while pos + 60 <= len(data):
        hdr = data[pos:pos+60]
        out.append((hdr[0:16].decode().strip(), data[pos+60:pos+60+int(hdr[48:58].decode().strip())]))
        pos += 60 + int(hdr[48:58].decode().strip()) + (int(hdr[48:58].decode().strip()) % 2)
    return out

def deb_files(deb):
    for name, body in ar_members(deb):
        if not name.startswith('data.tar'):
            continue
        try:
            raw = lzma.decompress(body) if name.endswith('.xz') else gzip.decompress(body) if name.endswith('.gz') else subprocess.run([ZSTD, '-d', '-c'], input=body, capture_output=True).stdout if name.endswith('.zst') else body
            with tarfile.open(fileobj=io.BytesIO(raw)) as t:
                return [m.name.lstrip('./') for m in t.getmembers() if m.isfile()]
        except Exception:
            pass
    return []

index, pkgver = {}, {}
for f in sorted(os.listdir(DEBS)):
    if f.endswith('.deb'):
        p = f[:-4].split('_')
        pkgver[p[0]] = p[1] if len(p) > 1 else '?'
        for path in deb_files(os.path.join(DEBS, f)):
            index.setdefault(path, p[0])

with tarfile.open(PAYLOAD) as t:
    shipped = sorted(m.name.lstrip('./') for m in t.getmembers() if m.isfile())

def owner(path):
    if path in index:
        return index[path]
    stem = os.path.basename(path).split('.so')[0]
    for p, pkg in index.items():
        if os.path.basename(p).split('.so')[0] == stem:
            return pkg
    return None

by_pkg, n_weston, unmapped = {}, 0, []
for p in shipped:
    pkg = owner(p)
    if pkg is None:
        unmapped.append(p)
    elif pkg in WESTON:
        n_weston += 1
    else:
        by_pkg.setdefault(pkg, []).append(p)

def stanzas(txt):
    out, cur, key, lic = [], {}, None, []
    for line in txt.splitlines():
        if not line.strip():
            if cur:
                cur['_lic'] = ' '.join(lic).strip()
                out.append(cur)
                cur, lic = {}, []
            key = None
            continue
        if line[:1] in (' ', '\t'):
            if key == 'License':
                lic.append(line.strip())
            continue
        if ':' in line:
            k, v = line.split(':', 1)
            cur[k.strip()] = v.strip()
            key = k.strip()
    if cur:
        cur['_lic'] = ' '.join(lic).strip()
        out.append(cur)
    return out

def best_stanza(txt, path):
    stem = os.path.basename(path).split('.so')[0]
    cands = []
    for st in stanzas(txt):
        pat = st.get('Files')
        lic = (st.get('License') or st.get('_lic') or '').strip()
        if not pat or not lic:
            continue
        for q in pat.split():
            q2 = q.rstrip('/')
            base = os.path.basename(q2).split('.so')[0].rstrip('*').rstrip('/')
            if q2 in ('*', './*'):
                cands.append((1, q2, lic))
            elif base and base == stem:
                cands.append((50 + len(q2), q2, lic))
            elif fnmatch.fnmatch(path, q2):
                cands.append((20 + len(q2), q2, lic))
            break
    cands.sort(key=lambda x: x[0], reverse=True)
    return cands[0] if cands else None

def plain_tag(txt):
    t = txt.lower()
    if 'permission is hereby granted, free of charge' in t:
        return 'MIT (X11/MIT 文本)'
    if 'public domain' in t or 'not copyrighted' in t:
        return 'public-domain'
    if 'gnu lesser general public license' in t:
        return 'LGPL (文本声明)'
    if 'gnu general public license' in t:
        return 'GPL (文本声明)'
    return 'SEE-COPYRIGHT-FILE'

os.makedirs(OUT, exist_ok=True)
for old in os.listdir(OUT):
    os.remove(os.path.join(OUT, old))
rows, details = [], []
for pkg in sorted(by_pkg):
    cp = os.path.join(ROOT, 'usr/share/doc', pkg, 'copyright')
    txt = open(cp, encoding='utf-8', errors='replace').read()
    shutil.copy2(cp, os.path.join(OUT, pkg + '.copyright'))
    if pkg in OVERRIDE:
        tag, basis = OVERRIDE[pkg]
    else:
        pick = best_stanza(txt, sorted(by_pkg[pkg])[0])
        tag, basis = (pick[2], pick[1] + ' -> ' + pick[2]) if pick else (plain_tag(txt), '版权文件为纯文本，按其中许可声明判定')
    rows.append((pkg, pkgver.get(pkg, '?'), len(by_pkg[pkg]), tag, basis))
    details.append((pkg, sorted(by_pkg[pkg])))

L = ['# 第三方依赖许可清单', '']
L.append('- 范围：`weston.tar` 中 **除 Weston 本体之外**的依赖（' + str(len(rows)) + ' 个 Debian 包 / ' + str(sum(r[2] for r in rows)) + ' 个文件）。')
L.append('- Weston 本体（包 `weston`、`libweston-10-0`，共 ' + str(n_weston) + ' 个文件）为 **MIT**，不在此逐条列出。')
L.append('- 未匹配到任何 Debian 包的文件：' + (str(unmapped) if unmapped else '无') + '。')
L.append('- 判定依据：读 `weston.tar` 真实文件 → 按 `.deb` 文件清单归属到包 → 按各包 `/usr/share/doc/<包>/copyright`（DEP-5 或纯文本）判定，逐条列出依据。')
L.append('')
L.append('## 依赖协议总表')
L.append('')
L.append('| Debian 包 | 版本 | 载荷内文件数 | 协议 | 依据 |')
L.append('|-----------|------|--------------|------|------|')
for pkg, ver, n, tag, basis in rows:
    L.append('| `' + pkg + '` | ' + ver + ' | ' + str(n) + ' | **' + tag + '** | ' + basis.replace('|', '/') + ' |')
L.append('')
L.append('## 逐文件对应')
L.append('')
for pkg, files in details:
    tag = [r[3] for r in rows if r[0] == pkg][0]
    for f in files:
        L.append('- `' + f + '` —— `' + pkg + '`（' + tag + '）')
L.append('')
L.append('每个包的完整许可文本见同目录 `<包名>.copyright`（即 Debian `/usr/share/doc/<包>/copyright` 原件）。')
open(os.path.join(OUT, 'README.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('pkgs=' + str(len(rows)) + ' files=' + str(sum(r[2] for r in rows)) + ' weston_files=' + str(n_weston) + ' unmapped=' + str(len(unmapped)))
for pkg, ver, n, tag, basis in rows:
    print('  ' + pkg.ljust(16) + ' ' + ver.ljust(18) + str(n).rjust(2) + '  ' + tag)