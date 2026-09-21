#!/usr/bin/env python3
"""Wait for Grok Bot CDP, then apply Omarchy Type CSS."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply as type_apply  # noqa: E402

PORT_FILE = Path("/tmp/omarchy-type-grok-devtools")


def main() -> int:
    cfg = type_apply.load_config()
    row = type_apply.find_app(cfg, "grok-bot")
    if not row or not type_apply.app_active(cfg, row):
        return 0
    family = type_apply.current_font()
    css = type_apply.grok_bot_css(family, float(row.get("scale") or 1.0))
    deadline = time.time() + 12
    while time.time() < deadline:
        try:
            import urllib.request
            with urllib.request.urlopen("http://127.0.0.1:9339/json/list", timeout=0.4) as resp:
                pages = json.loads(resp.read().decode())
            if pages:
                # Fake a DevToolsActivePort-style file for inject_cdp
                PORT_FILE.write_text("9339\n/devtools/browser\n", encoding="utf-8")
                # inject_cdp reads port from first line then /json/list
                type_apply.inject_cdp(PORT_FILE, css, timeout=1.5)
                return 0
        except Exception:
            time.sleep(0.25)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
