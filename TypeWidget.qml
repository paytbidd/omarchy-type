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
    text: "Aa"
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
      spacing: Style.space(10)

      Column {
        width: parent.width
        spacing: Style.space(2)
        Text {
          text: "Omarchy Type"
          color: root.fg
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.subtitle
          font.bold: true
        }
        Text {
          width: parent.width
          wrapMode: Text.WordWrap
          text: root.fontName !== "" ? ("Font: " + root.fontName) : "Uses the current Omarchy font."
          color: Qt.darker(root.fg, 1.4)
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.caption
        }
      }

      Repeater {
        model: Model.SURFACES

        Column {
          id: surfaceRow
          required property var modelData
          readonly property string surfaceId: modelData.id
          width: body.width
          spacing: Style.space(4)

          Row {
            width: parent.width
            spacing: Style.space(8)

            Text {
              width: parent.width - includeSwitch.width - Style.space(8)
              anchors.verticalCenter: parent.verticalCenter
              text: modelData.label
              color: root.fg
              font.family: root.bar ? root.bar.fontFamily : Style.font.family
              font.pixelSize: Style.font.body
              elide: Text.ElideRight
            }

            Text {
              id: includeSwitch
              readonly property bool on: !!(root.config.surfaces[modelData.id] && root.config.surfaces[modelData.id].enabled)
              text: on ? "On" : "Off"
              color: root.fg
              font.family: root.bar ? root.bar.fontFamily : Style.font.family
              font.pixelSize: Style.font.body
              font.bold: on
              anchors.verticalCenter: parent.verticalCenter
              Accessible.role: Accessible.Button
              Accessible.name: (on ? "Disable " : "Enable ") + modelData.label
              MouseArea {
                anchors.fill: parent
                anchors.margins: -Style.space(4)
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.setEnabled(modelData.id, !includeSwitch.on)
              }
            }
          }

          Text {
            width: parent.width
            wrapMode: Text.WordWrap
            text: modelData.description
            color: Qt.darker(root.fg, 1.5)
            font.family: root.bar ? root.bar.fontFamily : Style.font.family
            font.pixelSize: Style.font.caption
          }

          Row {
            width: parent.width
            spacing: Style.space(8)
            visible: includeSwitch.on

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
                color: selected ? root.fg : Qt.darker(root.fg, 1.5)
                font.family: root.bar ? root.bar.fontFamily : Style.font.family
                font.pixelSize: Style.font.caption
                font.bold: selected
                MouseArea {
                  anchors.fill: parent
                  anchors.margins: -Style.space(2)
                  hoverEnabled: true
                  cursorShape: Qt.PointingHandCursor
                  onClicked: root.setScale(surfaceRow.surfaceId, scaleValue)
                }
              }
            }
          }
        }
      }

      Text {
        width: parent.width
        wrapMode: Text.WordWrap
        text: "Reopen a webapp to pick up Chromium extension changes. Grok Bot applies on the next launch."
        color: Qt.darker(root.fg, 1.6)
        font.family: root.bar ? root.bar.fontFamily : Style.font.family
        font.pixelSize: Style.font.caption
      }
    }
  }
}
