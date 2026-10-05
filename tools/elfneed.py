import struct, sys

def vmap(b, is64, e, phoff, phentsize, phnum):
    segs = []
    for i in range(phnum):
        off = phoff + i * phentsize
        if is64:
            p_type, _f, p_off, p_va, _pa, p_fsz = struct.unpack_from(e + "IIQQQQ", b, off)
        else:
            p_type, p_off, p_va, _pa, p_fsz, _f = struct.unpack_from(e + "IIIIII", b, off)
        if p_type == 1:
            segs.append((p_va, p_off, p_fsz))
    return segs

def to_off(segs, va):
    for sva, soff, ssz in segs:
        if sva <= va < sva + ssz:
            return soff + (va - sva)
    return None

def needed(path):
    b = open(path, "rb").read()
    if b[:4] != b"\x7fELF":
        return ["(not ELF)"]
    is64 = b[4] == 2
    e = "<" if b[5] == 1 else ">"
    if is64:
        phoff, = struct.unpack_from(e + "Q", b, 0x20)
        phentsize, phnum = struct.unpack_from(e + "HH", b, 0x36)
    else:
        phoff, = struct.unpack_from(e + "I", b, 0x1c)
        phentsize, phnum = struct.unpack_from(e + "HH", b, 0x2a)
    segs = vmap(b, is64, e, phoff, phentsize, phnum)
    dyn_off = None
    for i in range(phnum):
        off = phoff + i * phentsize
        if is64:
            p_type, _f, p_off, _va, _pa, p_fsz = struct.unpack_from(e + "IIQQQQ", b, off)
        else:
            p_type, p_off, _va, _pa, p_fsz, _f = struct.unpack_from(e + "IIIIII", b, off)
        if p_type == 2:
            dyn_off, dyn_sz = p_off, p_fsz
    if dyn_off is None:
        return ["(no PT_DYNAMIC)"]
    ents = []
    step = 16 if is64 else 8
    for o in range(dyn_off, dyn_off + dyn_sz, step):
        tag, val = struct.unpack_from(e + ("qQ" if is64 else "iI"), b, o)
        ents.append((tag, val))
    strtab = next((v for t, v in ents if t == 5), None)
    out = []
    for tag, val in ents:
        if tag in (1, 15, 29):
            off = to_off(segs, strtab + val) if tag != 5 else to_off(segs, strtab)
            off = to_off(segs, strtab + val)
            if off is None:
                continue
            end = b.index(b"\0", off)
            s = b[off:end].decode("utf-8", "replace")
            out.append(("NEEDED " if tag == 1 else ("RUNPATH " if tag == 15 else "RPATH ")) + s)
    return out

for p in sys.argv[1:]:
    print("==", p)
    for line in needed(p):
        print("   ", line)
