import json, socket, sys, time
QMP = 4446
BTN_TOUCH = 330
def send(batches, timeout=15):
    s = socket.create_connection(('127.0.0.1', QMP), timeout=timeout)
    f = s.makefile('rwb')
    try:
        json.loads(f.readline().decode('utf-8', 'replace'))
        def run(cmd):
            f.write((json.dumps(cmd) + '\n').encode()); f.flush()
            while True:
                line = f.readline()
                if not line:
                    raise RuntimeError('qmp closed')
                obj = json.loads(line.decode('utf-8', 'replace'))
                if 'return' in obj or 'error' in obj:
                    return obj
        run({'execute': 'qmp_capabilities'})
        return [run(c) for c in batches]
    finally:
        try: f.close()
        except OSError: pass
        s.close()

x1, y1, x2, y2 = (int(v) for v in sys.argv[1:5])
steps = int(sys.argv[5]) if len(sys.argv) > 5 else 12
W, H = 960, 480
ax1, ay1 = int(round(x1 * 32767 / W)), int(round(y1 * 32767 / H))
ax2, ay2 = int(round(x2 * 32767 / W)), int(round(y2 * 32767 / H))
def ev(ax, ay, down):
    return {'execute': 'input-send-event', 'arguments': {'events': [
        {'type': 'abs', 'data': {'axis': 'x', 'value': ax}},
        {'type': 'abs', 'data': {'axis': 'y', 'value': ay}},
        {'type': 'btn', 'data': {'down': down, 'button': 'left'}},
        {'type': 'key', 'data': {'down': down, 'key': {'type': 'number', 'data': BTN_TOUCH}}},
    ]}}
send([ev(ax1, ay1, True)])
for i in range(1, steps + 1):
    ax = int(round(ax1 + (ax2 - ax1) * i / steps))
    ay = int(round(ay1 + (ay2 - ay1) * i / steps))
    send([{'execute': 'input-send-event', 'arguments': {'events': [
        {'type': 'abs', 'data': {'axis': 'x', 'value': ax}},
        {'type': 'abs', 'data': {'axis': 'y', 'value': ay}}]}}])
    time.sleep(0.04)
send([ev(ax2, ay2, False)])
print('swipe (%d,%d)->(%d,%d) steps=%d' % (x1, y1, x2, y2, steps))