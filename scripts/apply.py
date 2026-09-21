#!/usr/bin/env python3
"""Apply Omarchy Type to enabled apps."""
from __future__ import annotations

import json
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

HOME = Path.home()
CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "omarchy" / "type.json"
FLAGS_PATH = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "chromium-flags.conf"
EXT_DIR = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "omarchy-type" / "chromium-ext"
FONTCONF = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "fontconfig" / "conf.d" / "51-omarchy-type.conf"
OLD_GROK_FONTCONF = FONTCONF.with_name("51-omarchy-type-grok.conf")
GROK_DESKTOP = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "applications" / "grok-bot.desktop"
YT_DESKTOP = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "applications" / "YouTube.desktop"
CHROMIUM_DESKTOP = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "applications" / "chromium.desktop"
CHROMIUM_PREFS = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "chromium" / "Default" / "Preferences"
AM_PROFILE = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "omarchy-apple-music" / "chromium-profile"
PLUGIN_DIR = Path(__file__).resolve().parent.parent
DESKTOP_DIRS = [
    Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "applications",
    Path("/usr/share/applications"),
]
TYPE_DESKTOP_MARK = "# omarchy-type"

RECIPES = {
    "apple-music": {
        "id": "apple-music", "label": "Apple Music", "desktop": "omarchy-apple-music.desktop",
        "kind": "chromium", "hosts": ["music.apple.com"], "defaultEnabled": True, "defaultScale": 0.92,
    },
    "grok-bot": {
        "id": "grok-bot", "label": "Grok Bot", "desktop": "grok-bot.desktop",
        "kind": "electron", "hosts": [], "defaultEnabled": True, "defaultScale": 1.0,
    },
    "youtube": {
        "id": "youtube", "label": "YouTube", "desktop": "YouTube.desktop",
        "kind": "chromium",
        "hosts": ["youtube.com", "youtu.be", "m.youtube.com"],
        "defaultEnabled": False, "defaultScale": 0.94,
    },
}
DEFAULT_IDS = ["apple-music", "grok-bot", "youtube"]
KINDS = {"chromium", "electron", "other"}
BROWSER_DESKTOPS = {
    "chromium.desktop", "google-chrome.desktop", "google-chrome-stable.desktop",
    "brave-origin.desktop", "brave.desktop",
}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
COMPATIBLE_KINDS = {"chromium", "electron"}


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


def clamp_scale(value) -> float:
    try:
        scale = float(value)
    except (TypeError, ValueError):
        return 1.0
    if 0.7 <= scale <= 1.2:
        return round(scale, 2)
    return 1.0


def recipe_app(rid: str, enabled: bool | None = None, scale: float | None = None) -> dict:
    r = RECIPES[rid]
    return {
        "id": r["id"],
        "label": r["label"],
        "desktop": r["desktop"],
        "kind": r["kind"],
        "hosts": list(r.get("hosts") or []),
        "enabled": r["defaultEnabled"] if enabled is None else enabled,
        "scale": r["defaultScale"] if scale is None else clamp_scale(scale),
    }


def default_apps() -> list[dict]:
    return [recipe_app(rid) for rid in DEFAULT_IDS]


def sanitize_app(row: dict) -> dict | None:
    if not isinstance(row, dict):
        return None
    app_id = str(row.get("id") or "").strip()
    if not app_id:
        return None
    recipe = RECIPES.get(app_id)
    kind = str(row.get("kind") or (recipe["kind"] if recipe else "chromium"))
    if kind == "chromium-ui":
        return None
    if kind not in KINDS:
        kind = recipe["kind"] if recipe else "other"
    hosts = []
    raw_hosts = row.get("hosts")
    if not raw_hosts and recipe:
        raw_hosts = recipe["hosts"]
    if isinstance(raw_hosts, list):
        for host in raw_hosts:
            h = str(host or "").strip()
            if h.startswith("www."):
                h = h[4:]
            if h and h not in hosts:
                hosts.append(h)
    scale = row.get("scale")
    if scale is None and recipe:
        scale = recipe["defaultScale"]
    return {
        "id": app_id,
        "label": str(row.get("label") or (recipe["label"] if recipe else app_id)),
        "desktop": str(row.get("desktop") or (recipe["desktop"] if recipe else f"{app_id}.desktop")),
        "kind": kind,
        "hosts": hosts,
        "enabled": row.get("enabled") is not False,
        "scale": clamp_scale(scale),
    }


