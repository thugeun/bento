import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject, QPointF, QRectF
from qtpy.QtGui import QColor, QImage, QPainter
app = QApplication([])
import bento as B
from video.videoWindow import VideoScene
from mainWindow import MainWindow
from timecode import Timecode

class Bout:
    def __init__(self, name, color): self._n, self._c = name, color
    def name(self): return self._n
    def color(self): return self._c
    def is_visible(self): return True
class Chan:
    def __init__(self, bouts): self.bouts = bouts
    def get_at(self, t): return self.bouts
class Annots:
    def __init__(self, chans): self.chans = chans
    def channel_names(self): return list(self.chans)
    def channel(self, c): return self.chans[c]

b = B.Bento.__new__(B.Bento); QObject.__init__(b)
rest, sniff, other = Bout("rest", QColor("gray")), Bout("sniff_face", QColor("red")), Bout("other", QColor("blue"))
b.annotations = Annots({"1": Chan([rest, sniff]), "2": Chan([]), "x": Chan([other])})
b.active_channels = ["2"]; b.current_time = Timecode("30.0", frames=100)
b.current_annotations = []; b.selected_bout = None; b._selection = []; b.edge_drag = None
b.noteAnnotationsChanged = lambda: None
seen = []
b.currentAnnotsChanged.connect(lambda v: seen.append(v))

# one line per channel, channel order, empty channel kept, active flag
b.update_current_annotations()
lines = seen[-1]
assert [l[0] for l in lines] == ["1", "2", "x"]
assert [l[1] for l in lines] == [False, True, False]
assert [e[1] for e in lines[0][2]] == ["rest", "sniff_face"] and lines[1][2] == []
assert b.current_annotations == [("1", rest), ("1", sniff), ("x", other)]

# main-window label: one table row per channel, marker cell only on the active channel
from qtpy.QtWidgets import QLabel
class NS: pass
mw = NS(); mw.ui = NS(); mw.ui.annotLabel = QLabel(); mw.show = lambda: None
mw.annotLineHtml = MainWindow.annotLineHtml
MainWindow.updateAnnotLabel(mw, lines)
html = mw.ui.annotLabel.text()
assert html.count("<tr>") == 3 and html.count("▶") == 1 and mw.annot_lines == lines
assert html.index("▶") > html.index("<tr>", html.index("<tr>") + 1)   # marker in row 2
txt = MainWindow.annotLineHtml(lines[0])
assert txt.startswith("1: ") and "rest" in txt and "sniff_face" in txt and "#ff0000" in txt
assert MainWindow.annotLineHtml(lines[1]) == "2: "

# line click cycles: first -> next -> clear
B.Bento.selectBoutFromLabelLine(b, lines[0][2]); assert b.selected_bout == ("1", rest)
b.update_current_annotations(); B.Bento.selectBoutFromLabelLine(b, seen[-1][0][2]); assert b.selected_bout == ("1", sniff)
b.update_current_annotations(); B.Bento.selectBoutFromLabelLine(b, seen[-1][0][2]); assert b.selected_bout is None
B.Bento.selectBoutFromLabelLine(b, [])   # empty line: no-op

# video overlay renders without overlap: one hit box per bout, rows strictly below each other
scene = VideoScene(); scene.setAnnots(lines)
img = QImage(400, 200, QImage.Format_ARGB32); img.fill(0)
p = QPainter(img); scene.drawForeground(p, QRectF(0, 0, 400, 200)); p.end()
boxes = scene.annot_bounds
assert [e[1] for _, e in boxes] == ["rest", "sniff_face", "other"]
r_rest, r_sniff, r_other = [r for r, _ in boxes]
assert r_rest.top() == r_sniff.top() and r_sniff.left() > r_rest.right()        # same line, side by side
assert r_other.top() >= r_rest.bottom() + 1 + (r_rest.height() - 1)             # skipped the empty row "2"
assert scene.annotAt(QPointF(r_sniff.center()))[1] == "sniff_face" and scene.annotAt(QPointF(1, 199)) is None
print("labels OK")
