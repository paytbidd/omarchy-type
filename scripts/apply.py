#!/usr/bin/env python3
"""Apply Omarchy Type to enabled Chromium/Electron surfaces."""
from __future__ import annotations

import json
import math
import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

HOME = Path.home()
CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "omarchy" / "type.json"
FLAGS_PATH = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "chromium-flags.conf"
EXT_DIR = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "omarchy-type" / "chromium-ext"
FONTCONF = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "fontconfig" / "conf.d" / "51-omarchy-type-grok.conf"
GROK_DESKTOP = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "applications" / "grok-bot.desktop"
AM_PROFILE = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "omarchy-apple-music" / "chromium-profile"
PLUGIN_DIR = Path(__file__).resolve().parent.parent

SURFACES = [
    {"id": "apple-music", "label": "Apple Music", "kind": "chromium",
     "hosts": ["music.apple.com"], "defaultEnabled": True, "defaultScale": 0.92},
    {"id": "grok-bot", "label": "Grok Bot", "kind": "electron",
     "hosts": [], "defaultEnabled": True, "defaultScale": 1.0},
    {"id": "youtube", "label": "YouTube", "kind": "chromium",
     "hosts": ["youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"],
     "defaultEnabled": False, "defaultScale": 0.94},
]


def log(msg: str) -> None:
    print(f"omarchy-type: {msg}", file=sys.stderr)


def current_font() -> str:
    try:
        out = subprocess.check_output(["omarchy", "font", "current"], text=True).strip()
        if out:
            return out
    except (OSError, subprocess.CalledProcessError):
        pass
    return "sans-serif"


def default_config() -> dict:
    return {"surfaces": {s["id"]: {"enabled": s["defaultEnabled"], "scale": s["defaultScale"]} for s in SURFACES}}


def load_config() -> dict:
    data = default_config()
    if CONFIG_PATH.is_file():
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        incoming = raw.get("surfaces") if isinstance(raw, dict) else {}
        if isinstance(incoming, dict):
            for sid, row in incoming.items():
                if sid not in data["surfaces"] or not isinstance(row, dict):
                    continue
                if isinstance(row.get("enabled"), bool):
                    data["surfaces"][sid]["enabled"] = row["enabled"]
                scale = row.get("scale")
                try:
                    scale_f = float(scale)
                except (TypeError, ValueError):
                    continue
                if 0.7 <= scale_f <= 1.2:
                    data["surfaces"][sid]["scale"] = round(scale_f, 2)
    return data


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def css_percent(scale: float) -> str:
    return f"{int(round(float(scale) * 100))}%"


def apple_music_css(family: str, scale: float) -> str:
    q = json.dumps(family)
    pct = css_percent(scale)
    return (
        f"html.omarchy-type{{font-family:{q}, ui-monospace, monospace !important;font-size:{pct} !important;}}"
        "html.omarchy-type body,html.omarchy-type button,html.omarchy-type input,"
        "html.omarchy-type textarea,html.omarchy-type select{font-family:inherit !important;}"
        f"html.omarchy-type *{{font-family:{q}, ui-monospace, monospace !important;letter-spacing:-0.01em;}}"
        "html.omarchy-type .navigation-item__link:hover{"
        "background-color:color-mix(in srgb, currentColor 16%, transparent) !important;}"
    )


def grok_bot_css(family: str, scale: float) -> str:
    q = json.dumps(family)
    pct = css_percent(scale)
    return (
        ":root,html,body,#root{"
        f"--cursor-font-family:{q}, monospace !important;"
        f"--cursor-font-family-sans:{q}, monospace !important;"
        f"--cursor-font-family-mono:{q}, monospace !important;"
        f"--cursor-font-mono:{q}, monospace !important;"
        f"--vscode-font-family:{q}, monospace !important;"
        f"--monaco-monospace-font:{q}, monospace !important;"
        f"--font-family-mono:{q}, monospace !important;"
        f"--font-family-monospace:{q}, monospace !important;"
        f"font-family:{q}, monospace !important;font-size:{pct} !important;}}"
    )


def youtube_css(family: str, scale: float) -> str:
    q = json.dumps(family)
    pct = css_percent(scale)
    return (
        f"html.omarchy-type{{font-size:{pct} !important;}}"
        f"html,body,ytd-app,#content,yt-formatted-string,tp-yt-paper-item,"
        f"#text,.title,.ytp-title-link{{font-family:{q}, \"YouTube Noto\", Roboto, sans-serif !important;}}"
        f"*{{font-family:{q}, Roboto, Arial, sans-serif !important;}}"
    )


