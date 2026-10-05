import struct, sys
def dyn(path):
    b = open(path, 'rb').read()
    phoff, = struct.unpack_from('<Q', b, 0x20)
    phentsize, phnum = struct.unpack_from('<HH', b, 0x36)
    out = []
    for i in range(phnum):
        o = phoff + i * phentsize
        p_type, _f, p_off, _va, _pa, p_fsz = struct.unpack_from('<IIQQQQ', b, o)
        if p_type != 2:
            continue
        for oo in range(p_off, p_off + p_fsz, 16):
            tag, val = struct.unpack_from('<qQ', b, oo)
            if tag == 0: break
            if tag in (12, 25, 27): out.append((tag, val))
    return out
for p in sys.argv[1:]:
    print(p, dyn(p))