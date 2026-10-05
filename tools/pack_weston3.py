import os, shutil
SRC = 'vm/work/weston-root'
DST = 'vm/packs/melon-pro/weston'
def put(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    real = os.path.realpath(src) if os.path.islink(src) else src
    if os.path.exists(real):
        shutil.copy2(real, dst)
        return os.path.getsize(real)
    return 0
total = 0
root = os.path.join(SRC, 'usr/lib/aarch64-linux-gnu/weston')
for name in sorted(os.listdir(root)):
    if name.startswith('libexec_weston.so') or name == 'kiosk-shell.so':
        rel = 'usr/lib/aarch64-linux-gnu/weston/' + name
        total += put(os.path.join(root, name), os.path.join(DST, rel))
        print('added ' + rel)
print('bytes: ' + str(total))