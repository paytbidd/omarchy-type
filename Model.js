.pragma library

var CONFIG_PATH_SUFFIX = ".config/omarchy/type.json"
var EXT_DIR_SUFFIX = ".local/share/omarchy-type/chromium-ext"

var RECIPES = {
  "apple-music": {
    id: "apple-music",
    label: "Apple Music",
    desktop: "omarchy-apple-music.desktop",
    kind: "chromium",
    hosts: ["music.apple.com"],
    defaultEnabled: true,
    defaultScale: 0.92
  },
  "grok-bot": {
    id: "grok-bot",
    label: "Grok Bot",
    desktop: "grok-bot.desktop",
    kind: "electron",
    hosts: [],
    defaultEnabled: true,
    defaultScale: 1.0
  },
  "youtube": {
    id: "youtube",
    label: "YouTube",
    desktop: "YouTube.desktop",
    kind: "chromium",
    hosts: ["youtube.com", "youtu.be", "m.youtube.com"],
    defaultEnabled: false,
    defaultScale: 0.94
  }
}

var DEFAULT_IDS = ["apple-music", "grok-bot", "youtube"]

function recipeApp(id) {
  var r = RECIPES[id]
  if (!r) return null
  return {
    id: r.id,
    label: r.label,
    desktop: r.desktop,
    kind: r.kind,
    hosts: r.hosts.slice(),
    enabled: r.defaultEnabled,
    scale: r.defaultScale
  }
}

function defaultApps() {
  var apps = []
  for (var i = 0; i < DEFAULT_IDS.length; i++) apps.push(recipeApp(DEFAULT_IDS[i]))
  return apps
}

function defaultConfig() {
  return { enabled: true, apps: defaultApps() }
}

function clampScale(value) {
  var scale = Number(value)
  if (!(scale >= 0.7 && scale <= 1.2)) return 1
  return Math.round(scale * 100) / 100
}

function cssPercent(scale) {
  return String(Math.round(clampScale(scale) * 100)) + "%"
}

function sanitizeApp(row) {
  if (!row || typeof row !== "object") return null
  var id = String(row.id || "").trim()
  if (!id) return null
  var recipe = RECIPES[id] || null
  var kind = String(row.kind || (recipe ? recipe.kind : "chromium"))
  if (kind === "chromium-ui") return null
  if (kind !== "chromium" && kind !== "electron" && kind !== "other") {
    kind = recipe ? recipe.kind : "other"
  }
  var hosts = []
  var rawHosts = row.hosts
  if (!rawHosts && recipe) rawHosts = recipe.hosts
  if (rawHosts && rawHosts.length) {
    for (var i = 0; i < rawHosts.length; i++) {
      var h = String(rawHosts[i] || "").replace(/^www\./, "").trim()
      if (h && hosts.indexOf(h) === -1) hosts.push(h)
    }
  }
  var scale = clampScale(row.scale)
  if (row.scale === undefined && recipe) scale = recipe.defaultScale
  return {
    id: id,
    label: String(row.label || (recipe ? recipe.label : id)),
    desktop: String(row.desktop || (recipe ? recipe.desktop : id + ".desktop")),
    kind: kind,
    hosts: hosts,
    enabled: row.enabled !== false,
    scale: scale
  }
}

function migrateSurfaces(surfaces) {
  var apps = defaultApps()
  if (!surfaces || typeof surfaces !== "object") return apps
  var byId = {}
  for (var i = 0; i < apps.length; i++) byId[apps[i].id] = apps[i]
  for (var sid in surfaces) {
    if (!Object.prototype.hasOwnProperty.call(surfaces, sid)) continue
    var row = surfaces[sid]
    if (!row || typeof row !== "object" || !byId[sid]) continue
    if (typeof row.enabled === "boolean") byId[sid].enabled = row.enabled
    var scale = Number(row.scale)
    if (scale >= 0.7 && scale <= 1.2) byId[sid].scale = Math.round(scale * 100) / 100
  }
  return apps
}

