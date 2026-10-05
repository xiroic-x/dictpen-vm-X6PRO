from pathlib import Path

base = Path("vm/work/firmware-a-inspect")
targets = [
    "usr/lib/libweston-11.so.0.0.1",
    "usr/lib/libweston-11/drm-backend.so",
    "usr/lib/libweston-11/gl-renderer.so",
    "usr/lib/libgbm.so.1",
    "usr/lib/libmali_hook.so.1",
    "usr/lib/libmali.so.1.9.0",
    "usr/bin/weston",
]
probes = [b"Failed to create gbm device", b"is not compatible with dumb buffers",
          b"gbm_bo_create", b"gbm_create_device", b"gbm_surface_create",
          b"gbm_bo_map", b"kms_swrast", b"MESA", b"/dev/mali", b"mali"]
for rel in targets:
    p = base / rel
    if not p.exists():
        print("MISSING", rel)
        continue
    b = p.read_bytes()
    hits = [s.decode() for s in probes if s in b]
    print(f"{rel:52} {len(b):>9} {hits}")
