# Omarchy Type

Applies the current Omarchy font to Chromium (and Electron) apps, with a
small bar panel to include or exclude each surface and fine-tune type scale.

Surfaces today:

- **Apple Music** — SF Pro replacement, 92% scale, stronger sidebar hover
- **Grok Bot** — Cursor/VS Code font variables + fontconfig remap
- **YouTube** — Roboto replacement on the YouTube webapp (off by default)

## Install

```bash
omarchy plugin add https://github.com/paytbidd/omarchy-type.git --yes
omarchy plugin enable payton.type --section right
```

Or copy this directory to `~/.config/omarchy/plugins/payton.type` and enable it.

Click **Aa** on the bar, or Super+Space → Style → Type. Toggles write `~/.config/omarchy/type.json` and
regenerate a Chromium content-script extension loaded via
`~/.config/chromium-flags.conf`. Reopen a webapp after changing membership.
`omarchy font set` re-applies through `~/.config/omarchy/hooks/font-set.d/omarchy-type`.

## CLI

```bash
python3 ~/.config/omarchy/plugins/payton.type/scripts/apply.py status
python3 ~/.config/omarchy/plugins/payton.type/scripts/apply.py enable youtube
python3 ~/.config/omarchy/plugins/payton.type/scripts/apply.py scale apple-music 0.90
```
