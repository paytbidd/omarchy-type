#!/usr/bin/env python3
"""Wait for the YouTube webapp CDP, then apply Omarchy Type (including shadow roots)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply as type_apply  # noqa: E402

PORT_FILE = Path("/tmp/omarchy-type-youtube-devtools")


INJECT = r"""
(function(css){
  document.documentElement.classList.add("omarchy-type");
  let sheet = null;
  try { sheet = new CSSStyleSheet(); sheet.replaceSync(css); } catch (e) {}
  function stamp(root){
    if (!root) return;
    if (sheet && root.adoptedStyleSheets !== undefined) {
      const list = root.adoptedStyleSheets;
      for (let i = 0; i < list.length; i++) if (list[i] === sheet) return;
      try { root.adoptedStyleSheets = list.concat(sheet); } catch (e) {}
      return;
    }
    let el = root.getElementById && root.getElementById("omarchy-type");
    if (el) { el.textContent = css; return; }
    el = document.createElement("style");
    el.id = "omarchy-type";
    el.textContent = css;
    try { (root.head || root).appendChild(el); } catch (e) {}
  }
  function walk(node){
    if (!node) return;
    if (node.shadowRoot) { stamp(node.shadowRoot); walk(node.shadowRoot); }
    const kids = node.querySelectorAll ? node.querySelectorAll("*") : [];
    for (let i = 0; i < kids.length; i++) {
      if (kids[i].shadowRoot) { stamp(kids[i].shadowRoot); walk(kids[i].shadowRoot); }
    }
  }
  function apply(){
    stamp(document);
    walk(document.documentElement);
  }
  apply();
  if (!window.__omarchyTypeObs) {
    let timer = 0;
    window.__omarchyTypeObs = new MutationObserver(function(){
      clearTimeout(timer);
      timer = setTimeout(apply, 200);
    });
    window.__omarchyTypeObs.observe(document.documentElement, {childList:true, subtree:true});
  }
  return getComputedStyle(document.body).fontFamily;
})
"""


def main() -> int:
    cfg = type_apply.load_config()
    row = cfg["surfaces"].get("youtube") or {}
    if not row.get("enabled"):
        return 0
    family = type_apply.current_font()
    css = type_apply.youtube_css(family, float(row.get("scale") or 1.0))
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            import urllib.request
            with urllib.request.urlopen("http://127.0.0.1:9340/json/list", timeout=0.5) as resp:
                pages = json.loads(resp.read().decode())
            if not pages:
                time.sleep(0.25)
                continue
            PORT_FILE.write_text("9340\n", encoding="utf-8")
            # Prefer evaluating the full shadow walk.
            import socket
            from urllib.parse import urlparse
            for page in pages:
                ws = page.get("webSocketDebuggerUrl")
                if not ws:
                    continue
                parsed = urlparse(ws)
                sock = socket.create_connection((parsed.hostname, parsed.port), timeout=2)
                key = __import__("os").urandom(16).hex()[:24]
                path = parsed.path or "/"
                if parsed.query:
                    path += "?" + parsed.query
                sock.sendall(
                    f"GET {path} HTTP/1.1\r\nHost={parsed.hostname}:{parsed.port}\r\n"
                    "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                    f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode()
                )
                sock.recv(4096)
                expr = "(" + INJECT + ")(" + json.dumps(css) + ")"
                payload = json.dumps({
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {"expression": expr, "returnByValue": True, "awaitPromise": False},
                })
                type_apply._ws_send(sock, payload)
                raw = type_apply._ws_recv(sock)
                sock.close()
                print(raw[:500], file=sys.stderr)
            return 0
        except Exception as exc:
            time.sleep(0.3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