function mergeConfig(raw) {
  if (!raw || typeof raw !== "object") return defaultConfig()
  var enabled = raw.enabled !== false
  var apps
  if (Object.prototype.toString.call(raw.apps) === "[object Array]") {
    apps = []
    var seen = {}
    for (var i = 0; i < raw.apps.length; i++) {
      var app = sanitizeApp(raw.apps[i])
      if (!app || seen[app.id]) continue
      seen[app.id] = true
      apps.push(app)
    }
  } else {
    apps = migrateSurfaces(raw.surfaces)
  }
  return { enabled: enabled, apps: apps }
}

function appById(config, id) {
  var apps = config && config.apps ? config.apps : []
  for (var i = 0; i < apps.length; i++) {
    if (apps[i].id === id) return apps[i]
  }
  return null
}

function hostMatches(host, candidate) {
  var h = String(host || "").replace(/^www\./, "")
  var c = String(candidate || "").replace(/^www\./, "")
  if (!h || !c) return false
  return h === c || h.slice(-(c.length + 1)) === "." + c
}

function hostToAppId(hostname, apps) {
  var list = apps || defaultConfig().apps
  var host = String(hostname || "").replace(/^www\./, "")
  for (var i = 0; i < list.length; i++) {
    var s = list[i]
    var hosts = s.hosts || []
    for (var j = 0; j < hosts.length; j++) {
      if (hostMatches(host, hosts[j])) return s.id
    }
  }
  return ""
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
  var z = clampScale(scale).toFixed(2)
  var guide = Math.max(260, Math.round(280 * clampScale(scale)))
  var masthead = Math.max(52, Math.round(56 * Math.max(clampScale(scale), 0.95)))
  return (
    "html.omarchy-type,html.omarchy-type body,html.omarchy-type ytd-app," +
    "html.omarchy-type yt-formatted-string,html.omarchy-type tp-yt-paper-item," +
    "html.omarchy-type #content,html.omarchy-type *{font-family:" + q + ", Roboto, Arial, sans-serif !important;}" +
    "html.omarchy-type ytd-app{--ytd-guide-width:" + guide + "px !important;" +
      "--app-drawer-width:" + guide + "px !important;--ytd-masthead-height:" + masthead + "px !important;}" +
    "html.omarchy-type ytd-masthead,html.omarchy-type #masthead-container,html.omarchy-type #header{" +
      "min-height:" + masthead + "px !important;height:" + masthead + "px !important;" +
      "font-size:14px !important;zoom:1 !important;}" +
    "html.omarchy-type ytd-guide-renderer,html.omarchy-type #guide-content," +
    "html.omarchy-type #guide-inner-content{width:" + guide + "px !important;min-width:" + guide + "px !important;}" +
    "html.omarchy-type #guide yt-formatted-string,html.omarchy-type ytd-guide-entry-renderer{font-size:13px !important;}" +
    "html.omarchy-type ytd-page-manager,html.omarchy-type #page-manager," +
    "html.omarchy-type ytd-browse,html.omarchy-type ytd-watch-flexy{zoom:" + z + " !important;}"
  )
}

function genericCss(family, scale) {
  var q = JSON.stringify(family)
  var pct = cssPercent(scale)
  return (
    "html.omarchy-type{" +
      "font-family:" + q + ", ui-sans-serif, sans-serif !important;" +
      "font-size:" + pct + " !important;" +
    "}" +
    "html.omarchy-type body,html.omarchy-type button,html.omarchy-type input," +
    "html.omarchy-type textarea,html.omarchy-type select,html.omarchy-type *" +
    "{font-family:" + q + ", ui-sans-serif, sans-serif !important;}"
  )
}

function cssForApp(app, family, scale) {
  if (!app) return ""
  if (app.id === "apple-music") return appleMusicCss(family, scale)
  if (app.id === "grok-bot") return grokBotCss(family, scale)
  if (app.id === "youtube") return youtubeCss(family, scale)
  if (app.kind === "chromium") return genericCss(family, scale)
  if (app.kind === "electron") return grokBotCss(family, scale)
  return ""
}

function cssForSurface(id, family, scale) {
  return cssForApp(recipeApp(id) || { id: id, kind: "chromium" }, family, scale)
}
