.pragma library

var CONFIG_PATH_SUFFIX = ".config/omarchy/type.json"
var EXT_DIR_SUFFIX = ".local/share/omarchy-type/chromium-ext"

var SURFACES = [
  {
    id: "apple-music",
    label: "Apple Music",
    kind: "chromium",
    hosts: ["music.apple.com"],
    defaultEnabled: true,
    defaultScale: 0.92,
    description: "Web player"
  },
  {
    id: "grok-bot",
    label: "Grok Bot",
    kind: "electron",
    hosts: [],
    defaultEnabled: true,
    defaultScale: 1.0,
    description: "Desktop agent"
  },
  {
    id: "youtube",
    label: "YouTube",
    kind: "chromium",
    hosts: ["youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"],
    defaultEnabled: false,
    defaultScale: 0.94,
    description: "Webapp"
  }
]

function defaultConfig() {
  var surfaces = {}
  for (var i = 0; i < SURFACES.length; i++) {
    var s = SURFACES[i]
    surfaces[s.id] = { enabled: s.defaultEnabled, scale: s.defaultScale }
  }
  return { surfaces: surfaces }
}

function mergeConfig(raw) {
  var base = defaultConfig()
  if (!raw || typeof raw !== "object") return base
  var incoming = raw.surfaces && typeof raw.surfaces === "object" ? raw.surfaces : {}
  for (var i = 0; i < SURFACES.length; i++) {
    var id = SURFACES[i].id
    var row = incoming[id]
    if (!row || typeof row !== "object") continue
    if (typeof row.enabled === "boolean") base.surfaces[id].enabled = row.enabled
    var scale = Number(row.scale)
    if (scale >= 0.7 && scale <= 1.2) base.surfaces[id].scale = Math.round(scale * 100) / 100
  }
  return base
}

function clampScale(value) {
  var scale = Number(value)
  if (!(scale >= 0.7 && scale <= 1.2)) return 1
  return Math.round(scale * 100) / 100
}

function cssPercent(scale) {
  return String(Math.round(clampScale(scale) * 100)) + "%"
}

function appleMusicCss(family, scale) {
  var q = JSON.stringify(family)
  var pct = cssPercent(scale)
  return (
    "html.omarchy-type{" +
      "font-family:" + q + ", ui-monospace, monospace !important;" +
      "font-size:" + pct + " !important;" +
    "}" +
    "html.omarchy-type body,html.omarchy-type button,html.omarchy-type input," +
    "html.omarchy-type textarea,html.omarchy-type select{font-family:inherit !important;}" +
    "html.omarchy-type *{font-family:" + q + ", ui-monospace, monospace !important;letter-spacing:-0.01em;}" +
    "html.omarchy-type .navigation-item__link:hover{" +
      "background-color:color-mix(in srgb, currentColor 16%, transparent) !important;" +
    "}"
  )
}

function grokBotCss(family, scale) {
  var q = JSON.stringify(family)
  var pct = cssPercent(scale)
  return (
    ":root,html,body,#root{" +
      "--cursor-font-family:" + q + ", monospace !important;" +
      "--cursor-font-family-sans:" + q + ", monospace !important;" +
      "--cursor-font-family-mono:" + q + ", monospace !important;" +
      "--cursor-font-mono:" + q + ", monospace !important;" +
      "--vscode-font-family:" + q + ", monospace !important;" +
      "--monaco-monospace-font:" + q + ", monospace !important;" +
      "--font-family-mono:" + q + ", monospace !important;" +
      "--font-family-monospace:" + q + ", monospace !important;" +
      "font-family:" + q + ", monospace !important;" +
      "font-size:" + pct + " !important;" +
    "}"
  )
}

function youtubeCss(family, scale) {
  var q = JSON.stringify(family)
  var pct = cssPercent(scale)
  return (
    "html.omarchy-type{font-size:" + pct + " !important;}" +
    "html.omarchy-type,html.omarchy-type body,html.omarchy-type ytd-app," +
    "html.omarchy-type yt-formatted-string,html.omarchy-type tp-yt-paper-item," +
    "html.omarchy-type #content{font-family:" + q + ", Roboto, sans-serif !important;}" +
    "html.omarchy-type *{font-family:" + q + ", Roboto, Arial, sans-serif !important;}"
  )
}

function cssForSurface(id, family, scale) {
  if (id === "apple-music") return appleMusicCss(family, scale)
  if (id === "grok-bot") return grokBotCss(family, scale)
  if (id === "youtube") return youtubeCss(family, scale)
  return ""
}

function surfaceById(id) {
  for (var i = 0; i < SURFACES.length; i++) {
    if (SURFACES[i].id === id) return SURFACES[i]
  }
  return null
}

function hostToSurfaceId(hostname) {
  var host = String(hostname || "").replace(/^www\./, "")
  for (var i = 0; i < SURFACES.length; i++) {
    var s = SURFACES[i]
    for (var j = 0; j < s.hosts.length; j++) {
      var h = String(s.hosts[j]).replace(/^www\./, "")
      if (host === h || host.slice(-("." + h).length) === "." + h) return s.id
    }
  }
  return ""
}
