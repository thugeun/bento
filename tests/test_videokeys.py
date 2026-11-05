import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject, Qt, QEvent, Signal
from qtpy.QtGui import QKeyEvent
app = QApplication([])
from video.videoWindow import VideoFrame

got = []
class MW:
    def keyPressEvent(self, ev): got.append((ev.key(), int(ev.modifiers())))
class StubBento(QObject):
    quitting = Signal()
    def __init__(self):
        super().__init__(); self.mainWindow = MW()
    def quit(self): pass
vf = VideoFrame(StubBento())
for key, mod in [(Qt.Key_A, Qt.NoModifier), (Qt.Key_Delete, Qt.NoModifier), (Qt.Key_Return, Qt.NoModifier),
                 (Qt.Key_Backspace, Qt.NoModifier), (Qt.Key_Escape, Qt.NoModifier), (Qt.Key_3, Qt.ControlModifier),
                 (Qt.Key_Left, Qt.ShiftModifier)]:
    app.sendEvent(vf, QKeyEvent(QEvent.KeyPress, key, mod))
assert [k for k, _ in got] == [Qt.Key_A, Qt.Key_Delete, Qt.Key_Return, Qt.Key_Backspace, Qt.Key_Escape, Qt.Key_3, Qt.Key_Left], got
assert got[5][1] == int(Qt.ControlModifier) and got[6][1] == int(Qt.ShiftModifier)
assert vf.ui.showPoseCheckBox.focusPolicy() == Qt.NoFocus and vf.focusPolicy() == Qt.StrongFocus
print("videokeys OK")
