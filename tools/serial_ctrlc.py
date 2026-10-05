import socket, time, sys
s = socket.create_connection(('127.0.0.1', 4444), timeout=10)
s.sendall(b'\x03')
time.sleep(1.5)
s.sendall(b'\n')
time.sleep(1.5)
s.setblocking(False)
data = b''
try:
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        data += chunk
except BlockingIOError:
    pass
s.close()
text = data.decode('utf-8', 'replace')
print('BYTES', len(data))
print(text[-1200:])