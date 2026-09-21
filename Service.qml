import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

Item {
  id: root

  readonly property string pluginDir: Qt.resolvedUrl(".").toString().replace("file://", "").replace(/\/$/, "")

  function apply() {
    if (!applyProc.running) applyProc.running = true
  }

  IpcHandler {
    target: "payton.type"
    function apply(): string {
      root.apply()
      return "ok"
    }
  }

  Process {
    id: applyProc
    command: ["python3", root.pluginDir + "/scripts/apply.py", "apply"]
  }

  Component.onCompleted: apply()
}
