import os, struct, subprocess, sys
ROOT = 'vm/work/weston-root'
GUEST_LIST = 'vm/work/firmware-a-inspect/system_a.filelist.txt'
TARGETS = ['usr/bin/weston','usr/lib/aarch64-linux-gnu/libweston-10.so.0.0.1','usr/lib/aarch64-linux-gnu/libweston-desktop-10.so.0.0.1','usr/lib/aarch64-linux-gnu/libweston-10/drm-backend.so','usr/lib/aarch64-linux-gnu/libweston-10/headless-backend.so','usr/lib/aarch64-linux-gnu/weston/desktop-shell.so','usr/lib/aarch64-linux-gnu/weston/kiosk-shell.so','usr/lib/aarch64-linux-gnu/weston/libexec_weston.so.0.0.0','usr/lib/aarch64-linux-gnu/weston-desktop-shell','usr/lib/aarch64-linux-gnu/weston-keyboard','usr/lib/aarch64-linux-gnu/libgbm.so.1.0.0','usr/lib/aarch64-linux-gnu/libpixman-1.so.0.42.2','usr/lib/aarch64-linux-gnu/libinput.so.10.13.0','usr/lib/aarch64-linux-gnu/libseat.so.1.0.0','usr/lib/aarch64-linux-gnu/libva-drm.so.2.1700.0']
TABLE = {'libcap.so.2':'libcap2','libselinux.so.1':'libselinux1','libpcre2-8.so.0':'libpcre2-8-0','libzstd.so.1':'libzstd1','liblzma.so.5':'liblzma5','libgcrypt.so.20':'libgcrypt20','liblz4.so.1':'liblz4-1','libffi.so.8':'libffi8','libglib-2.0.so.0':'libglib2.0-0','libgobject-2.0.so.0':'libglib2.0-0','libgio-2.0.so.0':'libglib2.0-0','libxml2.so.2':'libxml2','libdw.so.1':'libdw1','libelf.so.1':'libelf1','libgpg-error.so.0':'libgpg-error0','libcap-ng.so.0':'libcap-ng0','libaudit.so.1':'libaudit1','libmount.so.1':'libmount1','libblkid.so.1':'libblkid1','libuuid.so.1':'libuuid1','libtinfo.so.6':'libtinfo6','libncurses.so.6':'libncurses6','libudev.so.1':'libudev1','libsystemd.so.0':'libsystemd0','libwayland-server.so.0':'libwayland-server0','libwayland-client.so.0':'libwayland-client0','libwayland-egl.so.1':'libwayland-egl1','libxkbcommon.so.0':'libxkbcommon0','libdrm.so.2':'libdrm2','libgbm.so.1':'libgbm1','libseat.so.1':'libseat1','libinput.so.10':'libinput10','libevdev.so.2':'libevdev2','libmtdev.so.1':'libmtdev1','libwacom.so.9':'libwacom9','libgudev-1.0.so.0':'libgudev-1.0-0','libpixman-1.so.0':'libpixman-1-0','libexpat.so.1':'libexpat1','libexpatw.so.1':'libexpat1','libstdc++.so.6':'libstdc++6','libgcc_s.so.1':'libgcc-s1','libc.so.6':'libc6','ld-linux-aarch64.so.1':'libc6','libdl.so.2':'libc6','libpthread.so.0':'libc6','librt.so.1':'libc6','libm.so.6':'libc6','libva.so.2':'libva2','libva-drm.so.2':'libva-drm2','liblcms2.so.2':'liblcms2-2','libpipewire-0.3.so.0':'libpipewire-0.3-0','libdbus-1.so.3':'libdbus-1-3','libjpeg.so.8':'libjpeg62-turbo','libpng16.so.16':'libpng16-16','libwebp.so.7':'libwebp7'}

def needed(path):
    b = open(path, 'rb').read()
    if b[:4] != b'\x7fELF':
        return []
    is64 = b[4] == 2
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
    ents = []
    for o in range(dyn[0], dyn[0] + dyn[1], 16):
        ents.append(struct.unpack_from(e + 'qQ', b, o))
    strtab = next((v for t, v in ents if t == 5), None)
    out = []
    for tag, val in ents:
        if tag == 1:
            off = to_off(strtab + val)
            if off is not None:
                out.append(b[off:b.index(b'\x00', off)].decode('utf-8', 'replace'))
    return out

have = set()
for base, _d, files in os.walk(ROOT):
    for f in files:
        have.add(f)
for line in open(GUEST_LIST, 'r', encoding='utf-8', errors='replace'):
    parts = line.split()
    if parts:
        have.add(parts[-1].split('\\')[-1])
missing = set()
for t in TARGETS:
    p = os.path.join(ROOT, t)
    if not os.path.exists(p):
        print('MISSING FILE ' + t)
        continue
    for dep in needed(p):
        if dep not in have:
            missing.add(dep)
print('missing sonames: ' + ', '.join(sorted(missing)))
pkgs = []
for soname in sorted(missing):
    pkg = TABLE.get(soname)
    if pkg and pkg not in pkgs:
        pkgs.append(pkg)
    elif not pkg:
        print('  !! no package mapping for ' + soname)
print('fetching: ' + ' '.join(pkgs))
if pkgs:
    subprocess.run([sys.executable, 'vm/work/debfetch.py'] + pkgs, check=False)