import gzip, io, lzma, os, struct, subprocess, sys, tarfile, urllib.request

MIRROR = os.environ.get('DEB_MIRROR', 'https://mirrors.aliyun.com/debian')
SUITE = os.environ.get('DEB_SUITE', 'bookworm')
ARCH = 'arm64'
OUT = os.path.join('vm', 'work')
DEBS = os.path.join(OUT, 'debs')
ROOT = os.path.join(OUT, 'weston-root')
ZSTD = os.path.join('vm', 'tools', 'zstd', 'zstd.exe')

def fetch(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print('get ' + url, flush=True)
    with urllib.request.urlopen(url, timeout=300) as r, open(dest, 'wb') as f:
        f.write(r.read())
    return dest

def build_index():
    url = MIRROR + '/dists/' + SUITE + '/main/binary-' + ARCH + '/Packages.gz'
    raw = urllib.request.urlopen(url, timeout=300).read()
    idx, name = {}, None
    for line in gzip.decompress(raw).decode('utf-8', 'replace').splitlines():
        if line.startswith('Package: '):
            name = line.split(': ', 1)[1].strip()
        elif line.startswith('Filename: ') and name:
            idx[name] = line.split(': ', 1)[1].strip()
            name = None
    return idx

def ar_members(path):
    blob = open(path, 'rb').read()
    pos, out = 8, []
    while pos + 60 <= len(blob):
        hdr = blob[pos:pos + 60]
        try:
            size = int(hdr[48:58].decode().strip())
        except ValueError:
            break
        name = hdr[0:16].decode().strip().rstrip('/')
        start = pos + 60
        out.append((name, blob[start:start + size]))
        pos = start + size + (size % 2)
    return out

def unpack_data(deb, dest):
    members = dict(ar_members(deb))
    payloads = [v for k, v in members.items() if k.startswith('data.tar')]
    if not payloads:
        return []
    raw = payloads[0]
    if raw[:2] == b'\x1f\x8b':
        stream = io.BytesIO(gzip.decompress(raw))
    elif raw[:6] == b'\xfd7zXZ\x00':
        stream = io.BytesIO(lzma.decompress(raw))
    elif raw[:4] == b'\x28\xb5\x2f\xfd':
        tmp = os.path.join(DEBS, 'data.tar.zst')
        open(tmp, 'wb').write(raw)
        out = os.path.join(DEBS, 'data.tar')
        subprocess.run([ZSTD, '-d', '-f', '-q', tmp, '-o', out], check=True)
        stream = open(out, 'rb')
    else:
        raise RuntimeError('unknown data.tar compression for ' + deb)
    tf = tarfile.open(fileobj=stream)
    names = [m.name for m in tf.getmembers()]
    tf.extractall(dest)
    return names

def needed(path):
    b = open(path, 'rb').read()
    if b[:4] != b'\x7fELF':
        return []
    is64 = b[4] == 2
    e = '<' if b[5] == 1 else '>'
    if is64:
        phoff, = struct.unpack_from(e + 'Q', b, 0x20)
        phentsize, phnum = struct.unpack_from(e + 'HH', b, 0x36)
    else:
        phoff, = struct.unpack_from(e + 'I', b, 0x1c)
        phentsize, phnum = struct.unpack_from(e + 'HH', b, 0x2a)
    segs, dyn = [], None
    for i in range(phnum):
        off = phoff + i * phentsize
        if is64:
            p_type, _f, p_off, p_va, _pa, p_fsz = struct.unpack_from(e + 'IIQQQQ', b, off)
        else:
            p_type, p_off, p_va, _pa, p_fsz, _f = struct.unpack_from(e + 'IIIIII', b, off)
        if p_type == 1:
            segs.append((p_va, p_off, p_fsz))
        elif p_type == 2:
            dyn = (p_off, p_fsz)
    if not dyn:
        return []
    def to_off(va):
        for sva, soff, ssz in segs:
            if sva <= va < sva + ssz:
                return soff + (va - sva)
        return None
    ents = []
    step = 16 if is64 else 8
    for o in range(dyn[0], dyn[0] + dyn[1], step):
        ents.append(struct.unpack_from(e + ('qQ' if is64 else 'iI'), b, o))
    strtab = next((v for t, v in ents if t == 5), None)
    out = []
    for tag, val in ents:
        if tag != 1:
            continue
        off = to_off(strtab + val)
        if off is None:
            continue
        out.append(b[off:b.index(b'\x00', off)].decode('utf-8', 'replace'))
    return out

def main():
    want = sys.argv[1:]
    idx = build_index()
    for pkg in want:
        if pkg not in idx:
            print('!! not in index: ' + pkg, flush=True)
            continue
        url = MIRROR + '/' + idx[pkg]
        dest = os.path.join(DEBS, os.path.basename(idx[pkg]))
        try:
            fetch(url, dest)
            names = unpack_data(dest, ROOT)
            print('  ' + pkg + ': ' + str(len(names)) + ' files', flush=True)
        except Exception as exc:
            print('  ' + pkg + ': FAILED ' + str(exc), flush=True)
    print('=== binaries and their NEEDED ===')
    for base, _dirs, files in sorted(os.walk(ROOT)):
        for f in sorted(files):
            p = os.path.join(base, f)
            deps = needed(p)
            if not deps:
                continue
            print('  ' + os.path.relpath(p, ROOT).replace('\\', '/') + ' : ' + ' '.join(deps), flush=True)
    print('=== done ===')

main()