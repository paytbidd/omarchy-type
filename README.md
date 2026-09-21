# Omarchy Type

Applies the current Omarchy font to apps you add — Chromium webapps and
Electron. Chromium’s own chrome (tabs, toolbar) is left alone.

Open it from Super+Space → Style → Type (or type “type” in the command
menu). The panel is a list: per-app On/Off, a master On/Off, scale, Add
from installed apps, and × to remove so that app is never skinned.

There is no bar chip. This plugin stays on as a service and a summoned
panel.

`~/.config/omarchy/type.json` holds the list. A Chromium content-script
extension is generated at `~/.local/share/omarchy-type/chromium-ext`. Font
changes re-apply through `~/.config/omarchy/hooks/font-set.d/omarchy-type`.

## Install

```bash
omarchy plugin add https://github.com/paytbidd/omarchy-type.git --yes
omarchy plugin enable payton.type
```

Super+Space → Style → Type opens the panel.
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
