import os, struct, subprocess, sys
ROOT = 'vm/work/weston-root'
GUEST_LIST = 'vm/work/firmware-a-inspect/system_a.filelist.txt'
START = ['usr/bin/weston','usr/lib/aarch64-linux-gnu/libweston-10.so.0.0.1','usr/lib/aarch64-linux-gnu/libweston-desktop-10.so.0.0.1','usr/lib/aarch64-linux-gnu/libweston-10/drm-backend.so','usr/lib/aarch64-linux-gnu/weston/kiosk-shell.so','usr/lib/aarch64-linux-gnu/weston/libexec_weston.so.0.0.0','lib/aarch64-linux-gnu/libcap.so.2','lib/aarch64-linux-gnu/libselinux.so.1']
TABLE = {
 'libcap.so.2':'libcap2','libgcrypt.so.20':'libgcrypt20','libgpg-error.so.0':'libgpg-error0',
 'libselinux.so.1':'libselinux1','libpcre2-8.so.0':'libpcre2-8-0','libzstd.so.1':'libzstd1',
 'liblzma.so.5':'liblzma5','liblz4.so.1':'liblz4-1','libffi.so.8':'libffi8',
 'libglib-2.0.so.0':'libglib2.0-0','libgobject-2.0.so.0':'libglib2.0-0','libgio-2.0.so.0':'libglib2.0-0',
 'libxml2.so.2':'libxml2','libdw.so.1':'libdw1','libelf.so.1':'libelf1','libcap-ng.so.0':'libcap-ng0',
 'libaudit.so.1':'libaudit1','libmount.so.1':'libmount1','libblkid.so.1':'libblkid1','libuuid.so.1':'libuuid1',
 'libtinfo.so.6':'libtinfo6','libncurses.so.6':'libncurses6','libbz2.so.1.0':'libbz2-1.0','libacl.so.1':'libacl1',
 'libseccomp.so.2':'libseccomp2','libkeyutils.so.1':'libkeyutils1','libudev.so.1':'libudev1',
 'libsystemd.so.0':'libsystemd0','libwayland-server.so.0':'libwayland-server0','libwayland-client.so.0':'libwayland-client0',
 'libwayland-egl.so.1':'libwayland-egl1','libxkbcommon.so.0':'libxkbcommon0','libdrm.so.2':'libdrm2',
 'libgbm.so.1':'libgbm1','libseat.so.1':'libseat1','libinput.so.10':'libinput10','libevdev.so.2':'libevdev2',
 'libmtdev.so.1':'libmtdev1','libwacom.so.9':'libwacom9','libgudev-1.0.so.0':'libgudev-1.0-0',
 'libpixman-1.so.0':'libpixman-1-0','libexpat.so.1':'libexpat1','libexpatw.so.1':'libexpat1',
 'libstdc++.so.6':'libstdc++6','libgcc_s.so.1':'libgcc-s1','libc.so.6':'libc6','ld-linux-aarch64.so.1':'libc6',
 'libdl.so.2':'libc6','libpthread.so.0':'libc6','librt.so.1':'libc6','libm.so.6':'libc6',
 'libva.so.2':'libva2','libva-drm.so.2':'libva-drm2','liblcms2.so.2':'liblcms2-2',
 'libpipewire-0.3.so.0':'libpipewire-0.3-0','libdbus-1.so.3':'libdbus-1-3','libjpeg.so.62':'libjpeg62-turbo',
 'libpng16.so.16':'libpng16-16','libwebp.so.7':'libwebp7','libcrypt.so.1':'libcrypt1','libnsl.so.1':'libnsl2',
 'libcairo.so.2':'libcairo2','libpango-1.0.so.0':'libpango-1.0-0','libpangocairo-1.0.so.0':'libpangocairo-1.0-0',
 'libfreetype.so.6':'libfreetype6','libfontconfig.so.1':'libfontconfig1','libharfbuzz.so.0':'libharfbuzz0b',
 'libfribidi.so.0':'libfribidi0','libthai.so.0':'libthai0','libdatrie.so.1':'libdatrie1','libgraphite2.so.3':'libgraphite2-3',
 'libxcb.so.1':'libxcb1','libxcb-render.so.0':'libxcb-render0','libxcb-shm.so.0':'libxcb-shm0','libX11.so.6':'libx11-6',
 'libXext.so.6':'libxext6','libXrender.so.1':'libxrender1','libXau.so.6':'libxau6','libXdmcp.so.6':'libxdmcp6',
 'libbsd.so.0':'libbsd0','libmd.so.0':'libmd0','libpixman-1.so.0':'libpixman-1-0'}

def needed(path):
    b = open(path, 'rb').read()
    if b[:4] != b'\x7fELF' or b[4] != 2:
        return []
    e = '<' if b[5] == 1 else '>'
    phoff, = struct.unpack_from(e + 'Q', b, 0x20)
    phentsize, phnum = struct.unpack_from(e + 'HH', b, 0x36)
    segs, dyn = [], None
    for i in range(phnum):
        off = phoff + i * phentsize
        p_type, _f, p_off, p_va, _pa, p_fsz = struct.unpack_from(e + 'IIQQQQ', b, off)
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
    ents = [struct.unpack_from(e + 'qQ', b, o) for o in range(dyn[0], dyn[0] + dyn[1], 16)]
    strtab = next((v for t, v in ents if t == 5), None)
    out = []
    for tag, val in ents:
        if tag == 1:
            off = to_off(strtab + val)
            if off is not None:
                out.append(b[off:b.index(b'\x00', off)].decode('utf-8', 'replace'))
    return out

def provided():
    have = set()
    for base, _d, files in os.walk(ROOT):
        for f in files:
            have.add(f)
    for line in open(GUEST_LIST, encoding='utf-8', errors='replace'):
        low = line.replace('/', chr(92))
        if 'lib32' + chr(92) in low or 'armhf' in low:
            continue
        parts = line.split()
        if parts:
            have.add(parts[-1].split(chr(92))[-1])
    return have

def resolve():
    have = provided()
    missing = set()
    queue = [os.path.join(ROOT, s) for s in START]
    seen = set()
    while queue:
        p = queue.pop()
        for dep in needed(p):
            if dep in have or dep in missing:
                continue
            missing.add(dep)
    return sorted(missing)

for round_no in range(6):
    miss = resolve()
    pkgs = []
    unmapped = []
    for soname in miss:
        pkg = TABLE.get(soname)
        if pkg:
            if pkg not in pkgs:
                pkgs.append(pkg)
        else:
            unmapped.append(soname)
    print('round ' + str(round_no) + ': missing=' + ','.join(miss) + ' | unmapped=' + ','.join(unmapped), flush=True)
    if not pkgs:
        break
    res = subprocess.run([sys.executable, 'vm/work/debfetch.py'] + pkgs, capture_output=True, text=True)
    got = [l for l in res.stdout.splitlines() if 'FAILED' in l]
    print('  fetched ' + str(len(pkgs)) + ' pkgs' + (' with failures: ' + '; '.join(got) if got else ''), flush=True)
print('closure done', flush=True)