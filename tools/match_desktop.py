import hashlib, os, zipfile
DX = 'vm/vm/desktop_x'
AMR = 'vm/work/amrpkg/etc/miniapp/resources/presetpkgs'
want = {}
for name in os.listdir(DX):
    p = os.path.join(DX, name)
    if os.path.isfile(p) and name.endswith('.bin'):
        want[name] = hashlib.md5(open(p, 'rb').read()).hexdigest()
print('desktop_x bundles: ' + str(len(want)))
scores = []
for f in sorted(os.listdir(AMR)):
    if not f.endswith('.amr'):
        continue
    try:
        z = zipfile.ZipFile(os.path.join(AMR, f))
    except Exception as exc:
        print('  ' + f + ' not a zip: ' + str(exc)); continue
    hit = 0
    for name in z.namelist():
        if name in want:
            data = z.read(name)
            if hashlib.md5(data).hexdigest() == want[name]:
                hit += 1
    scores.append((hit, f, len(z.namelist())))
scores.sort(reverse=True)
for hit, f, n in scores[:6]:
    print('  ' + f + ' entries=' + str(n) + ' identical_bundles=' + str(hit))