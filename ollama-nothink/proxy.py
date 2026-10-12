#!/usr/bin/env python3
"""Proxy local do Ollama que forca think=false nas chamadas /api/chat e /api/generate sem o campo "think".
Existe porque o Cline (extensao 4.0.10) nao envia "think" e o Qwen3.8 raciocina por padrao (Cap. 8.9, ADR-013).
Escuta SO em 127.0.0.1:11435 e repassa tudo ao Ollama em 127.0.0.1:11434 (streaming preservado)."""
import http.client, json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = ("127.0.0.1", 11434)
LISTEN = ("127.0.0.1", 11435)


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _proxy(self):
        n = int(self.headers.get("Content-Length") or 0)
        corpo = self.rfile.read(n) if n else b""
        if self.command == "POST" and self.path in ("/api/chat", "/api/generate") and corpo:
            try:
                d = json.loads(corpo)
                d.setdefault("think", False)
                corpo = json.dumps(d).encode()
            except ValueError:
                pass
        c = http.client.HTTPConnection(*UPSTREAM, timeout=900)
        c.request(self.command, self.path, corpo, {"Content-Type": self.headers.get("Content-Type", "application/json")})
        r = c.getresponse()
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                self.send_header(k, v)
        self.send_header("Transfer-Encoding", "chunked"); self.end_headers()
        while True:
            b = r.read1(65536)
            if not b:
                break
            self.wfile.write(b"%x\r\n%s\r\n" % (len(b), b)); self.wfile.flush()
        self.wfile.write(b"0\r\n\r\n"); self.wfile.flush(); c.close()

    do_GET = do_POST = do_HEAD = do_DELETE = _proxy

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(LISTEN, H).serve_forever()
