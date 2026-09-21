const assert = require("assert")
const fs = require("fs")
const path = require("path")
const src = fs.readFileSync(path.join(__dirname, "..", "Model.js"), "utf8")
  .replace(/^\.pragma library\s*/, "")
eval(src)

assert.equal(defaultConfig().apps.length, 3)
assert.equal(defaultConfig().enabled, true)
assert.equal(defaultConfig().apps[0].id, "apple-music")
assert.equal(defaultConfig().apps.find(a => a.id === "youtube").enabled, false)
assert.equal(defaultConfig().apps.find(a => a.id === "chromium"), undefined)

const migrated = mergeConfig({
  surfaces: { youtube: { enabled: true, scale: 0.9 }, "apple-music": { enabled: true, scale: 0.92 } }
})
assert.equal(migrated.enabled, true)
assert.equal(migrated.apps.find(a => a.id === "youtube").enabled, true)
assert.equal(migrated.apps.find(a => a.id === "youtube").scale, 0.9)
assert.equal(migrated.apps.find(a => a.id === "chromium"), undefined)

const listed = mergeConfig({
  enabled: false,
  apps: [
    { id: "chromium", label: "Chromium", desktop: "chromium.desktop", kind: "chromium-ui", enabled: true, scale: 0.92 },
    { id: "discord", label: "Discord", desktop: "Discord.desktop", kind: "chromium", hosts: ["discord.com"], enabled: true, scale: 1 }
  ]
})
assert.equal(listed.enabled, false)
assert.equal(listed.apps.length, 1)
assert.equal(listed.apps[0].id, "discord")
assert.equal(listed.apps[0].hosts[0], "discord.com")

assert.equal(mergeConfig({ apps: [{ id: "youtube", scale: 9 }] }).apps[0].scale, 1)
assert.equal(cssPercent(0.92), "92%")
assert.equal(hostToAppId("music.apple.com"), "apple-music")
assert.equal(hostToAppId("www.youtube.com"), "youtube")
assert.equal(hostToAppId("youtu.be"), "youtube")
assert.equal(hostToAppId("discord.com", listed.apps), "discord")
assert.equal(appleMusicCss("iA Writer Mono S", 0.92).indexOf("92%") !== -1, true)
assert.equal(grokBotCss("iA Writer Mono S", 1).indexOf("--cursor-font-family") !== -1, true)
assert.equal(youtubeCss("iA Writer Mono S", 0.94).indexOf("Roboto") !== -1, true)
assert.equal(youtubeCss("iA Writer Mono S", 0.86).indexOf("zoom:0.86") !== -1, true)
assert.equal(youtubeCss("iA Writer Mono S", 0.86).indexOf("font-size:86%") === -1, true)
assert.equal(youtubeCss("iA Writer Mono S", 0.86).indexOf("--ytd-guide-width:260px") !== -1, true)
assert.equal(genericCss("iA Writer Mono S", 0.86).indexOf("86%") !== -1, true)
assert.equal(cssForSurface("nope", "X", 1).indexOf("X") !== -1, true)
assert.equal(sanitizeApp({ id: "chromium", kind: "chromium-ui" }), null)

const fontPath = path.join(__dirname, "..", "fonts", "ChicagoKare-Regular.ttf")
assert.equal(fs.existsSync(fontPath), true)

console.log("omarchy-type model tests passed")
