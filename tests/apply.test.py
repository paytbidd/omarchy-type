#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("omarchy_type_apply", ROOT / "scripts" / "apply.py")
apply = importlib.util.module_from_spec(SPEC)
sys.modules["omarchy_type_apply"] = apply
SPEC.loader.exec_module(apply)


class ApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        home = Path(self.tmp.name)
        apply.HOME = home
        apply.CONFIG_PATH = home / ".config/omarchy/type.json"
        apply.FLAGS_PATH = home / ".config/chromium-flags.conf"
        apply.EXT_DIR = home / ".local/share/omarchy-type/chromium-ext"
        apply.FONTCONF = home / ".config/fontconfig/conf.d/51-omarchy-type.conf"
        apply.OLD_GROK_FONTCONF = apply.FONTCONF.with_name("51-omarchy-type-grok.conf")
        apply.GROK_DESKTOP = home / ".local/share/applications/grok-bot.desktop"
        apply.YT_DESKTOP = home / ".local/share/applications/YouTube.desktop"
        apply.CHROMIUM_DESKTOP = home / ".local/share/applications/chromium.desktop"
        apply.CHROMIUM_PREFS = home / ".config/chromium/Default/Preferences"
        apply.AM_PROFILE = home / ".local/share/omarchy-apple-music/chromium-profile"
        apply.DESKTOP_DIRS = [home / ".local/share/applications"]
        (home / ".local/share/applications").mkdir(parents=True)
        apps_dir = home / ".local/share/applications"
        (apps_dir / "Discord.desktop").write_text(
            "[Desktop Entry]\nName=Discord\nExec=omarchy-launch-webapp https://discord.com/channels/@me\n"
            "Type=Application\n",
            encoding="utf-8",
        )
        (apps_dir / "foot.desktop").write_text(
            "[Desktop Entry]\nName=Foot\nExec=foot\nType=Application\n",
            encoding="utf-8",
        )
        (apps_dir / "cups.desktop").write_text(
            "[Desktop Entry]\nName=Manage Printing\nExec=xdg-open http://localhost:631/\nType=Application\n",
            encoding="utf-8",
        )
        electron_dir = home / "FakeElectron"
        electron_dir.mkdir()
        (electron_dir / "app.asar").write_text("x", encoding="utf-8")
        (electron_dir / "app").write_text("#!/bin/bash\n", encoding="utf-8")
        (apps_dir / "Cursor.desktop").write_text(
            f"[Desktop Entry]\nName=Cursor\nExec={electron_dir / 'app'} %F\nType=Application\n",
            encoding="utf-8",
        )
        apply.current_font = lambda: "iA Writer Mono S"
        apply.inject_cdp = lambda *args, **kwargs: False

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_migrates_surfaces_without_chromium_ui(self) -> None:
        apply.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        apply.CONFIG_PATH.write_text(json.dumps({
            "surfaces": {"youtube": {"enabled": True, "scale": 0.86}}
        }), encoding="utf-8")
        cfg = apply.load_config()
        self.assertTrue(cfg["enabled"])
        ids = [a["id"] for a in cfg["apps"]]
        self.assertEqual(ids, ["apple-music", "grok-bot", "youtube"])
        self.assertTrue(apply.find_app(cfg, "youtube")["enabled"])
        self.assertEqual(apply.find_app(cfg, "youtube")["scale"], 0.86)
        self.assertEqual(apply.find_app(cfg, "youtube")["hosts"], ["youtube.com", "youtu.be", "m.youtube.com"])

    def test_add_list_is_webapps_and_electron(self) -> None:
        listed = apply.list_installed_apps({"apps": []})
        labels = {row["label"] for row in listed}
        self.assertIn("Discord", labels)
        self.assertIn("Cursor", labels)
        self.assertNotIn("Foot", labels)
        self.assertNotIn("Manage Printing", labels)
        self.assertEqual(apply.add_app("foot.desktop"), 1)

    def test_add_remove_and_master(self) -> None:
        self.assertEqual(apply.add_app("Discord.desktop"), 0)
        cfg = apply.load_config()
        self.assertTrue(any(a["id"] == "discord" for a in cfg["apps"]))
        discord = apply.find_app(cfg, "discord")
        self.assertEqual(discord["hosts"], ["discord.com"])
        self.assertEqual(discord["kind"], "chromium")
        self.assertEqual(apply.remove_app("discord"), 0)
        self.assertIsNone(apply.find_app(apply.load_config(), "discord"))
        self.assertEqual(apply.set_master(False), 0)
        self.assertFalse(apply.load_config()["enabled"])

    def test_drops_chromium_ui_and_restores_launcher(self) -> None:
        apply.FLAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        apply.FLAGS_PATH.write_text(
            "--ozone-platform=wayland\n"
            "--load-extension=/usr/share/omarchy/default/chromium/extensions/copy-url\n"
            "--system-font-family=iA Writer Mono S\n",
            encoding="utf-8",
        )
        apply.CHROMIUM_DESKTOP.write_text(
            "# omarchy-type\n[Desktop Entry]\nName=Chromium\n"
            "Exec=/usr/bin/chromium --system-font-family=iA Writer Mono S %U\n",
            encoding="utf-8",
        )
        apply.CHROMIUM_PREFS.parent.mkdir(parents=True, exist_ok=True)
        apply.CHROMIUM_PREFS.write_text(json.dumps({
            "webkit": {"webprefs": {
                "default_font_size": 15,
                "default_fixed_font_size": 12,
                "fonts": {"standard": {"Zyyy": "iA Writer Mono S"}},
            }}
        }), encoding="utf-8")
        apply.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        apply.CONFIG_PATH.write_text(json.dumps({
            "enabled": True,
            "apps": [
                {"id": "youtube", "label": "YouTube", "kind": "chromium",
                 "hosts": ["youtube.com"], "enabled": True, "scale": 0.86},
                {"id": "chromium", "label": "Chromium", "kind": "chromium-ui",
                 "enabled": True, "scale": 0.92},
            ],
        }), encoding="utf-8")
        self.assertEqual(apply.apply(), 0)
        self.assertFalse(apply.CHROMIUM_DESKTOP.exists())
        flags = apply.FLAGS_PATH.read_text(encoding="utf-8")
        self.assertNotIn("--system-font-family=", flags)
        self.assertIn("omarchy-type/chromium-ext", flags)
        cfg = apply.load_config()
        self.assertIsNone(apply.find_app(cfg, "chromium"))
        prefs = json.loads(apply.CHROMIUM_PREFS.read_text(encoding="utf-8"))
        self.assertNotIn("Zyyy", prefs["webkit"]["webprefs"]["fonts"]["standard"])
        self.assertEqual(prefs["webkit"]["webprefs"]["default_font_size"], 16)

    def test_youtube_css_keeps_chrome(self) -> None:
        css = apply.youtube_css("iA Writer Mono S", 0.86)
        self.assertIn("zoom:0.86", css)
        self.assertNotIn("font-size:86%", css)
        self.assertIn("--ytd-guide-width:260px", css)
        self.assertIn("min-height:53px", css)

    def test_chicago_font_bundled(self) -> None:
        self.assertTrue((ROOT / "fonts" / "ChicagoKare-Regular.ttf").is_file())


if __name__ == "__main__":
    unittest.main()
