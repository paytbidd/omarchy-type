(function () {
  var surfaces = window.__omarchyTypeSurfaces || {}
  var host = String(location.hostname || "").replace(/^www\./, "")
  var css = ""
  var ids = Object.keys(surfaces)
  for (var i = 0; i < ids.length; i++) {
    var spec = surfaces[ids[i]]
    var hosts = spec.hosts || []
    for (var j = 0; j < hosts.length; j++) {
      var h = String(hosts[j] || "").replace(/^www\./, "")
      if (host === h || host.slice(-(h.length + 1)) === "." + h) {
        css = spec.css || ""
        break
      }
    }
    if (css) break
  }
  if (!css) return
  function apply() {
    var style = document.getElementById("omarchy-type")
    if (!style) {
      style = document.createElement("style")
      style.id = "omarchy-type"
      var hostEl = document.head || document.documentElement
      if (hostEl) hostEl.appendChild(style)
    }
    if (style) style.textContent = css
    if (document.documentElement) document.documentElement.classList.add("omarchy-type")
  }
  apply()
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply)
  }
})()
