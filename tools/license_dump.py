import os, re
ROOT = 'vm/work/weston-root'
PKGS = ['libgcrypt20','liblzma5','libblkid1','libmount1','libuuid1','libxkbcommon0','libaudit1','libdrm2','libpixman-1-0','libselinux1']

def stanzas(txt):
    out, cur, key, liclines = [], {}, None, []
    for line in txt.splitlines():
        if not line.strip():
            if cur:
                cur['_lic'] = ' '.join(liclines)[:110]
                out.append(cur)
                cur, liclines = {}, []
            key = None
            continue
        if line[:1] in (' ', '\t'):
            if key == 'License':
                liclines.append(line.strip())
            continue
        if ':' in line:
            k, v = line.split(':', 1)
            cur[k.strip()] = v.strip()
            key = k.strip()
    if cur:
        cur['_lic'] = ' '.join(liclines)[:110]
        out.append(cur)
    return out

for pkg in PKGS:
    cp = os.path.join(ROOT, 'usr/share/doc', pkg, 'copyright')
    if not os.path.exists(cp):
        print('[' + pkg + '] NO COPYRIGHT')
        continue
    txt = open(cp, encoding='utf-8', errors='replace').read()
    st = stanzas(txt)
    print('==== ' + pkg + ' (stanzas=' + str(len(st)) + ') ====')
    for s in st:
        f = s.get('Files')
        lic = s.get('_lic') or s.get('License', '')
        if not f and not lic:
            continue
        print('  Files: ' + (f or '-')[:70] + '   =>   ' + (lic or '-')[:90])