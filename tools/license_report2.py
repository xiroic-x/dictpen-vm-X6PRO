import os, io, re, fnmatch, gzip, lzma, subprocess, tarfile, shutil

DEBS = 'vm/work/debs'
ROOT = 'vm/work/weston-root'
OUT = 'vm/dist/x6pro-pack/licenses'
PAYLOAD = 'vm/packs/x6pro/weston.tar'
ZSTD = 'vm/tools/zstd/zstd.exe'
WESTON_PKGS = {'weston', 'libweston-10-0'}
TOKENS = ['public-domain', 'LGPL-2.1+', 'LGPL-2+', 'GPL-2+', 'GPL-2', 'BSD-3-clause', 'BSD-2-clause', 'MIT', 'Expat', 'X11', 'ISC', 'zlib', 'PD', '0BSD']

def ar_members(path):
    data = open(path, 'rb').read()
    if data[:8] != b'!<arch>\n':
        return []
    pos, out = 8, []
    while pos + 60 <= len(data):
        hdr = data[pos:pos+60]
        name = hdr[0:16].decode().strip()
        size = int(hdr[48:58].decode().strip())
        out.append((name, data[pos+60:pos+60+size]))
        pos += 60 + size + (size % 2)
    return out

def deb_files(deb):
    for name, body in ar_members(deb):
        if not name.startswith('data.tar'):
            continue
        try:
            if name.endswith('.xz'):
                raw = lzma.decompress(body)
            elif name.endswith('.gz'):
                raw = gzip.decompress(body)
            elif name.endswith('.zst'):
                raw = subprocess.run([ZSTD, '-d', '-c'], input=body, capture_output=True).stdout
            else:
                raw = body
            with tarfile.open(fileobj=io.BytesIO(raw)) as t:
                return [m.name.lstrip('./') for m in t.getmembers() if m.isfile()]
        except Exception as exc:
            print('  ! ' + deb + ': ' + str(exc))
    return []

index, pkgver = {}, {}
for f in sorted(os.listdir(DEBS)):
    if not f.endswith('.deb'):
        continue
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

by_pkg, weston_files, unmapped = {}, [], []
for p in shipped:
    pkg = owner(p)
    if pkg is None:
        unmapped.append(p)
    elif pkg in WESTON_PKGS:
        weston_files.append(p)
    else:
        by_pkg.setdefault(pkg, []).append(p)
print('shipped=' + str(len(shipped)) + ' dependency_pkgs=' + str(len(by_pkg)) + ' weston_own_files=' + str(len(weston_files)) + ' unmapped=' + str(len(unmapped)))
print('unmapped_list=' + str(unmapped))

def stanzas(txt):
    out, cur = [], {}
    for line in txt.splitlines():
        if not line.strip():
            if cur:
                out.append(cur)
                cur = {}
            continue
        if line[:1] in (' ', '\t'):
            continue
        if ':' in line:
            k, v = line.split(':', 1)
            cur[k.strip()] = v.strip()
    if cur:
        out.append(cur)
    return out

def tag_of(txt, path):
    hits = []
    for st in stanzas(txt):
        pat = st.get('Files')
        if not pat:
            continue
        for q in pat.split():
            q2 = q.rstrip('/')
            if q2 in ('*', './*') or fnmatch.fnmatch(path, q2) or path.startswith(q2 + '/'):
                hits.append(st)
                break
    if hits:
        return hits[-1].get('License', '').strip() or 'EMPTY'
    m = re.search(r'^License:\s*(.+)$', txt, re.M)
    if m:
        return m.group(1).strip() + ' (inferred)'
    for tok in TOKENS:
        if re.search(r'\b' + re.escape(tok) + r'\b', txt):
            return tok + ' (from-text)'
    return 'NOT-STATED'

os.makedirs(OUT, exist_ok=True)
for old in os.listdir(OUT):
    os.remove(os.path.join(OUT, old))
missing, summary, per_file, unknown = [], [], [], set()
for pkg in sorted(by_pkg):
    cp = os.path.join(ROOT, 'usr/share/doc', pkg, 'copyright')
    if not os.path.exists(cp):
        missing.append(pkg)
        continue
    shutil.copy2(cp, os.path.join(OUT, pkg + '.copyright'))
    txt = open(cp, encoding='utf-8', errors='replace').read()
    tags = set()
    for p in sorted(by_pkg[pkg]):
        tag = tag_of(txt, p)
        tags.add(tag)
        per_file.append((pkg, p, tag))
        if tag in ('NOT-STATED', 'EMPTY'):
            unknown.add((pkg, cp))
    summary.append((pkg, pkgver.get(pkg, '?'), len(by_pkg[pkg]), '; '.join(sorted(tags))))

L = ['# 第三方依赖许可清单', '']
L.append('范围：weston.tar 中除 Weston 本体之外的依赖库。Weston 本体（weston、libweston-10-0 两个包，共 ' + str(len(weston_files)) + ' 个文件）为 MIT 许可证，不在此逐条列出。')
L.append('')
L.append('生成方式：读 weston.tar 的真实文件 → 按 .deb 文件清单归属到 Debian 包 → 按各包 DEP-5 copyright 的 Files: 规则逐文件取 License: 字段。')
L.append('')
L.append('## 按包汇总（' + str(len(summary)) + ' 个包）')
L.append('')
L.append('| Debian 包 | 版本 | 文件数 | 适用协议 |')
L.append('|-----------|------|--------|----------|')
for pkg, ver, n, tags in summary:
    L.append('| `' + pkg + '` | ' + ver + ' | ' + str(n) + ' | ' + tags + ' |')
L.append('')
L.append('## 逐文件对应')
L.append('')
L.append('| 载荷内文件 | Debian 包 | 适用协议 |')
L.append('|------------|-----------|----------|')
for pkg, p, tag in sorted(per_file):
    L.append('| `' + p + '` | `' + pkg + '` | ' + tag + ' |')
L.append('')
L.append('各包完整许可文本见同目录的 <包名>.copyright（即 Debian /usr/share/doc/<包>/copyright）。')
open(os.path.join(OUT, 'README.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('report_pkgs=' + str(len(summary)) + ' report_files=' + str(len(per_file)) + ' missing=' + str(missing))
for pkg, ver, n, tags in summary:
    print('  ' + pkg + ' ' + ver + ' (' + str(n) + ') :: ' + tags)
print('needs_review=' + str(len(unknown)))
for pkg, cp in sorted(unknown):
    print('  [' + pkg + '] head: ' + ' / '.join(open(cp, encoding='utf-8', errors='replace').read().splitlines()[:4])[:160])