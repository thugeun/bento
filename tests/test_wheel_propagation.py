import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import Qt, QPoint, QPointF, QObject, Signal
from qtpy.QtGui import QWheelEvent
app = QApplication([])
from video.videoWindow import VideoFrame
class FB(QObject):
    quitting = Signal()
    def __init__(self):
        super().__init__(); self.calls = []
        class V: zoom_time_scale = lambda s, e: self.calls.append("zoom") or True
        class U: annotationsView = V()
        class M: ui = U()
        self.mainWindow = M()
    def quit(self, *a): pass
    def wheel_time_step(self, e): self.calls.append("step"); return True
fb = FB(); vf = VideoFrame(fb); vf.show()
vp = vf.ui.videoView.viewport()
ev = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, 120), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
ev.ignore()   # Qt hands spontaneous events to the receiver un-accepted
app.sendEvent(vp, ev)
print("steps per wheel event in video window:", fb.calls.count("step"))
assert fb.calls.count("step") == 1, fb.calls
print("OK")
