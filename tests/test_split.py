import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject
app = QApplication([])
import bento as B
from annot.annot import Annotations, Bout
from annot.behavior import Behaviors
from timecode import Timecode

beh = Behaviors(); beh.load(open(os.path.expanduser("~/.bento/color_profiles.txt")))
ann = Annotations(beh)
ann.set_sample_rate(30.); ann.set_start_frame(0); ann.set_end_frame(3000)
ann.addEmptyChannel("1")
fr = 30.
T = lambda f: Timecode(fr, frames=f)
def add(chan, s, e, name): ann.add_bout(Bout(T(s), T(e), beh.get(name)), chan)
add("1", 100, 200, "attack"); add("1", 300, 400, "rest")

b = B.Bento.__new__(B.Bento); QObject.__init__(b)
b.annotations = ann; b.active_channels = ["1"]; b.behaviors = beh
b.time_start = T(0); b.time_end = T(3000); b.current_time = T(150)
b._selection = []; b.edge_drag = None; b.pending_bout = None; b.reopened_bout = None
b.current_annotations = []; b.newAnnotations = False; b.undo_stack = []; b.redo_stack = []
class Scene:
    chan_map = {}
    def sceneChanged(self, *a): pass
b.annotationsScene = Scene()
msgs = []
class SB:
    def showMessage(self, m, *a): msgs.append(m)
class MW:
    def statusBar(self): return SB()
b.mainWindow = MW()
b.noteAnnotationsChanged = lambda *a, **k: None
b.update_current_annotations = lambda: None
spans = lambda: sorted((x.start().frames, x.end().frames, x.name()) for x in ann.channel("1"))

# no selection -> bout under time line
B.Bento.splitSelectedBoutAtCursor(b)
assert spans() == [(100, 149, "attack"), (150, 200, "attack"), (300, 400, "rest")], spans()
assert b.selected_bout[1].start().frames == 150 and len(b.undo_stack) == 1 and b.newAnnotations
# split at first frame -> nothing
b.current_time = T(150); B.Bento.splitSelectedBoutAtCursor(b)
assert spans()[1] == (150, 200, "attack") and msgs[-1].startswith("Nothing")
# split at last frame -> [150,199] + [200,200]
b.current_time = T(200); B.Bento.splitSelectedBoutAtCursor(b)
assert (150, 199, "attack") in spans() and (200, 200, "attack") in spans()
# outside -> nothing
b.current_time = T(250); b.selected_bout = None; B.Bento.splitSelectedBoutAtCursor(b)
assert msgs[-1].startswith("Nothing")
# multi-selection: only bouts containing t split
b.selectAllBoutsInActiveChannel(); b.current_time = T(350)
n = len(spans()); B.Bento.splitSelectedBoutAtCursor(b)
assert len(spans()) == n + 1 and (300, 349, "rest") in spans() and b.selected_bouts[0][1].start().frames == 350
# undo
B.Bento.undo(b)
assert (300, 400, "rest") in spans()
B.Bento.redo(b)
assert (350, 400, "rest") in spans()
# context-menu path: split_bouts_at at an arbitrary time
bout = [x for x in ann.channel("1") if x.start().frames == 100][0]
assert B.Bento.split_bouts_at(b, [("1", bout)], T(120)) == 1 and (100, 119, "attack") in spans()
print("split OK")
