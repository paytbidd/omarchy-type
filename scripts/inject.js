(function () {
  var surfaces = window.__omarchyTypeSurfaces || {}
  var host = String(location.hostname || "").replace(/^www\./, "")
  var spec = null
  var ids = Object.keys(surfaces)
  for (var i = 0; i < ids.length; i++) {
    var row = surfaces[ids[i]]
    var hosts = row.hosts || []
    for (var j = 0; j < hosts.length; j++) {
      var h = String(hosts[j] || "").replace(/^www\./, "")
      if (host === h || host.slice(-(h.length + 1)) === "." + h) {
        spec = row
        break
      }
    }
    if (spec) break
  }
  if (!spec || !spec.css) return

  var css = spec.css
  var sheet = null
  try {
    sheet = new CSSStyleSheet()
    sheet.replaceSync(css)
  } catch (_) {
    sheet = null
  }

  function hasSheet(root) {
    if (!root || !root.adoptedStyleSheets || !sheet) return false
    var list = root.adoptedStyleSheets
    for (var i = 0; i < list.length; i++) {
      if (list[i] === sheet) return true
    }
    return false
  }

  function stamp(root) {
    if (!root) return
    if (sheet && root.adoptedStyleSheets !== undefined) {
      if (!hasSheet(root)) {
        try {
          root.adoptedStyleSheets = root.adoptedStyleSheets.concat(sheet)
        } catch (_) {}
      }
      return
    }
    var existing = root.getElementById && root.getElementById("omarchy-type")
    if (existing) {
      existing.textContent = css
      return
    }
    var style = document.createElement("style")
    style.id = "omarchy-type"
    style.textContent = css
    var hostEl = root.head || root
    try { hostEl.appendChild(style) } catch (_) {}
  }

  function walk(node) {
    if (!node) return
    if (node.shadowRoot) {
      stamp(node.shadowRoot)
      walk(node.shadowRoot)
    }
    var kids = node.querySelectorAll ? node.querySelectorAll("*") : []
    for (var i = 0; i < kids.length; i++) {
      if (kids[i].shadowRoot) {
        stamp(kids[i].shadowRoot)
        walk(kids[i].shadowRoot)
      }
    }
  }

  function apply() {
    if (document.documentElement) document.documentElement.classList.add("omarchy-type")
    stamp(document)
    if (spec.shadow) walk(document.documentElement || document)
  }

  apply()
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply)
  }
  window.addEventListener("yt-navigate-finish", apply)
  window.addEventListener("pageshow", apply)

  if (spec.shadow && typeof MutationObserver !== "undefined" && document.documentElement) {
    var timer = 0
    var observer = new MutationObserver(function () {
      clearTimeout(timer)
      timer = setTimeout(apply, 250)
    })
    observer.observe(document.documentElement, { childList: true, subtree: true })
  }
})()
