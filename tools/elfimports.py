import re, struct, sys

def parse(path):
    b = open(path, "rb").read()
    is64 = b[4] == 2
    e = "<" if b[5] == 1 else ">"
    if is64:
        shoff, = struct.unpack_from(e + "Q", b, 0x28)
        shentsize, shnum = struct.unpack_from(e + "HH", b, 0x3a)
    else:
        shoff, = struct.unpack_from(e + "I", b, 0x20)
        shentsize, shnum = struct.unpack_from(e + "HH", b, 0x2e)
    secs = []
    for i in range(shnum):
        o = shoff + i * shentsize
        if is64:
            name, typ, flags, addr, off, size, link, info, align, entsize = struct.unpack_from(e + "IIQQQQIIQQ", b, o)
        else:
            name, typ, flags, addr, off, size, link, info, align, entsize = struct.unpack_from(e + "IIIIIIIIII", b, o)
        secs.append((name, typ, addr, off, size, link, entsize))
    shstr = b[secs[1][3]:secs[1][3] + secs[1][4]]
    def nm(x):
        return shstr[x:b.index(b"\0", x)].decode()
    named = {nm(s[0]): s for s in secs if s[0] < len(shstr)}
    return b, e, is64, named

def dump(path, pat):
    b, e, is64, named = parse(path)
    rx = re.compile(pat)
    def strtab_for(sec):
        link = sec[5]
        # reparse to get section by index
        return None
    out = []
    for key in (".dynsym", ".symtab"):
        s = named.get(key)
        if not s:
            continue
        dynstr = None
        # find linked strtab by scanning sections again
        # (approximate: use section names .dynstr / .strtab)
        dynstr = named.get(".dynstr" if key == ".dynsym" else ".strtab")
        if not dynstr:
            continue
        base = dynstr[3]
        data = b[s[3]:s[3] + s[4]]
        step = s[6] or (24 if is64 else 16)
        for o in range(0, len(data), step):
            if is64:
                nameoff, info, other, shndx, value, size = struct.unpack_from(e + "IBBHQQ", data, o)
            else:
                nameoff, value, size, info, other, shndx = struct.unpack_from(e + "IIIBBH", data, o)
            if nameoff == 0:
                continue
            name = b[base + nameoff:b.index(b"\0", base + nameoff)].decode("utf-8", "replace")
            if rx.search(name):
                kind = "UNDEF" if shndx == 0 else key
                out.append(f"{kind} {name}")
    print("==", path)
    for line in sorted(set(out)):
        print("   ", line)

for arg in sys.argv[1:]:
    path, _, pat = arg.partition("|")
    dump(path, pat or ".")
