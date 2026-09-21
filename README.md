# Omarchy Type

Applies the current Omarchy font to apps you add — Chromium webapps and
Electron. Chromium’s own chrome (tabs, toolbar) is left alone.

Open it from Super+Space → Style → Type (or type “type” in the command
menu). The panel is a list: per-app On/Off, a master On/Off, scale, Add
from installed apps, and × to remove so that app is never skinned.

The **Tt** bar chip is optional. This plugin stays on without sitting on
the bar.

`~/.config/omarchy/type.json` holds the list. A Chromium content-script
extension is generated at `~/.local/share/omarchy-type/chromium-ext`. Font
changes re-apply through `~/.config/omarchy/hooks/font-set.d/omarchy-type`.

## Install

```bash
omarchy plugin add https://github.com/paytbidd/omarchy-type.git --yes
omarchy plugin enable payton.type
```

That enables Type without a bar chip. Super+Space → Style → Type opens
the panel. To put **Tt** on the bar:

```bash
omarchy bar put payton.type --section right
```
## CLI

```bash
python3 ~/.config/omarchy/plugins/payton.type/scripts/apply.py status
python3 ~/.config/omarchy/plugins/payton.type/scripts/apply.py enable youtube
python3 ~/.config/omarchy/plugins/payton.type/scripts/apply.py disable
python3 ~/.config/omarchy/plugins/payton.type/scripts/apply.py add Discord.desktop
python3 ~/.config/omarchy/plugins/payton.type/scripts/apply.py remove discord
python3 ~/.config/omarchy/plugins/payton.type/scripts/apply.py scale apple-music 0.92
python3 ~/.config/omarchy/plugins/payton.type/scripts/apply.py refresh youtube
```
