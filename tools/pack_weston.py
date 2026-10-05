import os, shutil
SRC = 'vm/work/weston-root'
DST = 'vm/packs/melon-pro/weston'
FILES = [
 'usr/bin/weston',
 'usr/lib/aarch64-linux-gnu/libweston-10.so.0.0.1',
 'usr/lib/aarch64-linux-gnu/libweston-desktop-10.so.0.0.1',
 'usr/lib/aarch64-linux-gnu/libweston-10/drm-backend.so',
 'usr/lib/aarch64-linux-gnu/libweston-10/headless-backend.so',
 'usr/lib/aarch64-linux-gnu/weston/kiosk-shell.so',
 'usr/lib/aarch64-linux-gnu/weston/libexec_weston.so.0.0.0',
 'usr/lib/aarch64-linux-gnu/weston-desktop-shell',
]
LIBS = ['libgbm.so.1.0.0','libpixman-1.so.0.42.2','libinput.so.10.13.0','libevdev.so.2.3.0','libmtdev.so.1.0.0',
        'libwacom.so.9.0.0','libgudev-1.0.so.0.3.0','libseat.so.1.0.0','libdrm.so.2.4.0','libudev.so.1.7.5',
        'libsystemd.so.0.35.0','libxkbcommon.so.0.0.0','libexpat.so.1.8.10','libva.so.2.1700.0',
        'libva-drm.so.2.1700.0','libdbus-1.so.3.32.0','libzstd.so.1.5.4','liblzma.so.5.4.1',
        'liblz4.so.1.9.4','libffi.so.8.1.2','libmount.so.1.1.0','libblkid.so.1.1.0','libuuid.so.1.3.0',
        'libpcre2-8.so.0.11.2','libgcrypt.so.20.4.1','libgpg-error.so.0.34.0','libcap-ng.so.0.0.0',
        'libaudit.so.1.0.0','libglib-2.0.so.0.7400.6','libgobject-2.0.so.0.7400.6','libgio-2.0.so.0.7400.6',
        'libselinux.so.1','libcap.so.2.66','libz.so.1.2.13']
def copy(rel):
    src = os.path.join(SRC, rel)
    dst = os.path.join(DST, rel)
    if not os.path.exists(src):
        print('MISSING ' + rel)
        return 0
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return os.path.getsize(src)
total = 0
for rel in FILES:
    total += copy(rel)
for base in ('usr/lib/aarch64-linux-gnu', 'lib/aarch64-linux-gnu'):
    for name in LIBS:
        rel = base + '/' + name
        if os.path.exists(os.path.join(DST, rel)):
            continue
        total += copy(rel)
print('total bytes copied: ' + str(total))
print('files in pack: ' + str(sum(len(f) for _b, _d, f in os.walk(DST))))