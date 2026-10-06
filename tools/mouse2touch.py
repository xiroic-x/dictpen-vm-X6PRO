#!/usr/bin/env python3
"""Drive the pen UI with the host mouse (Windows).

The pen UI is touch-only: a click in the QEMU window arrives as a *mouse* event,
which the guest compositor consumes as a pointer and the touch UI ignores.  This
tool watches the QEMU window and re-sends every press / drag / release over QMP as
a proper touch sequence, so clicking the window drives the pen directly.

    python scripts/mouse2touch.py            # run while the VM window is open
    python scripts/mouse2touch.py --test 490 240   # send one touch and exit
","",
Panel geometry comes from the running pack (960x480); the touch point is only
forwarded when it falls inside the pen's UI strip (y=107..373 by default).
"""
import argparse, ctypes, json, socket, sys, time

QMP_PORT = 4446
BTN_TOUCH = 330


def qmp(events, timeout=5):
    s = socket.create_connection(("127.0.0.1", QMP_PORT), timeout=timeout)
    f = s.makefile("rwb")
    try:
        json.loads(f.readline().decode("utf-8", "replace"))
        def run(cmd):
            f.write((json.dumps(cmd) + "\n").encode())
            f.flush()
            while True:
                line = f.readline()
                if not line:
                    raise RuntimeError("qmp closed")
                obj = json.loads(line.decode("utf-8", "replace"))
                if "return" in obj or "error" in obj:
                    return obj
        run({"execute": "qmp_capabilities"})
        return run({"execute": "input-send-event", "arguments": {"events": events}})
    finally:
        try:
            f.close()
        except OSError:
            pass
        s.close()


def touch(x, y, down, w, h):
    ax = int(round(x * 32767 / w))
    ay = int(round(y * 32767 / h))
    ev = [
        {"type": "abs", "data": {"axis": "x", "value": ax}},
        {"type": "abs", "data": {"axis": "y", "value": ay}},
        {"type": "key", "data": {"down": down, "key": {"type": "number", "data": BTN_TOUCH}}},
    ]
    if down:
        ev.append({"type": "btn", "data": {"down": True, "button": "left"}})
    else:
        ev.append({"type": "btn", "data": {"down": False, "button": "left"}})
    qmp(ev)


def find_qemu_window():
    u = ctypes.windll.user32
    best = [None, 0]
    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        if not u.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(hwnd, buf, 256)
        if "QEMU" not in buf.value:
            return True
        r = ctypes.wintypes.RECT()
        u.GetClientRect(hwnd, ctypes.byref(r))
        area = (r.right - r.left) * (r.bottom - r.top)
        if area > best[1]:
            best[0], best[1] = hwnd, area
        return True
    u.EnumWindows(cb, 0)
    return best[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", nargs=2, type=int, metavar=("X", "Y"))
    ap.add_argument("--panel", nargs=2, type=int, default=(960, 480))
    ap.add_argument("--strip", nargs=2, type=int, default=(107, 373),
                    help="guest Y range that belongs to the pen UI")
    args = ap.parse_args()
    w, h = args.panel
    if args.test:
        x, y = args.test
        touch(x, y, True, w, h)
        time.sleep(0.08)
        touch(x, y, False, w, h)
        print("sent touch %d,%d" % (x, y))
        return 0
    try:
        import ctypes.wintypes
    except Exception as exc:
        print("mouse2touch needs a Windows host:", exc)
        return 1
    u = ctypes.windll.user32
    hwnd = find_qemu_window()
    if not hwnd:
        print("mouse2touch: no QEMU window found (start the VM first)")
        return 1
    r = ctypes.wintypes.RECT()
    u.GetClientRect(hwnd, ctypes.byref(r))
    cw, ch = r.right - r.left, r.bottom - r.top
    pt = ctypes.wintypes.POINT()
    while True:
        u.GetCursorPos(ctypes.byref(pt))
        if u.ScreenToClient(hwnd, ctypes.byref(pt)):
            inside = 0 <= pt.x < cw and 0 <= pt.y < ch
            if inside:
                gx = int(pt.x * w / cw)
                gy = int(pt.y * h / ch)
                down = bool(u.GetAsyncKeyState(0x01) & 0x8000)
                if args.strip[0] <= gy <= args.strip[1]:
                    if down and not S[0]:
                        S[0] = True
                        touch(gx, gy, True, w, h)
                    elif down and S[0]:
                        touch(gx, gy, True, w, h)   # drag: move the touch point
                    elif not down and S[0]:
                        S[0] = False
                        touch(gx, gy, False, w, h)
                elif not down and S[0]:
                    S[0] = False
                    touch(gx, gy, False, w, h)
        time.sleep(0.02)


S = [False]
if __name__ == "__main__":
    sys.exit(main())