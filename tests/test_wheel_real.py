# Real Windows wheel input into a VideoFrame vs an AnnotationsView-like main window.
import os, sys, ctypes, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from qtpy.QtWidgets import QApplication, QMainWindow
from qtpy.QtCore import Qt, QObject, Signal, QTimer, QPoint
app = QApplication([])
from video.videoWindow import VideoFrame
from widgets.annotationsWidget import AnnotationsView
class FB(QObject):
    quitting = Signal()
    def __init__(self):
        super().__init__(); self.calls = []
        class V: zoom_time_scale = lambda s, e: self.calls.append("zoom") or True
        class U: annotationsView = V()
        class M: ui = U()
        self.mainWindow = M()
    def quit(self, *a): pass
    def wheel_time_step(self, e): self.calls.append(("step", e.angleDelta().y(), int(e.phase()))); return True
fb = FB()
vf = VideoFrame(fb); vf.setWindowTitle("wheel test video"); vf.resize(300, 300); vf.move(50, 50); vf.show()
mw = QMainWindow(); av = AnnotationsView(mw); av.set_bento(fb); mw.setCentralWidget(av); mw.resize(300, 300); mw.move(400, 50); mw.show()
u = ctypes.windll.user32
old = ctypes.wintypes.POINT() if hasattr(ctypes, 'wintypes') else None
import ctypes.wintypes as wt
old = wt.POINT(); u.GetCursorPos(ctypes.byref(old))
def wheel_at(x, y, n):
    u.SetCursorPos(x, y); app.processEvents(); time.sleep(0.2)
    for _ in range(n):
        u.mouse_event(0x0800, 0, 0, -120, 0); time.sleep(0.15); app.processEvents()
    time.sleep(0.3); app.processEvents()
def run():
    app.processEvents(); time.sleep(0.5)
    g = vf.ui.videoView.viewport().mapToGlobal(QPoint(100, 100)); fb.calls.clear(); wheel_at(g.x(), g.y(), 3)
    print("video window: 3 ticks ->", len(fb.calls), "steps", fb.calls)
    g = av.viewport().mapToGlobal(QPoint(100, 100)); fb.calls.clear(); wheel_at(g.x(), g.y(), 3)
    print("annotations view: 3 ticks ->", len(fb.calls), "steps", fb.calls)
    u.SetCursorPos(old.x, old.y); app.quit()
QTimer.singleShot(800, run); app.exec_()
