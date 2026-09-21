import QtQuick
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "payton.type"

  readonly property color fg: bar ? bar.foreground : Color.foreground

  function open() {
    if (bar && bar.shell && typeof bar.shell.summon === "function")
      bar.shell.summon("payton.type", "{}")
  }
  function openFromHotkey() { open() }
  function close() {
    if (bar && bar.shell && typeof bar.shell.hide === "function")
      bar.shell.hide("payton.type")
  }
  function toggle() {
    if (bar && bar.shell && typeof bar.shell.toggle === "function")
      bar.shell.toggle("payton.type", "{}")
    else
      open()
  }

  implicitWidth: glyph.implicitWidth + Style.space(10)
  implicitHeight: bar ? bar.barSize : Style.bar.sizeHorizontal

  FontLoader {
    id: chicago
    source: Qt.resolvedUrl("fonts/ChicagoKare-Regular.ttf")
  }

  Text {
    id: glyph
    anchors.centerIn: parent
    text: "Tt"
    textFormat: Text.PlainText
    color: root.fg
    font.family: chicago.status === FontLoader.Ready ? chicago.name : "Chicago Kare"
    font.pixelSize: 13
    font.kerning: false
    font.hintingPreference: Font.PreferFullHinting
    renderType: Text.NativeRendering
  }

  MouseArea {
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    acceptedButtons: Qt.LeftButton
    onClicked: root.toggle()
    onEntered: if (root.bar) root.bar.showTooltip(root, "Type")
    onExited: if (root.bar) root.bar.hideTooltip(root)
  }
}