def migrate_surfaces(surfaces: dict) -> list[dict]:
    apps = default_apps()
    by_id = {a["id"]: a for a in apps}
    if not isinstance(surfaces, dict):
        return apps
    for sid, row in surfaces.items():
        if sid not in by_id or not isinstance(row, dict):
            continue
        if isinstance(row.get("enabled"), bool):
            by_id[sid]["enabled"] = row["enabled"]
        if "scale" in row:
            by_id[sid]["scale"] = clamp_scale(row.get("scale"))
    return apps


def default_config() -> dict:
    return {"enabled": True, "apps": default_apps()}


def load_config() -> dict:
    raw: dict = {}
    if CONFIG_PATH.is_file():
        try:
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                raw = loaded
        except Exception:
            raw = {}
    enabled = raw.get("enabled", True)
    if not isinstance(enabled, bool):
        enabled = True
    if isinstance(raw.get("apps"), list):
        apps = []
        seen = set()
        for row in raw["apps"]:
            app = sanitize_app(row) if isinstance(row, dict) else None
            if not app or app["id"] in seen:
                continue
            seen.add(app["id"])
            apps.append(app)
    else:
        apps = migrate_surfaces(raw.get("surfaces") if isinstance(raw.get("surfaces"), dict) else {})
    return {"enabled": enabled, "apps": apps}


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "enabled": bool(cfg.get("enabled", True)),
        "apps": [sanitize_app(a) for a in cfg.get("apps", []) if sanitize_app(a)],
    }
    CONFIG_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def css_percent(scale: float) -> str:
    return f"{int(round(float(clamp_scale(scale)) * 100))}%"


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
    z = f"{clamp_scale(scale):.2f}"
    guide = max(260, int(round(280 * clamp_scale(scale))))
    masthead = max(52, int(round(56 * max(clamp_scale(scale), 0.95))))
    return (
        f"html.omarchy-type,html.omarchy-type body,html.omarchy-type ytd-app,"
        f"html.omarchy-type yt-formatted-string,html.omarchy-type tp-yt-paper-item,"
        f"html.omarchy-type #content,html.omarchy-type *{{font-family:{q}, Roboto, Arial, sans-serif !important;}}"
        f"html.omarchy-type ytd-app{{--ytd-guide-width:{guide}px !important;"
        f"--app-drawer-width:{guide}px !important;--ytd-masthead-height:{masthead}px !important;}}"
        f"html.omarchy-type ytd-masthead,html.omarchy-type #masthead-container,html.omarchy-type #header{{"
        f"min-height:{masthead}px !important;height:{masthead}px !important;"
        f"font-size:14px !important;zoom:1 !important;}}"
        f"html.omarchy-type ytd-guide-renderer,html.omarchy-type #guide-content,"
        f"html.omarchy-type #guide-inner-content{{width:{guide}px !important;min-width:{guide}px !important;}}"
        f"html.omarchy-type #guide yt-formatted-string,html.omarchy-type ytd-guide-entry-renderer{{"
        f"font-size:13px !important;}}"
        f"html.omarchy-type ytd-page-manager,html.omarchy-type #page-manager,"
        f"html.omarchy-type ytd-browse,html.omarchy-type ytd-watch-flexy{{zoom:{z} !important;}}"
    )


def generic_css(family: str, scale: float) -> str:
    q = json.dumps(family)
    pct = css_percent(scale)
    return (
        f"html.omarchy-type{{font-family:{q}, ui-sans-serif, sans-serif !important;font-size:{pct} !important;}}"
        "html.omarchy-type body,html.omarchy-type button,html.omarchy-type input,"
        "html.omarchy-type textarea,html.omarchy-type select,html.omarchy-type *"
        f"{{font-family:{q}, ui-sans-serif, sans-serif !important;}}"
    )


