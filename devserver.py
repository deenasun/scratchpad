#!/usr/bin/env python3
"""Tiny zero-dependency live-reload static server.

Serves this directory over HTTP and auto-reloads the open browser tab
whenever any .html/.css/.js file in the folder changes on disk. The
reload snippet is injected into HTML responses on the fly, so the
source files are never modified.

Usage:  python3 devserver.py [port]
Then open the printed URL and just keep saving — the tab refreshes.
"""
import http.server
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
WATCH_EXT = (".html", ".css", ".js")
START_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

# Injected before </body>. Restores the current slide across reloads,
# then polls the server for file changes every 500ms.
RELOAD_JS = b"""
<script>
(function () {
  try {
    var saved = sessionStorage.getItem('__lr_slide');
    if (saved !== null && typeof show === 'function') show(parseInt(saved, 10));
  } catch (e) {}
  var last = null;
  setInterval(function () {
    fetch('/__livereload__', { cache: 'no-store' })
      .then(function (r) { return r.text(); })
      .then(function (v) {
        if (last === null) { last = v; return; }
        if (v !== last) {
          try { sessionStorage.setItem('__lr_slide', String(typeof index === 'number' ? index : 0)); } catch (e) {}
          location.reload();
        }
      })
      .catch(function () {});
  }, 500);
})();
</script>
"""


def latest_mtime():
    newest = 0.0
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".")]  # skip .git etc.
        for f in files:
            if f.endswith(WATCH_EXT):
                try:
                    m = os.path.getmtime(os.path.join(dirpath, f))
                    if m > newest:
                        newest = m
                except OSError:
                    pass
    return newest


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, *a):
        pass  # keep the console quiet

    def _send(self, body, content_type):
        try:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # client navigated away mid-response; harmless

    def do_GET(self):
        if self.path.startswith("/__livereload__"):
            self._send(str(latest_mtime()).encode(), "text/plain")
            return

        path = self.translate_path(self.path)
        if path.endswith(".html") and os.path.isfile(path):
            with open(path, "rb") as fh:
                html = fh.read()
            if b"</body>" in html:
                html = html.replace(b"</body>", RELOAD_JS + b"</body>", 1)
            else:
                html += RELOAD_JS
            self._send(html, "text/html; charset=utf-8")
            return

        return super().do_GET()


def main():
    for port in range(START_PORT, START_PORT + 20):
        try:
            httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
        except OSError:
            continue
        url = "http://localhost:%d/ai_tech_review.html" % port
        print("Live-reload server running.")
        print("  Open:  " + url)
        print("  Watching %s for .html/.css/.js changes." % ROOT)
        print("  Save the file to auto-reload. Ctrl-C to stop.")
        sys.stdout.flush()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
        return
    raise SystemExit("No free port in range %d-%d" % (START_PORT, START_PORT + 19))


if __name__ == "__main__":
    main()