CSS_FOR = {
    "apple-music": apple_music_css,
    "grok-bot": grok_bot_css,
    "youtube": youtube_css,
}


def write_chromium_extension(cfg: dict, family: str) -> None:
    baked = {}
    matches = []
    for spec in SURFACES:
        if spec["kind"] != "chromium":
            continue
        row = cfg["surfaces"][spec["id"]]
        if not row["enabled"]:
            continue
        baked[spec["id"]] = {
            "hosts": spec["hosts"],
            "css": CSS_FOR[spec["id"]](family, row["scale"]),
            "shadow": spec["id"] == "youtube",
        }
        for host in spec["hosts"]:
            matches.append(f"https://{host}/*")
            if not host.startswith("www."):
                matches.append(f"https://www.{host}/*")
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    (EXT_DIR / "manifest.json").write_text(json.dumps({
        "manifest_version": 3,
        "name": "Omarchy Type",
        "version": "1.0.0",
        "content_scripts": [{
            "matches": sorted(set(matches)) or ["https://example.invalid/*"],
            "js": ["inject.js"],
            "run_at": "document_start",
            "all_frames": True,
        }],
    }, indent=2) + "\n", encoding="utf-8")
    (EXT_DIR / "inject.js").write_text(
        "window.__omarchyTypeSurfaces = " + json.dumps(baked) + ";\n"
        + (PLUGIN_DIR / "scripts" / "inject.js").read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def ensure_chromium_flags() -> None:
    ext = str(EXT_DIR)
    FLAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = FLAGS_PATH.read_text(encoding="utf-8").splitlines() if FLAGS_PATH.is_file() else []
    out = []
    found = False
    for line in lines:
        if line.startswith("--load-extension="):
            found = True
            parts = line.split("=", 1)[1].split(",")
            parts = [p for p in parts if p and "omarchy-type/chromium-ext" not in p]
            parts.append(ext)
            out.append("--load-extension=" + ",".join(parts))
        else:
            out.append(line)
    if not found:
        out.append(f"--load-extension={ext}")
    if out and out[-1] != "":
        out.append("")
    FLAGS_PATH.write_text("\n".join(out), encoding="utf-8")


def write_grok_fontconfig(family: str, enabled: bool) -> None:
    FONTCONF.parent.mkdir(parents=True, exist_ok=True)
    if not enabled:
        if FONTCONF.exists():
            FONTCONF.unlink()
        return
    xml_font = (family.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    families = [
        "sans-serif", "system-ui", "ui-sans-serif", "ui-monospace", "Segoe UI",
        "Inter", "SF Pro", "SF Pro Text", "-apple-system", "BlinkMacSystemFont",
        "Roboto", "Helvetica", "Arial", "Liberation Sans",
    ]
    blocks = []
    for prg in ("grok-bot", "Grok Bot"):
        for fam in families:
            xml_fam = fam.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            blocks.append(f"""  <match target="pattern">
    <test name="prgname"><string>{prg}</string></test>
    <test name="family" qual="any"><string>{xml_fam}</string></test>
    <edit name="family" mode="prepend_first" binding="strong"><string>{xml_font}</string></edit>
  </match>""")
    FONTCONF.write_text(
        '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
        f"<fontconfig>\n  <description>Omarchy Type for Grok Bot ({xml_font})</description>\n"
        + "\n".join(blocks) + "\n</fontconfig>\n",
        encoding="utf-8",
    )


def write_grok_desktop(enabled: bool) -> None:
    launch = PLUGIN_DIR / "scripts" / "launch-grok"
    if not enabled:
        if GROK_DESKTOP.is_file() and "omarchy-type" in GROK_DESKTOP.read_text(encoding="utf-8", errors="replace"):
            GROK_DESKTOP.unlink()
        return
    GROK_DESKTOP.parent.mkdir(parents=True, exist_ok=True)
    GROK_DESKTOP.write_text(
        "[Desktop Entry]\n"
        "Name=Grok Bot\n"
        "Comment=Grok Bot desktop agent\n"
        f"Exec={launch} %U\n"
        f"TryExec={launch}\n"
        "Icon=grok-bot\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=Development;\n"
        "MimeType=x-scheme-handler/grokbot;x-scheme-handler/sand;\n"
        "StartupWMClass=Grok Bot\n"
        "StartupNotify=true\n"
        "Keywords=Grok;AI;Agent;\n",
        encoding="utf-8",
    )
    GROK_DESKTOP.chmod(0o755)


def _ws_send(sock: socket.socket, payload: str) -> None:
    data = payload.encode()
    header = bytearray([0x81])
    n = len(data)
    mask = os.urandom(4)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(n.to_bytes(2, "big"))
    else:
        header.append(0x80 | 127)
        header.extend(n.to_bytes(8, "big"))
    header.extend(mask)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    sock.sendall(header + masked)


def _ws_recv(sock: socket.socket) -> str:
    hdr = sock.recv(2)
    if len(hdr) < 2:
        raise ConnectionError("short websocket header")
    n = hdr[1] & 0x7F
    if n == 126:
        n = int.from_bytes(sock.recv(2), "big")
    elif n == 127:
        n = int.from_bytes(sock.recv(8), "big")
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("websocket closed")
        data += chunk
    return data.decode("utf-8", "replace")


def inject_cdp(devtools_port_file: Path, css: str, timeout: float = 2.0) -> bool:
    if not devtools_port_file.is_file():
        return False
    try:
        port = int(devtools_port_file.read_text(encoding="utf-8").splitlines()[0].strip())
    except (ValueError, OSError):
        return False
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=timeout) as resp:
            pages = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False
    ok = False
    script = (
        "(function(){const css=" + json.dumps(css) + ";"
        "let s=document.getElementById('omarchy-type');"
        "if(!s){s=document.createElement('style');s.id='omarchy-type';"
        "(document.head||document.documentElement).appendChild(s);}"
        "s.textContent=css;document.documentElement.classList.add('omarchy-type');})();"
    )
    for page in pages:
        ws_url = page.get("webSocketDebuggerUrl")
        if not ws_url:
            continue
        parsed = urlparse(ws_url)
        try:
            sock = socket.create_connection((parsed.hostname, parsed.port), timeout=timeout)
            key = os.urandom(16).hex()[:24]
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            req = (
                f"GET {path} HTTP/1.1\r\nHost={parsed.hostname}:{parsed.port}\r\n"
                "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
            )
            sock.sendall(req.encode())
            sock.recv(4096)
            payload = json.dumps({"id": 1, "method": "Runtime.evaluate",
                                  "params": {"expression": script, "returnByValue": True}})
            _ws_send(sock, payload)
            _ws_recv(sock)
            sock.close()
            ok = True
        except OSError:
            continue
    return ok


def apply() -> int:
    cfg = load_config()
    family = current_font()
    write_chromium_extension(cfg, family)
    ensure_chromium_flags()
    grok = cfg["surfaces"]["grok-bot"]
    write_grok_fontconfig(family, grok["enabled"])
    write_grok_desktop(grok["enabled"])
    if grok["enabled"]:
        inject_cdp(Path("/tmp/grok-bot-devtools-port"), grok_bot_css(family, grok["scale"]))
        # launch-grok writes this; also try common Electron debug port file
        inject_cdp(Path.home() / ".config/Grok Bot/DevToolsActivePort", grok_bot_css(family, grok["scale"]))
    am = cfg["surfaces"]["apple-music"]
    if am["enabled"]:
        inject_cdp(AM_PROFILE / "DevToolsActivePort", apple_music_css(family, am["scale"]))
    save_config(cfg)
    print(json.dumps({"ok": True, "font": family, "config": cfg}, indent=2))
    return 0


def set_surface(sid: str, enabled: bool | None = None, scale: float | None = None) -> int:
    if sid not in {s["id"] for s in SURFACES}:
        log(f"unknown surface {sid}")
        return 1
    cfg = load_config()
    if enabled is not None:
        cfg["surfaces"][sid]["enabled"] = enabled
    if scale is not None:
        cfg["surfaces"][sid]["scale"] = round(max(0.7, min(1.2, float(scale))), 2)
    save_config(cfg)
    return apply()


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "apply"
    if cmd in ("apply", "refresh"):
        return apply()
    if cmd == "status":
        print(json.dumps({"font": current_font(), "config": load_config()}, indent=2))
        return 0
    if cmd == "enable" and len(argv) >= 3:
        return set_surface(argv[2], enabled=True)
    if cmd == "disable" and len(argv) >= 3:
        return set_surface(argv[2], enabled=False)
    if cmd == "scale" and len(argv) >= 4:
        return set_surface(argv[2], scale=float(argv[3]))
    if cmd == "toggle" and len(argv) >= 3:
        cfg = load_config()
        sid = argv[2]
        if sid not in cfg["surfaces"]:
            log(f"unknown surface {sid}")
            return 1
        return set_surface(sid, enabled=not cfg["surfaces"][sid]["enabled"])
    print("Usage: apply.py apply|status|enable <id>|disable <id>|toggle <id>|scale <id> <0.7-1.2>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
