#!/usr/bin/env python3
"""Baixador paralelo e retomavel (blocos de 16 MiB, N conexoes) com verificacao de SHA-256.
Uso: pdl.py URL DESTINO TAMANHO SHA256 [N]"""
import sys, os, json, hashlib, threading, time, urllib.request, queue

url, dest, size, sha = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
N = int(sys.argv[5]) if len(sys.argv) > 5 else 8
BLK = 16 << 20
part = dest + ".part"
st = dest + ".state"
nb = (size + BLK - 1) // BLK
done = set(json.load(open(st))) if os.path.exists(st) and os.path.exists(part) else set()
if not os.path.exists(part) or os.path.getsize(part) != size:
    with open(part, "wb") as f:
        f.truncate(size)
    done = set()
q = queue.Queue()
for i in range(nb):
    if i not in done:
        q.put(i)
lock = threading.Lock()
t0 = time.time()
got = [len(done) * BLK]
base = got[0]


def resolver():
    r = urllib.request.Request(url, headers={"Range": "bytes=0-0", "User-Agent": "pases-pdl"})
    with urllib.request.urlopen(r, timeout=60) as x:
        return x.geturl()


cdn = [resolver()]


def worker():
    fd = os.open(part, os.O_WRONLY)
    while True:
        try:
            i = q.get_nowait()
        except queue.Empty:
            break
        a = i * BLK
        b = min(size, a + BLK) - 1
        ok = False
        for tent in range(8):
            try:
                r = urllib.request.Request(cdn[0], headers={"Range": f"bytes={a}-{b}", "User-Agent": "pases-pdl"})
                with urllib.request.urlopen(r, timeout=120) as x:
                    buf = x.read()
                if len(buf) != b - a + 1:
                    raise IOError("tamanho do bloco")
                os.pwrite(fd, buf, a)
                ok = True
                break
            except Exception:
                time.sleep(2 + tent)
                try:
                    cdn[0] = resolver()
                except Exception:
                    pass
        if not ok:
            q.put(i)
            time.sleep(5)
            continue
        with lock:
            done.add(i)
            got[0] += len(buf)
            if len(done) % 8 == 0:
                json.dump(sorted(done), open(st, "w"))
    os.close(fd)


th = [threading.Thread(target=worker) for _ in range(N)]
for t in th:
    t.start()
while any(t.is_alive() for t in th):
    time.sleep(10)
    print("%.1f%%  %.1f MB/s" % (100 * got[0] / size, (got[0] - base) / max(1, time.time() - t0) / 1e6), flush=True)
for t in th:
    t.join()
if len(done) != nb:
    print("INCOMPLETO", len(done), nb)
    sys.exit(2)
h = hashlib.sha256()
with open(part, "rb") as f:
    for b in iter(lambda: f.read(1 << 24), b""):
        h.update(b)
if h.hexdigest() != sha:
    print("SHA DIFERENTE", h.hexdigest())
    sys.exit(3)
os.replace(part, dest)
if os.path.exists(st):
    os.remove(st)
print("OK", dest, size)
