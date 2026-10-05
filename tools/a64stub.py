import os, struct, sys

FAIL_STUB = struct.pack('<III', 0x529FFFE0, 0x72BFFFE0, 0xD65F03C0)   # movz/movk w0,#0xffff ; ret  -> -1
OK_STUB   = struct.pack('<II', 0x52800000, 0xD65F03C0)              # mov w0,#0 ; ret         -> 0
FAIL_HINTS = ('init', 'open', 'create', 'load', 'setup', 'start', 'connect', 'begin', 'prepare', 'config')

def load(path):
    return bytearray(open(path, 'rb').read())

def phdrs(b):
    phoff, = struct.unpack_from('<Q', b, 0x20)
    phentsize, phnum = struct.unpack_from('<HH', b, 0x36)
    out = []
    for i in range(phnum):
        o = phoff + i * phentsize
        p_type, p_flags, p_off, p_va, _pa, p_fsz = struct.unpack_from('<IIQQQQ', b, o)
        out.append((p_type, p_flags, p_off, p_va, p_fsz))
    return out

def v2o(segs, va):
    for p_type, p_flags, p_off, p_va, p_fsz in segs:
        if p_type == 1 and p_va <= va < p_va + p_fsz:
            return p_off + (va - p_va), p_flags
    return None, 0

def shdrs(b):
    shoff, = struct.unpack_from('<Q', b, 0x28)
    shentsize, shnum = struct.unpack_from('<HH', b, 0x3a)
    out = []
    for i in range(shnum):
        o = shoff + i * shentsize
        vals = struct.unpack_from('<IIQQQQIIQQ', b, o)
        out.append(vals)
    return out

def patch(path, out_path):
    b = load(path)
    segs = phdrs(b)
    secs = shdrs(b)
    dynsym = dynstr = None
    for s in secs:
        if s[1] == 11:
            dynsym = s
        if s[1] == 3 and dynsym is None:
            dynstr = s
    if dynsym is None:
        print('  no .dynsym -> skipped'); return
    strtab = None
    link = dynsym[6]
    if 0 <= link < len(secs):
        strtab = secs[link]
    if strtab is None:
        print('  no linked strtab -> skipped'); return
    base = strtab[4]
    symoff, symsize, symentsize = dynsym[4], dynsym[5], (dynsym[9] or 24)
    nfail = nok = 0
    seen = set()
    for o in range(symoff, symoff + symsize, symentsize):
        nameoff, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', b, o)
        if nameoff == 0 or (info & 0xf) != 2 or shndx == 0 or value == 0:
            continue
        end = b.index(b'\x00', base + nameoff)
        name = bytes(b[base + nameoff:end]).decode('utf-8', 'replace')
        if name in seen or name in ('_init', '_fini') or name.startswith(('__gmon', '_ITM_', '__cxa_')):
            continue
        seen.add(name)
        off, flags = v2o(segs, value)
        if off is None or not (flags & 1):
            continue
        stub = FAIL_STUB if any(h in name.lower() for h in FAIL_HINTS) else OK_STUB
        b[off:off + len(stub)] = stub
        if stub is FAIL_STUB: nfail += 1
        else: nok += 1
    # Neutralise constructors only when asked (some firmware libs depend on them).
    keep_ctors = os.environ.get('KEEP_CTORS') == '1'
    for p_type, p_flags, p_off, p_va, p_fsz in (() if keep_ctors else segs):
        if p_type != 2:
            continue
        for o in range(p_off, p_off + p_fsz, 16):
            tag, val = struct.unpack_from('<qQ', b, o)
            if tag == 0:
                break
            if tag in (12, 25, 27):
                struct.pack_into('<qQ', b, o, tag, 0)
    open(out_path, 'wb').write(bytes(b))
    print('  ' + os.path.basename(out_path) + ': stubs=' + str(nfail + nok) + ' (fail=' + str(nfail) + ', ok=' + str(nok) + '), constructors neutralised')

for src, dst in zip(sys.argv[1::2], sys.argv[2::2]):
    print(src)
    patch(src, dst)