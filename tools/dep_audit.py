import os, re, struct, subprocess, tarfile

PAYLOAD = 'vm/packs/x6pro/weston.tar'
DEBS = 'vm/work/debs'
ROOT = 'vm/work/weston-root'
OUT = 'vm/dist/x6pro-pack/licenses'

def elf_needed(path):
    b = open(path, 'rb').read()
    phoff, = struct.unpack_from('<Q', b, 0x20)
    phentsize, phnum = struct.unpack_from('<HH', b, 0x36)
    segs = []
    dyn = None
    for i in range(phnum):
        o = phoff + i * phentsize
        p_type, _f, p_off, p_va, _pa, p_fsz = struct.unpack_from('<IIQQQQ', b, o)
        if p_type == 1:
            segs.append((p_va, p_off, p_fsz))
        if p_type == 2:
            dyn = (p_off, p_fsz)
    if not dyn:
        return []
    def v2o(va):
        for p_va, p_off, p_fsz in segs:
            if p_va <= va < p_va + p_fsz:
                return p_off + (va - p_va)
        return None
    dyn_off, dyn_sz = dyn
    strtab = strsz = None
    offs = []
    for o in range(dyn_off, dyn_off + dyn_sz, 16):
        tag, val = struct.unpack_from('<qQ', b, o)
        if tag == 0:
            break
        if tag == 1:
            offs.append(val)
        if tag == 5:
            strtab = val
        if tag == 10:
            strsz = val
    if strtab is None:
        return []
    base = v2o(strtab)
    names = []
    for va in offs:
        p = base + va
        end = b.index(b'\x00', p)
        names.append(b[p:end].decode())
    return names

with tarfile.open(PAYLOAD) as t:
    members = [m for m in t.getmembers() if m.isfile()]
    names = [m.name.lstrip('./') for m in members]
    t.extractall('vm/work/payload-check', filter='data')

elf_files = [n for n in names if n.endswith('.so') or '.so.' in os.path.basename(n) or os.path.basename(n) in ('weston', 'weston-desktop-shell')]
shipped = {}
for n in elf_files:
    p = os.path.join('vm/work/payload-check', n)
    try:
        for son in elf_needed(p):
            shipped.setdefault(os.path.basename(son), n)
    except Exception as exc:
        print('  parse fail ' + n + ': ' + str(exc))
print('shipped_lib_names=' + str(len(shipped)))
print('shipped=' + ', '.join(sorted(shipped)))

def deb_list(path):
    try:
        out = subprocess.run(['7z', 'l', '-ba', path], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return []
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 6:
            rows.append(parts[-1].replace('\\', '/'))
    return rows

debmap = {}
for f in sorted(os.listdir(DEBS)):
    if not f.endswith('.deb'):
        continue
    pkg = f.split('_')[0]
    ver = f.split('_')[1] if len(f.split('_')) > 1 else '?'
    for path in deb_list(os.path.join(DEBS, f)):
        debmap.setdefault(path, (pkg, ver, f))
print('deb_files_indexed=' + str(len(debmap)))

owner = {}
for son, src in shipped.items():
    stem = son.split('.so')[0]
    hit = None
    for path, info in debmap.items():
        if os.path.basename(path).startswith(stem + '.so'):
            hit = (path, info)
            break
    if hit:
        owner.setdefault(hit[1][0], set()).add(son)
    else:
        owner.setdefault('?unmapped', set()).add(son)
print('owners=' + str(len(owner)))
for pkg in sorted(owner):
    print('  ' + pkg + ' <- ' + ', '.join(sorted(owner[pkg])))