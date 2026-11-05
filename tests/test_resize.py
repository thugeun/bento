import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from unittest.mock import MagicMock
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject, Signal
app = QApplication([])
from widgets.annotationsWidget import AnnotationsScene
from timecode import Timecode
import mainWindow as M

class Sig(QObject):
    quitting = Signal(); annotationsSceneHeightChanged = Signal(float); timeChanged = Signal(object)
sig = Sig()
bento = MagicMock()
bento.quitting = sig.quitting
bento.annotationsSceneHeightChanged = sig.annotationsSceneHeightChanged
bento.annotationsScene = AnnotationsScene()
bento.player.SPEED_STEP = 1.5
bento.annotations.channel_names.return_value = []
bento.get_time.return_value = Timecode(30., frames=100)
w = M.MainWindow(bento)
w.show(); app.processEvents()
assert w.maximumSize().width() > 10000, w.maximumSize()
h0 = w.ui.annotationsView.height()
w.resize(1000, 700); app.processEvents()
assert w.width() == 1000 and w.height() == 700, (w.width(), w.height())
h1 = w.ui.annotationsView.height()
assert h1 - h0 > 300, (h0, h1)   # extra height went to the annotations view
assert w.ui.timeLabel.height() < 60 and w.ui.playButton.height() < 60
# vertical scale follows the view height, horizontal scale untouched
v = w.ui.annotationsView
hs = v.transform().m11()
v.setVScaleAndShow(3.)
assert abs(v.transform().m22() - v.height() / 3.) < 1e-6
w.resize(1000, 900); app.processEvents()
assert abs(v.transform().m22() - v.height() / 3.) < 1e-6 and v.transform().m11() == hs
print("resize OK", h0, h1)
