#!/usr/bin/env python3
"""Serve the final Antarctica video: inline player + direct download (with Range support)."""
import http.server
import socketserver
import os
import re
from urllib.parse import unquote

ROOT = "/home/user/antactica"
PORT = 8080

INDEX = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ANTARCTICA FROZE FIRST — Final Video</title>
<style>
  :root { color-scheme: dark; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: radial-gradient(1200px 800px at 50% -10%, #0b1b3d 0%, #050a18 55%, #02040a 100%);
    color: #e8eefc;
    font-family: -apple-system, "Segoe UI", Roboto, Inter, sans-serif;
    min-height: 100vh; display: flex; flex-direction: column; align-items: center;
    padding: 40px 16px 64px;
  }
  .badge {
    letter-spacing: 3px; font-size: 12px; text-transform: uppercase;
    color: #67e8f9; border: 1px solid rgba(103,232,249,.35); border-radius: 999px;
    padding: 7px 16px; margin-bottom: 18px;
  }
  h1 {
    font-size: clamp(26px, 5vw, 44px); font-weight: 800; text-align: center;
    letter-spacing: 1px; max-width: 900px;
  }
  h1 span { color: #67e8f9; }
  .meta { color: #9db2d4; margin: 14px 0 26px; text-align: center; font-size: 14px; line-height: 1.7; }
  .wrap { display: flex; gap: 32px; flex-wrap: wrap; align-items: flex-start; justify-content: center; width: 100%; }
  .player {
    position: relative; width: min(46vh, 430px); aspect-ratio: 9/16;
    border-radius: 20px; overflow: hidden; background: #000;
    box-shadow: 0 0 0 1px rgba(120,160,255,.14), 0 30px 80px -20px rgba(20,90,200,.45);
  }
  .player video { width: 100%; height: 100%; object-fit: cover; display: block; }
  .side { width: min(480px, 94vw); display: flex; flex-direction: column; gap: 14px; }
  .card {
    background: rgba(13,22,44,.72); border: 1px solid rgba(120,160,255,.14);
    border-radius: 16px; padding: 18px 20px;
  }
  .card h2 { font-size: 15px; color: #67e8f9; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; }
  .row { display: flex; justify-content: space-between; font-size: 13.5px; padding: 4px 0; color: #c3d2ec; }
  .row b { color: #fff; font-weight: 600; }
  .btn {
    display: block; text-align: center; text-decoration: none; font-weight: 700;
    font-size: 16px; letter-spacing: .5px; border-radius: 14px; padding: 16px 20px;
    transition: transform .12s ease, filter .12s ease;
  }
  .btn:hover { transform: translateY(-1px); filter: brightness(1.1); }
  .btn.dl { background: linear-gradient(135deg, #67e8f9, #2b8ee8); color: #04121f; }
  .btn.q { background: rgba(255,255,255,.06); color: #dfe9fb; border: 1px solid rgba(160,190,255,.25); }
  .thumbs { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
  .thumbs img { width: 74px; height: 131px; object-fit: cover; border-radius: 8px; border: 1px solid rgba(160,190,255,.2); }
  .hint { color: #7f93b8; font-size: 12px; text-align: center; margin-top: 26px; }
  a { color: #67e8f9; }
</style>
</head>
<body>
  <div class="badge">Universe Impact · Production Reel</div>
  <h1>ANTARCTICA <span>FROZE FIRST</span></h1>
  <div class="meta">
    1:45 · 1080×1920 · 30 fps · H.264 + AAC · 43.5 MB<br>
    Karaoke captions · procedural animations · real NASA imagery · cinematic mix (−14 LUFS)
  </div>
  <div class="wrap">
    <div class="player">
      <video id="v" controls playsinline preload="metadata" poster="/thumbnail_ant.jpg">
        <source src="/antarctica_froze_first_9x16.mp4" type="video/mp4">
      </video>
    </div>
    <div class="side">
      <div class="card">
        <h2>Final file</h2>
        <div class="row"><span>Filename</span><b>antarctica_froze_first_9x16.mp4</b></div>
        <div class="row"><span>Duration</span><b>1:45.17</b></div>
        <div class="row"><span>Size</span><b>43.5 MB</b></div>
        <div class="row"><span>Video</span><b>H.264 High · 3.1 Mbps</b></div>
        <div class="row"><span>Audio</span><b>AAC-LC 190 kbps stereo</b></div>
        <div class="row"><span>Loudness</span><b>−13.0 LUFS / −1.5 dBTP</b></div>
        <div class="row"><span>SHA-256</span><b style="font-size:10.5px">ac2a7aa5…477b00</b></div>
      </div>
      <a class="btn dl" href="/antarctica_froze_first_9x16.mp4" download>⬇ Download MP4 (43.5 MB)</a>
      <a class="btn q" href="/thumbnail_ant.jpg" download>Download thumbnail</a>
      <div class="card">
        <h2>Scene QA frames</h2>
        <div class="thumbs">
          <img src="/work/qa_s1.jpg" alt="s1"><img src="/work/qa_s2.jpg" alt="s2">
          <img src="/work/qa_s3.jpg" alt="s3"><img src="/work/qa_s4.jpg" alt="s4">
          <img src="/work/qa_s5.jpg" alt="s5"><img src="/work/qa_s6.jpg" alt="s6">
          <img src="/work/qa_s7.jpg" alt="s7"><img src="/work/qa_s8.jpg" alt="s8">
        </div>
      </div>
    </div>
  </div>
  <div class="hint">Rebuild anytime: <code>gen_anims_ant.py → prep_assets_ant.py → build_ant.py</code> (see README.md)</div>
</body>
</html>
"""

CTYPES = {".mp4": "video/mp4", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
          ".png": "image/png", ".html": "text/html; charset=utf-8", ".md": "text/plain"}

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = unquote(self.path.split("?")[0])
        if path in ("/", "/index.html"):
            body = INDEX.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        fp = os.path.realpath(os.path.join(ROOT, path.lstrip("/")))
        if not fp.startswith(ROOT) or not os.path.isfile(fp):
            self.send_error(404)
            return
        size = os.path.getsize(fp)
        ctype = CTYPES.get(os.path.splitext(fp)[1].lower(), "application/octet-stream")
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                start = int(m.group(1) or 0)
                end = min(int(m.group(2) or size - 1), size - 1)
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with open(fp, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(65536, left))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)

    def log_message(self, *args):
        pass

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    with Server(("0.0.0.0", PORT), Handler) as httpd:
        print(f"serving {ROOT} on port {PORT}")
        httpd.serve_forever()
