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
  property var catalog: []
  property string fontName: ""
  property bool popupOpen: false
  property bool adding: false
  property string query: ""
  readonly property bool opened: popupOpen
  readonly property color fg: bar ? bar.foreground : Color.foreground
  readonly property string applyBin: Qt.resolvedUrl("scripts/apply.py").toString().replace("file://", "")
  readonly property var visibleCatalog: {
    var q = String(root.query || "").trim().toLowerCase()
    var out = []
    for (var i = 0; i < root.catalog.length; i++) {
      var row = root.catalog[i]
      if (!q || String(row.label).toLowerCase().indexOf(q) !== -1)
        out.push(row)
    }
    return out
  }

  function open() {
    popupOpen = true
    adding = false
    query = ""
  }
  function openFromHotkey() { open() }
  function close() {
    popupOpen = false
    adding = false
    query = ""
  }
  function toggle() {
    if (popupOpen) close()
    else open()
  }

  function triggerPress(button) {
    if (button === Qt.RightButton) return
    toggle()
  }

  function applyBinCmd(args) {
    var cmd = ["python3", root.applyBin]
    for (var i = 0; i < args.length; i++) cmd.push(args[i])
    Quickshell.execDetached(cmd)
    Qt.callLater(refresh)
  }

  function refresh() {
    if (!statusProc.running) statusProc.running = true
  }

  function refreshCatalog() {
    if (!catalogProc.running) catalogProc.running = true
  }

  function replaceConfig(next) {
    root.config = next
  }

  function setMaster(on) {
    var next = JSON.parse(JSON.stringify(root.config))
    next.enabled = on
    replaceConfig(next)
    applyBinCmd([on ? "enable" : "disable"])
  }

  function setEnabled(id, on) {
    var next = JSON.parse(JSON.stringify(root.config))
    for (var i = 0; i < next.apps.length; i++) {
      if (next.apps[i].id === id) next.apps[i].enabled = on
    }
    replaceConfig(next)
    applyBinCmd([on ? "enable" : "disable", id])
  }

  function setScale(id, scale) {
    var next = JSON.parse(JSON.stringify(root.config))
    for (var i = 0; i < next.apps.length; i++) {
      if (next.apps[i].id === id) next.apps[i].scale = scale
    }
    replaceConfig(next)
    applyBinCmd(["scale", id, String(scale)])
  }

  function addApp(desktop) {
    adding = false
    query = ""
    applyBinCmd(["add", desktop])
  }

  function removeApp(id) {
    var next = JSON.parse(JSON.stringify(root.config))
    next.apps = next.apps.filter(function (a) { return a.id !== id })
    replaceConfig(next)
    applyBinCmd(["remove", id])
  }

  function refreshApp(id) {
    applyBinCmd(["refresh", id])
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

  Process {
    id: statusProc
    command: ["python3", root.applyBin, "status"]
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

  Process {
    id: catalogProc
    command: ["python3", root.applyBin, "apps"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try {
          var data = JSON.parse(text)
          root.catalog = Array.isArray(data) ? data : []
        } catch (e) {
          root.catalog = []
        }
      }
    }
  }

  Timer {
    interval: 400
    running: root.popupOpen
    repeat: false
    onTriggered: root.refresh()
  }

  onPopupOpenChanged: {
    if (root.popupOpen) {
      root.adding = false
      root.query = ""
    }
  }

  onAddingChanged: {
    if (root.adding) root.refreshCatalog()
  }

  Component.onCompleted: refresh()

  PopupCard {
    id: popup
    anchorItem: root
    bar: root.bar
    owner: root
    open: root.popupOpen
    contentWidth: popup.fittedContentWidth(Style.space(360))
    contentHeight: popup.fittedContentHeight(Math.min(body.implicitHeight, Style.space(420)))

    Flickable {
      id: scroller
      width: parent.width
      height: parent.height
      implicitHeight: body.implicitHeight
      contentWidth: width
      contentHeight: body.implicitHeight
      clip: true
      boundsBehavior: Flickable.StopAtBounds
      interactive: body.implicitHeight > height

      Column {
        id: body
        width: scroller.width
        spacing: Style.space(8)

        Item {
          width: parent.width
          height: Math.max(titleLabel.implicitHeight, masterLabel.implicitHeight)

          Text {
            id: titleLabel
            text: "Type"
            color: root.fg
            font.family: root.bar ? root.bar.fontFamily : Style.font.family
            font.pixelSize: Style.font.subtitle
            font.bold: true
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
          }

          Text {
            id: masterLabel
            text: root.config.enabled ? "On" : "Off"
            color: root.fg
            font.family: root.bar ? root.bar.fontFamily : Style.font.family
            font.pixelSize: Style.font.body
            font.bold: root.config.enabled
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            MouseArea {
              anchors.fill: parent
              anchors.margins: -Style.space(4)
              cursorShape: Qt.PointingHandCursor
              Accessible.role: Accessible.Button
              Accessible.name: root.config.enabled ? "Disable Type" : "Enable Type"
              onClicked: root.setMaster(!root.config.enabled)
            }
          }
        }

        Repeater {
          model: root.config.apps

          Column {
            id: appRow
            required property var modelData
            readonly property string appId: modelData.id
            width: body.width
            spacing: Style.space(6)

            BorderSurface {
              width: parent.width
              implicitHeight: rowInner.implicitHeight + Style.space(12)
              radius: Style.cornerRadius
              color: rowMouse.containsMouse
                ? Style.hoverFillFor(root.fg, root.fg)
                : (appRow.modelData.enabled ? Style.normalFillFor(root.fg, root.fg) : "transparent")
              borderSpec: appRow.modelData.enabled
                ? Border.controlSpec("normal", root.fg, root.fg)
                : Border.none()

              MouseArea {
                id: rowMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                Accessible.role: Accessible.Button
                Accessible.name: (appRow.modelData.enabled ? "Disable " : "Enable ") + appRow.modelData.label
                onClicked: root.setEnabled(appRow.appId, !appRow.modelData.enabled)
              }

              Row {
                id: rowInner
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: Style.space(10)
                anchors.rightMargin: Style.space(10)
                spacing: Style.space(8)
                z: 1

                Text {
                  width: parent.width - toggleLabel.implicitWidth - removeMark.implicitWidth - Style.space(16)
                  text: appRow.modelData.label
                  color: root.fg
                  font.family: root.bar ? root.bar.fontFamily : Style.font.family
                  font.pixelSize: Style.font.body
                  elide: Text.ElideRight
                  anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                  id: toggleLabel
                  text: appRow.modelData.enabled ? "On" : "Off"
                  color: root.fg
                  font.family: root.bar ? root.bar.fontFamily : Style.font.family
                  font.pixelSize: Style.font.body
                  font.bold: appRow.modelData.enabled
                  anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                  id: removeMark
                  text: "×"
                  color: Qt.darker(root.fg, 1.35)
                  font.family: root.bar ? root.bar.fontFamily : Style.font.family
                  font.pixelSize: Style.font.body
                  anchors.verticalCenter: parent.verticalCenter
                  MouseArea {
                    anchors.fill: parent
                    anchors.margins: -Style.space(4)
                    cursorShape: Qt.PointingHandCursor
                    Accessible.role: Accessible.Button
                    Accessible.name: "Remove " + appRow.modelData.label
                    onClicked: root.removeApp(appRow.appId)
                  }
                }
              }
            }

            Row {
              width: parent.width
              spacing: Style.space(6)
              visible: appRow.modelData.enabled && root.config.enabled
              leftPadding: Style.space(10)

              Repeater {
                model: [0.8, 0.86, 0.92, 1.0, 1.08]

                Text {
                  required property var modelData
                  readonly property real scaleValue: Number(modelData)
                  readonly property bool selected: Math.abs(Number(appRow.modelData.scale) - scaleValue) < 0.01
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
                    onClicked: root.setScale(appRow.appId, scaleValue)
                  }
                }
              }

              Item { width: Style.space(6); height: 1 }

              Text {
                text: "Refresh"
                color: root.fg
                font.family: root.bar ? root.bar.fontFamily : Style.font.family
                font.pixelSize: Style.font.caption
                MouseArea {
                  anchors.fill: parent
                  anchors.margins: -Style.space(3)
                  hoverEnabled: true
                  cursorShape: Qt.PointingHandCursor
                  Accessible.role: Accessible.Button
                  Accessible.name: "Refresh " + appRow.modelData.label
                  onClicked: root.refreshApp(appRow.appId)
                }
              }
            }
          }
        }

        Column {
          width: parent.width
          spacing: Style.space(6)
          visible: root.adding

          TextField {
            id: searchField
            width: parent.width
            text: root.query
            foreground: root.fg
            font.family: root.bar ? root.bar.fontFamily : Style.font.family
            onTextChanged: root.query = text
            Keys.onEscapePressed: {
              root.adding = false
              root.query = ""
            }
          }

          Repeater {
            model: root.visibleCatalog

            BorderSurface {
              required property var modelData
              width: parent.width
              implicitHeight: addLabel.implicitHeight + Style.space(12)
              radius: Style.cornerRadius
              color: addMouse.containsMouse
                ? Style.hoverFillFor(root.fg, root.fg)
                : "transparent"
              borderSpec: Border.none()

              Text {
                id: addLabel
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: Style.space(10)
                anchors.rightMargin: Style.space(10)
                text: parent.modelData.label
                color: root.fg
                font.family: root.bar ? root.bar.fontFamily : Style.font.family
                font.pixelSize: Style.font.body
                elide: Text.ElideRight
              }

              MouseArea {
                id: addMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                Accessible.role: Accessible.Button
                Accessible.name: "Add " + parent.modelData.label
                onClicked: root.addApp(parent.modelData.desktop)
              }
            }
          }
        }

        Text {
          visible: !root.adding
          text: "Add"
          color: root.fg
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.body
          MouseArea {
            anchors.fill: parent
            anchors.margins: -Style.space(4)
            cursorShape: Qt.PointingHandCursor
            Accessible.role: Accessible.Button
            Accessible.name: "Add"
            onClicked: {
              root.adding = true
              Qt.callLater(function () { searchField.forceActiveFocus() })
            }
          }
        }
      }
    }
  }
}
