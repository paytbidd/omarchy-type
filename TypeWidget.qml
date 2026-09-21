import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as Model

BarWidget {
  id: root
  moduleName: "payton.type"

  property var config: Model.defaultConfig()
  property string fontName: ""
  property bool popupOpen: false
  readonly property bool opened: popupOpen
  readonly property color fg: bar ? bar.foreground : Color.foreground

  function open() { popupOpen = true }
  function openFromHotkey() { popupOpen = true }
  function close() { popupOpen = false }
  function toggle() { popupOpen = !popupOpen }

  function triggerPress(button) {
    if (button === Qt.RightButton) return
    toggle()
  }

  function refresh() {
    if (!statusProc.running) statusProc.running = true
  }

  function setEnabled(id, on) {
    Quickshell.execDetached([
      "python3", Qt.resolvedUrl("scripts/apply.py").toString().replace("file://", ""),
      on ? "enable" : "disable", id
    ])
    Qt.callLater(refresh)
  }

  function setScale(id, scale) {
    Quickshell.execDetached([
      "python3", Qt.resolvedUrl("scripts/apply.py").toString().replace("file://", ""),
      "scale", id, String(scale)
    ])
    Qt.callLater(refresh)
  }

  implicitWidth: glyph.implicitWidth + Style.space(10)
  implicitHeight: bar ? bar.barSize : Style.bar.sizeHorizontal

  Text {
    id: glyph
    anchors.centerIn: parent
    text: "Tt"
    color: root.fg
    font.family: bar ? bar.fontFamily : Style.font.family
    font.pixelSize: Style.font.caption
    font.bold: true
  }

  MouseArea {
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    acceptedButtons: Qt.LeftButton
    onClicked: root.toggle()
    onEntered: if (root.bar) root.bar.showTooltip(root, "Omarchy Type")
    onExited: if (root.bar) root.bar.hideTooltip(root)
  }

  Process {
    id: statusProc
    command: ["python3", Qt.resolvedUrl("scripts/apply.py").toString().replace("file://", ""), "status"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try {
          var data = JSON.parse(text)
          if (data.font) root.fontName = data.font
          if (data.config) root.config = Model.mergeConfig(data.config)
        } catch (e) {}
      }
    }
  }

  Timer {
    interval: 400
    running: root.popupOpen
    repeat: false
    onTriggered: root.refresh()
  }

  Component.onCompleted: refresh()

  PopupCard {
    id: popup
    anchorItem: root
    bar: root.bar
    owner: root
    open: root.popupOpen
    contentWidth: popup.fittedContentWidth(Style.space(320))
    contentHeight: popup.fittedContentHeight(body.implicitHeight)

    Column {
      id: body
      width: parent.width
      spacing: Style.space(8)

      Row {
        width: parent.width
        spacing: Style.space(8)

        Text {
          text: "Type"
          color: root.fg
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.subtitle
          font.bold: true
          anchors.verticalCenter: parent.verticalCenter
        }

        Text {
          text: root.fontName !== "" ? root.fontName : "Omarchy font"
          color: Qt.darker(root.fg, 1.45)
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.caption
          elide: Text.ElideRight
          width: parent.width - Style.space(64)
          anchors.verticalCenter: parent.verticalCenter
        }
      }

      Repeater {
        model: Model.SURFACES

        Column {
          id: surfaceRow
          required property var modelData
          readonly property string surfaceId: modelData.id
          readonly property bool on: !!(root.config.surfaces[surfaceId] && root.config.surfaces[surfaceId].enabled)
          width: body.width
          spacing: Style.space(6)

          BorderSurface {
            width: parent.width
            implicitHeight: rowInner.implicitHeight + Style.space(12)
            radius: Style.cornerRadius
            color: rowMouse.containsMouse
              ? Style.hoverFillFor(root.fg, root.fg)
              : (surfaceRow.on ? Style.normalFillFor(root.fg, root.fg) : "transparent")
            borderSpec: surfaceRow.on
              ? Border.controlSpec("normal", root.fg, root.fg)
              : Border.none()

            Row {
              id: rowInner
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              anchors.leftMargin: Style.space(10)
              anchors.rightMargin: Style.space(10)
              spacing: Style.space(8)

              Column {
                width: parent.width - toggleLabel.implicitWidth - Style.space(8)
                spacing: Style.space(1)
                Text {
                  width: parent.width
                  text: surfaceRow.modelData.label
                  color: root.fg
                  font.family: root.bar ? root.bar.fontFamily : Style.font.family
                  font.pixelSize: Style.font.body
                  elide: Text.ElideRight
                }
                Text {
                  width: parent.width
                  text: surfaceRow.modelData.description
                  color: Qt.darker(root.fg, 1.5)
                  font.family: root.bar ? root.bar.fontFamily : Style.font.family
                  font.pixelSize: Style.font.caption
                  elide: Text.ElideRight
                }
              }

              Text {
                id: toggleLabel
                text: surfaceRow.on ? "On" : "Off"
                color: root.fg
                font.family: root.bar ? root.bar.fontFamily : Style.font.family
                font.pixelSize: Style.font.body
                font.bold: surfaceRow.on
                anchors.verticalCenter: parent.verticalCenter
              }
            }

            MouseArea {
              id: rowMouse
              anchors.fill: parent
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              Accessible.role: Accessible.Button
              Accessible.name: (surfaceRow.on ? "Disable " : "Enable ") + surfaceRow.modelData.label
              onClicked: root.setEnabled(surfaceRow.surfaceId, !surfaceRow.on)
            }
          }

          Row {
            width: parent.width
            spacing: Style.space(6)
            visible: surfaceRow.on
            leftPadding: Style.space(10)

            Repeater {
              model: [0.8, 0.86, 0.92, 1.0, 1.08]

              Text {
                required property var modelData
                readonly property real scaleValue: Number(modelData)
                readonly property bool selected: {
                  var current = root.config.surfaces[surfaceRow.surfaceId]
                    ? root.config.surfaces[surfaceRow.surfaceId].scale : 1
                  return Math.abs(current - scaleValue) < 0.01
                }
                text: Math.round(scaleValue * 100) + "%"
                color: selected ? root.fg : Qt.darker(root.fg, 1.55)
                font.family: root.bar ? root.bar.fontFamily : Style.font.family
                font.pixelSize: Style.font.caption
                font.bold: selected
                MouseArea {
                  anchors.fill: parent
                  anchors.margins: -Style.space(3)
                  hoverEnabled: true
                  cursorShape: Qt.PointingHandCursor
                  onClicked: root.setScale(surfaceRow.surfaceId, scaleValue)
                }
              }
            }
          }
        }
      }
    }
  }
}
