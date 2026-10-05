import os, shutil
SRC = 'vm/work/weston-root'
DST = 'vm/packs/x6pro/weston'
EXACT = ['usr/bin/weston',
 'usr/lib/aarch64-linux-gnu/libweston-10/drm-backend.so',
 'usr/lib/aarch64-linux-gnu/libweston-10/headless-backend.so',
 'usr/lib/aarch64-linux-gnu/weston/kiosk-shell.so',
 'usr/lib/aarch64-linux-gnu/weston-desktop-shell']
PREFIX = ['libweston-10.so','libweston-desktop-10.so','libexec_weston.so','libgbm.so','libpixman-1.so',
 'libinput.so','libevdev.so','libmtdev.so','libwacom.so','libgudev-1.0.so','libseat.so','libdrm.so',
 'libudev.so','libsystemd.so','libxkbcommon.so','libexpat.so','libva.so','libva-drm.so','libdbus-1.so',
 'libzstd.so','liblzma.so','liblz4.so','libffi.so','libmount.so','libblkid.so','libuuid.so',
 'libpcre2-8.so','libgcrypt.so','libgpg-error.so','libcap-ng.so','libaudit.so','libglib-2.0.so',
 'libgobject-2.0.so','libgio-2.0.so','libselinux.so','libcap.so','libz.so']
def put(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.islink(src):
        real = os.path.realpath(src)
        if os.path.exists(real):
            shutil.copy2(real, dst)
            return os.path.getsize(real)
        return 0
    shutil.copy2(src, dst)
    return os.path.getsize(src)
total = 0
for rel in EXACT:
    src = os.path.join(SRC, rel)
    if os.path.exists(src):
        total += put(src, os.path.join(DST, rel))
    else:
        print('MISSING ' + rel)
for libdir in ('usr/lib/aarch64-linux-gnu', 'lib/aarch64-linux-gnu'):
    full = os.path.join(SRC, libdir)
    if not os.path.isdir(full):
        continue
    for name in sorted(os.listdir(full)):
        if not any(name.startswith(p) for p in PREFIX):
            continue
        total += put(os.path.join(full, name), os.path.join(DST, libdir, name))
print('copied bytes: ' + str(total))
print('files: ' + str(sum(len(f) for _b, _d, f in os.walk(DST))))
print('dirs: ' + ', '.join(sorted(os.listdir(DST))))
missing_soname = []
for libdir in ('usr/lib/aarch64-linux-gnu', 'lib/aarch64-linux-gnu'):
    full = os.path.join(DST, libdir)
    if os.path.isdir(full):
        missing_soname += [n for n in os.listdir(full) if '.so.' in n]
print('libs in pack: ' + str(len(missing_soname)))