def css_for_app(app: dict, family: str) -> str:
    scale = app.get("scale", 1)
    if app["id"] == "apple-music":
        return apple_music_css(family, scale)
    if app["id"] == "grok-bot":
        return grok_bot_css(family, scale)
    if app["id"] == "youtube":
        return youtube_css(family, scale)
    if app["kind"] == "chromium":
        return generic_css(family, scale)
    if app["kind"] == "electron":
        return grok_bot_css(family, scale)
    return ""


def find_app(cfg: dict, app_id: str) -> dict | None:
    for app in cfg["apps"]:
        if app["id"] == app_id:
            return app
    return None


def app_active(cfg: dict, app: dict) -> bool:
    return bool(cfg.get("enabled", True) and app.get("enabled", True))


def write_chromium_extension(cfg: dict, family: str) -> None:
    baked = {}
    matches = []
    if cfg.get("enabled", True):
        for app in cfg["apps"]:
            if app["kind"] != "chromium" or not app["enabled"]:
                continue
            css = css_for_app(app, family)
            if not css or not app["hosts"]:
                continue
            baked[app["id"]] = {
                "hosts": app["hosts"],
                "css": css,
                "shadow": True,
            }
            for host in app["hosts"]:
                matches.append(f"https://{host}/*")
                if not host.startswith("www."):
                    matches.append(f"https://www.{host}/*")
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    (EXT_DIR / "sw.js").write_text("self.addEventListener('install', () => {});\n", encoding="utf-8")
    match_list = sorted(set(matches)) or ["https://example.invalid/*"]
    (EXT_DIR / "manifest.json").write_text(json.dumps({
        "manifest_version": 3,
        "name": "Omarchy Type",
        "version": "1.1.0",
        "background": {"service_worker": "sw.js"},
        "host_permissions": match_list,
        "content_scripts": [{
            "matches": match_list,
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


def _flag_line_key(line: str) -> str:
    if line.startswith("--") and "=" in line:
        return line.split("=", 1)[0]
    return line.strip()


def ensure_chromium_flags(cfg: dict, family: str) -> None:
    FLAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = FLAGS_PATH.read_text(encoding="utf-8").splitlines() if FLAGS_PATH.is_file() else []
    out: list[str] = []
    found_ext = False
    want_ext = False
    if cfg.get("enabled", True):
        want_ext = any(a["kind"] == "chromium" and a["enabled"] and a["hosts"] for a in cfg["apps"])
    ext = str(EXT_DIR)
    for line in lines:
        key = _flag_line_key(line)
        if line.startswith("--load-extension="):
            found_ext = True
            parts = [p for p in line.split("=", 1)[1].split(",") if p and "omarchy-type/chromium-ext" not in p]
            if want_ext:
                parts.append(ext)
            if parts:
                out.append("--load-extension=" + ",".join(parts))
            continue
        if key in ("--system-font-family", "--force-device-scale-factor"):
            continue
        out.append(line)
    if want_ext and not found_ext:
        out.append(f"--load-extension={ext}")
    while out and out[-1] == "":
        out.pop()
    out.append("")
    FLAGS_PATH.write_text("\n".join(out), encoding="utf-8")


def xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_fontconfig(cfg: dict, family: str) -> None:
    FONTCONF.parent.mkdir(parents=True, exist_ok=True)
    if OLD_GROK_FONTCONF.exists():
        OLD_GROK_FONTCONF.unlink()
    names: list[str] = []
    if cfg.get("enabled", True):
        for app in cfg["apps"]:
            if not app["enabled"]:
                continue
            if app["kind"] not in ("electron", "other"):
                continue
            names.extend(_prg_names_for(app))
    names = list(dict.fromkeys(n for n in names if n))
    if not names:
        if FONTCONF.exists():
            FONTCONF.unlink()
        return
    xml_font = xml_escape(family)
    families = [
        "sans-serif", "system-ui", "ui-sans-serif", "ui-monospace", "Segoe UI",
        "Inter", "SF Pro", "SF Pro Text", "-apple-system", "BlinkMacSystemFont",
        "Roboto", "Helvetica", "Arial", "Liberation Sans",
    ]
    blocks = []
    for prg in names:
        xml_prg = xml_escape(prg)
        for fam in families:
            xml_fam = xml_escape(fam)
            blocks.append(
                "  <match target=\"pattern\">\n"
                f"    <test name=\"prgname\"><string>{xml_prg}</string></test>\n"
                f"    <test name=\"family\" qual=\"any\"><string>{xml_fam}</string></test>\n"
                f"    <edit name=\"family\" mode=\"prepend_first\" binding=\"strong\"><string>{xml_font}</string></edit>\n"
                "  </match>"
            )
    FONTCONF.write_text(
        '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
        f"<fontconfig>\n  <description>Omarchy Type ({xml_font})</description>\n"
        + "\n".join(blocks) + "\n</fontconfig>\n",
        encoding="utf-8",
    )


def _prg_names_for(app: dict) -> list[str]:
    if app["id"] == "grok-bot":
        return ["grok-bot", "Grok Bot"]
    desktop = find_desktop_path(app.get("desktop") or "")
    parsed = parse_desktop(desktop) if desktop else {}
    exec_line = parsed.get("Exec") or ""
    try:
        token = shlex.split(exec_line, posix=True)[0]
    except ValueError:
        token = exec_line.split()[0] if exec_line.split() else ""
    name = Path(token).name
    return [name] if name else []


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


def write_youtube_desktop(enabled: bool) -> None:
    launch = PLUGIN_DIR / "scripts" / "launch-youtube"
    if not YT_DESKTOP.is_file():
        return
    text = YT_DESKTOP.read_text(encoding="utf-8")
    stock = "Exec=omarchy-launch-webapp https://youtube.com/"
    typed = f"Exec={launch}"
    if enabled:
        if "launch-youtube" not in text:
            text = re.sub(r"^Exec=.*$", typed, text, count=1, flags=re.M)
            YT_DESKTOP.write_text(text, encoding="utf-8")
    else:
        if "launch-youtube" in text:
            text = re.sub(r"^Exec=.*$", stock, text, count=1, flags=re.M)
            YT_DESKTOP.write_text(text, encoding="utf-8")


def clear_chromium_ui(family: str) -> None:
    if CHROMIUM_DESKTOP.is_file():
        text = CHROMIUM_DESKTOP.read_text(encoding="utf-8", errors="replace")
        if TYPE_DESKTOP_MARK in text:
            CHROMIUM_DESKTOP.unlink()
    if not CHROMIUM_PREFS.is_file():
        return
    try:
        data = json.loads(CHROMIUM_PREFS.read_text(encoding="utf-8"))
    except Exception:
        return
    if not isinstance(data, dict):
        return
    webkit = data.get("webkit")
    if not isinstance(webkit, dict):
        return
    webprefs = webkit.get("webprefs")
    if not isinstance(webprefs, dict):
        return
    changed = False
    fonts = webprefs.get("fonts")
    if isinstance(fonts, dict):
        for generic in ("standard", "sansserif", "serif", "fixed"):
            slot = fonts.get(generic)
            if isinstance(slot, dict) and slot.get("Zyyy") == family:
                slot.pop("Zyyy", None)
                changed = True
    if webprefs.get("default_font_size") in (14, 15):
        webprefs["default_font_size"] = 16
        webprefs["default_fixed_font_size"] = 13
        changed = True
    if not changed:
        return
    try:
        CHROMIUM_PREFS.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    except OSError:
        log("could not restore Chromium preferences")


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


def parse_desktop(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return data
    in_entry = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_entry = line == "[Desktop Entry]"
            continue
        if not in_entry or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key not in data:
            data[key] = value
    return data


def find_desktop_path(desktop_id: str) -> Path | None:
    name = desktop_id if desktop_id.endswith(".desktop") else f"{desktop_id}.desktop"
    for directory in DESKTOP_DIRS:
        path = directory / name
        if path.is_file():
            return path
    return None


def hosts_from_wmclass(wmclass: str) -> list[str]:
    wm = str(wmclass or "")
    if wm.startswith("chrome-") and "__" in wm:
        host = wm[len("chrome-"):].split("__", 1)[0].removeprefix("www.")
        if host and "." in host:
            return [host]
    return []


def hosts_from_exec(exec_line: str) -> list[str]:
    urls = re.findall(r"https?://[^\s\"']+", exec_line)
    app = re.search(r"--app=([^\s]+)", exec_line)
    if app:
        urls.append(app.group(1).strip("\"'"))
    hosts = []
    for url in urls:
        host = (urlparse(url).hostname or "").removeprefix("www.")
        if host and host not in LOCAL_HOSTS:
            hosts.append(host)
    return list(dict.fromkeys(hosts))


def _exec_token(exec_line: str) -> Path | None:
    try:
        parts = shlex.split(exec_line, posix=True)
    except ValueError:
        parts = exec_line.split()
    if not parts:
        return None
    token = Path(parts[0])
    if token.is_absolute():
        return token
    from shutil import which
    found = which(parts[0])
    return Path(found) if found else token


def is_electron_command(exec_line: str) -> bool:
    low = exec_line.lower()
    if any(s in low for s in ("electron", "grok-bot", "launch-grok")):
        return True
    path = _exec_token(exec_line)
    if not path:
        return False
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:8000]
    except OSError:
        head = ""
    if head.startswith("#!") and ("asar" in head or "electron" in head.lower()):
        return True
    bases = [path.parent, path.parent / "resources", Path("/usr/lib") / path.stem, Path("/usr/share") / path.stem]
    return any(
        (base / name).is_file()
        for base in bases
        for name in ("app.asar", "resources/app.asar", "obsidian.asar")
    )


def recipe_for_desktop(desktop_id: str, hosts: list[str]) -> dict | None:
    name = desktop_id if desktop_id.endswith(".desktop") else f"{desktop_id}.desktop"
    for recipe in RECIPES.values():
        if recipe["desktop"].lower() == name.lower():
            return recipe
        recipe_hosts = {h.removeprefix("www.") for h in recipe.get("hosts") or []}
        if recipe_hosts and recipe_hosts.intersection(h.removeprefix("www.") for h in hosts):
            return recipe
    return None


def classify_desktop(desktop_id: str, parsed: dict[str, str]) -> tuple[str, list[str]]:
    hosts = hosts_from_exec(parsed.get("Exec") or "") or hosts_from_wmclass(parsed.get("StartupWMClass") or "")
    recipe = recipe_for_desktop(desktop_id, hosts)
    if recipe:
        return recipe["kind"], list(recipe.get("hosts") or hosts)
    name = desktop_id.lower()
    exec_line = parsed.get("Exec") or ""
    if name in BROWSER_DESKTOPS:
        return "skip", []
    if is_electron_command(exec_line):
        return "electron", hosts
    if "omarchy-launch-webapp" in exec_line or "--app=" in exec_line or hosts:
        if not hosts:
            return "skip", []
        return "chromium", hosts
    return "skip", []


def desktop_to_app(path: Path) -> dict | None:
    parsed = parse_desktop(path)
    if parsed.get("Type", "Application") not in ("Application", ""):
        return None
    if parsed.get("NoDisplay", "").lower() == "true":
        return None
    if parsed.get("Hidden", "").lower() == "true":
        return None
    if not parsed.get("Name"):
        return None
    desktop_id = path.name
    hosts: list[str]
    kind, hosts = classify_desktop(desktop_id, parsed)
    if kind not in COMPATIBLE_KINDS:
        return None
    if kind == "chromium" and not hosts:
        return None
    recipe = recipe_for_desktop(desktop_id, hosts)
    if recipe:
        return recipe_app(recipe["id"], enabled=True)
    slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-") or path.stem.lower()
    return {
        "id": slug,
        "label": parsed["Name"],
        "desktop": desktop_id,
        "kind": kind,
        "hosts": hosts,
        "enabled": True,
        "scale": 1.0,
    }


def list_installed_apps(cfg: dict | None = None) -> list[dict]:
    taken = set()
    if cfg:
        for app in cfg["apps"]:
            taken.add(app["id"])
            taken.add(app.get("desktop") or "")
            taken.add((app.get("desktop") or "").lower())
    found: dict[str, dict] = {}
    for directory in DESKTOP_DIRS:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.desktop")):
            if path.name in taken or path.name.lower() in taken:
                continue
            app = desktop_to_app(path)
            if not app or app["kind"] not in COMPATIBLE_KINDS:
                continue
            if app["id"] in taken or app["id"] in found:
                continue
            found[app["id"]] = {
                "id": app["id"],
                "label": app["label"],
                "desktop": app["desktop"],
                "kind": app["kind"],
            }
    return sorted(found.values(), key=lambda a: a["label"].lower())


def apply() -> int:
    cfg = load_config()
    family = current_font()
    write_chromium_extension(cfg, family)
    ensure_chromium_flags(cfg, family)
    write_fontconfig(cfg, family)
    grok = find_app(cfg, "grok-bot")
    write_grok_desktop(bool(grok and app_active(cfg, grok)))
    youtube = find_app(cfg, "youtube")
    write_youtube_desktop(bool(youtube and app_active(cfg, youtube)))
    clear_chromium_ui(family)
    if grok and app_active(cfg, grok):
        css = css_for_app(grok, family)
        inject_cdp(Path("/tmp/grok-bot-devtools-port"), css)
        inject_cdp(Path.home() / ".config/Grok Bot/DevToolsActivePort", css)
    am = find_app(cfg, "apple-music")
    if am and app_active(cfg, am):
        inject_cdp(AM_PROFILE / "DevToolsActivePort", css_for_app(am, family))
    if youtube and app_active(cfg, youtube):
        yt_port = Path("/tmp/omarchy-type-youtube-devtools")
        if not yt_port.is_file():
            yt_port.write_text("9340\n", encoding="utf-8")
        inject_cdp(yt_port, css_for_app(youtube, family))
    save_config(cfg)
    print(json.dumps({"ok": True, "font": family, "config": cfg}, indent=2))
    return 0


def set_master(enabled: bool) -> int:
    cfg = load_config()
    cfg["enabled"] = enabled
    save_config(cfg)
    return apply()


def set_app(app_id: str, enabled: bool | None = None, scale: float | None = None) -> int:
    cfg = load_config()
    app = find_app(cfg, app_id)
    if not app:
        log(f"unknown app {app_id}")
        return 1
    if enabled is not None:
        app["enabled"] = enabled
    if scale is not None:
        app["scale"] = clamp_scale(scale)
    save_config(cfg)
    return apply()


def add_app(desktop_id: str) -> int:
    path = find_desktop_path(desktop_id)
    if not path:
        log(f"desktop not found: {desktop_id}")
        return 1
    app = desktop_to_app(path)
    if not app or app["kind"] not in COMPATIBLE_KINDS:
        log(f"not a webapp or Electron app: {desktop_id}")
        return 1
    cfg = load_config()
    if find_app(cfg, app["id"]) or any(a.get("desktop") == app["desktop"] for a in cfg["apps"]):
        log(f"already added {app['id']}")
        return apply()
    cfg["apps"].append(app)
    save_config(cfg)
    return apply()


def remove_app(app_id: str) -> int:
    cfg = load_config()
    next_apps = [a for a in cfg["apps"] if a["id"] != app_id]
    if len(next_apps) == len(cfg["apps"]):
        log(f"unknown app {app_id}")
        return 1
    cfg["apps"] = next_apps
    save_config(cfg)
    return apply()


def _proc_exe(pid: int) -> str:
    try:
        return os.readlink(f"/proc/{pid}/exe")
    except OSError:
        return ""


def _proc_cmdline(pid: int) -> list[str]:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return []
    return [p.decode("utf-8", "replace") for p in raw.split(b"\0") if p]


def _class_needles(app: dict) -> list[str]:
    if app["id"] == "youtube":
        return ["youtube.com__"]
    if app["id"] == "apple-music":
        return ["music.apple.com__"]
    if app["id"] == "grok-bot":
        return ["Grok Bot"]
    return [f"{h}__" for h in app.get("hosts") or []]


def pids_for_app(app: dict) -> list[int]:
    found: list[int] = []
    try:
        clients = json.loads(subprocess.check_output(["hyprctl", "clients", "-j"], text=True))
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError):
        clients = []
    needles = _class_needles(app)
    if isinstance(clients, list):
        for client in clients:
            cls = str(client.get("class") or "")
            if any(n in cls for n in needles):
                pid = client.get("pid")
                if isinstance(pid, int) and pid > 1:
                    found.append(pid)
    hosts = app.get("hosts") or []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        argv = _proc_cmdline(pid)
        if not argv:
            continue
        line = " ".join(argv)
        if "apply.py" in line:
            continue
        exe = _proc_exe(pid)
        if app["id"] == "grok-bot":
            if "grok-bot" in exe or any("grok-bot" in a for a in argv):
                found.append(pid)
            continue
        if "chromium" not in exe and "chrome" not in Path(exe).name:
            continue
        if app["id"] == "apple-music" and "omarchy-apple-music" in line:
            found.append(pid)
            continue
        app_url = next((a[6:] for a in argv if a.startswith("--app=")), "")
        if app_url and hosts and any(h in app_url for h in hosts):
            found.append(pid)
    return list(dict.fromkeys(found))


def kill_pids(pids: list[int]) -> None:
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.time() + 2.0
    while time.time() < deadline:
        if not any(Path(f"/proc/{pid}").exists() for pid in pids):
            return
        time.sleep(0.1)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def launch_app(app: dict) -> None:
    if app["id"] == "youtube":
        cmd = [str(PLUGIN_DIR / "scripts" / "launch-youtube")]
    elif app["id"] == "grok-bot":
        cmd = [str(PLUGIN_DIR / "scripts" / "launch-grok")]
    else:
        desktop = find_desktop_path(app.get("desktop") or "")
        parsed = parse_desktop(desktop) if desktop else {}
        exec_line = parsed.get("Exec") or ""
        try:
            parts = shlex.split(exec_line, posix=True)
        except ValueError:
            parts = exec_line.split()
        cmd = [p for p in parts if p not in ("%U", "%u", "%F", "%f")]
        if not cmd:
            return
    subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def restart_app(app_id: str) -> int:
    cfg = load_config()
    app = find_app(cfg, app_id)
    if not app:
        log(f"unknown app {app_id}")
        return 1
    running = pids_for_app(app)
    rc = apply()
    if running:
        kill_pids(running)
        time.sleep(0.35)
    cfg = load_config()
    app = find_app(cfg, app_id)
    if app and app_active(cfg, app) and running:
        launch_app(app)
    return rc


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "apply"
    if cmd == "apply":
        return apply()
    if cmd == "refresh":
        if len(argv) >= 3:
            return restart_app(argv[2])
        return apply()
    if cmd == "status":
        print(json.dumps({"font": current_font(), "config": load_config()}, indent=2))
        return 0
    if cmd == "apps":
        print(json.dumps(list_installed_apps(load_config()), indent=2))
        return 0
    if cmd == "add" and len(argv) >= 3:
        return add_app(argv[2])
    if cmd == "remove" and len(argv) >= 3:
        return remove_app(argv[2])
    if cmd == "enable":
        if len(argv) >= 3:
            return set_app(argv[2], enabled=True)
        return set_master(True)
    if cmd == "disable":
        if len(argv) >= 3:
            return set_app(argv[2], enabled=False)
        return set_master(False)
    if cmd == "scale" and len(argv) >= 4:
        rc = set_app(argv[2], scale=float(argv[3]))
        if rc == 0:
            restart_app(argv[2])
        return rc
    if cmd == "toggle":
        cfg = load_config()
        if len(argv) >= 3:
            app = find_app(cfg, argv[2])
            if not app:
                log(f"unknown app {argv[2]}")
                return 1
            return set_app(argv[2], enabled=not app["enabled"])
        return set_master(not cfg.get("enabled", True))
    print(
        "Usage: apply.py apply|status|apps|add <desktop>|remove <id>|"
        "enable [id]|disable [id]|toggle [id]|scale <id> <0.7-1.2>|refresh <id>",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
