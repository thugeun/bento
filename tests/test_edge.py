import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject, QPoint, QPointF, Qt
app = QApplication([])
import bento as B
from annot.annot import Annotations, Bout
from annot.behavior import Behaviors
from timecode import Timecode
from widgets.annotationsWidget import AnnotationsView, AnnotationsScene

beh = Behaviors(); beh.load(open(os.path.expanduser("~/.bento/color_profiles.txt")))
ann = Annotations(beh)
ann.set_sample_rate(30.); ann.set_start_frame(0); ann.set_end_frame(3000)
ann.addEmptyChannel("1")
fr = 30.
T = lambda f: Timecode(fr, frames=f)
def add(chan, s, e, name): ann.add_bout(Bout(T(s), T(e), beh.get(name)), chan)
add("1", 300, 600, "attack"); add("1", 900, 1200, "rest")

b = B.Bento.__new__(B.Bento); QObject.__init__(b)
b.annotations = ann; b.active_channels = ["1"]; b.behaviors = beh
b.time_start = T(0); b.time_end = T(3000); b.current_time = T(1500)
b._selection = []; b.edge_drag = None; b.pending_bout = None; b.reopened_bout = None
b.current_annotations = []; b.newAnnotations = False; b.undo_stack = []; b.redo_stack = []
b.annotationsScene = AnnotationsScene()
b.noteAnnotationsChanged = lambda *a, **k: None
b.update_current_annotations = lambda: None
b.get_time = lambda: b.current_time
bouts = lambda: list(ann.channel("1"))
attack = bouts()[0]

# 1. click on an edge without moving: no time jump, no undo entry
b.selected_bout = ("1", attack)
assert b.begin_edge_drag('end') and len(b.undo_stack) == 1
B.Bento.end_edge_drag(b)
assert b.current_time.frames == 1500 and b.undo_stack == [] and b.edge_drag is None
# real drag still jumps and keeps undo
assert b.begin_edge_drag('end'); B.Bento.drag_bout_edge(b, T(650)); B.Bento.end_edge_drag(b)
assert attack.end().frames == 650 and b.current_time.frames == 650 and len(b.undo_stack) == 1

# 2. _any_edge_under finds an unselected bout's edge
b.selected_bout = None
view = AnnotationsView(); view.set_bento(b); view.setScene(b.annotationsScene)
view.resize(600, 100); view.show(); app.processEvents()
view.resetTransform(); view.scale(10., 20.)   # 10 px / s, 20 px per channel row
b.channel_row = lambda chan: 0 if chan == "1" else None
b.channel_name_at_row = lambda row: "1" if row == 0 else None
class Ev:
    def __init__(self, pt): self._p = pt
    def pos(self): return self._p
def ev_at(seconds):
    return Ev(view.mapFromScene(QPointF(seconds, 0.5)))
hit = view._any_edge_under(ev_at(900 / 30.))          # rest start, 30 s
assert hit and hit[1] is bouts()[1] and hit[2] == 'start', hit
hit = view._any_edge_under(ev_at(650 / 30. + 0.2))    # attack end (21.67 s), 2 px off
assert hit and hit[1] is attack and hit[2] == 'end', hit
assert view._any_edge_under(ev_at(25.)) is None        # mid gap
assert view._any_edge_under(ev_at(15.)) is None        # mid bout
print("edge OK")
