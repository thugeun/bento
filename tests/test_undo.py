import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject, Qt
app = QApplication([])
import bento as B
from annot.annot import Annotations, Bout
from annot.behavior import Behaviors
from timecode import Timecode

beh = Behaviors(); beh.load(open(os.path.expanduser("~/.bento/color_profiles.txt")))
ann = Annotations(beh); ann.set_sample_rate(30.); ann.set_start_frame(0); ann.set_end_frame(3000)
ann.addEmptyChannel("1")
fr = 30.; T = lambda f: Timecode(fr, frames=f)
b = B.Bento.__new__(B.Bento); QObject.__init__(b)
b.annotations = ann; b.active_channels = ["1"]; b.behaviors = beh
b.time_start = T(0); b.time_end = T(3000); b.current_time = T(100)
b._selection = []; b.edge_drag = None; b.pending_bout = None; b.reopened_bout = None
b.current_annotations = []; b.newAnnotations = False; b.undo_stack = []; b.redo_stack = []
class Scene:
    chan_map = {}
    def sceneChanged(self, *a): pass
class SB:
    def showMessage(self, m, t=0): print("status:", m)
class MW:
    def statusBar(self): return SB()
b.annotationsScene = Scene(); b.mainWindow = MW()
b.noteAnnotationsChanged = lambda *a, **k: None
b.update_current_annotations = lambda: None
class Ev:
    def __init__(self, k, mods=Qt.NoModifier): self.k, self.m = k, mods
    def key(self): return self.k
    def modifiers(self): return self.m
ka, kr = ord('A'), ord('T')
state = lambda: [(x.start().frames, x.end().frames, x.name()) for x in ann.channel("1")]

B.Bento.processHotKey(b, Ev(ka)); b.set_time(T(130)); B.Bento.processHotKey(b, Ev(ka))
assert state() == [(100, 130, "attack")] and len(b.undo_stack) == 1
b.set_time(T(200)); B.Bento.processHotKey(b, Ev(kr)); b.set_time(T(230)); B.Bento.processHotKey(b, Ev(ka))  # chain
assert state() == [(100, 130, "attack"), (200, 229, "rest")] and b.pending_bout.name() == "attack"
B.Bento.processHotKey(b, Ev(Qt.Key_Escape))
# delete + undo + redo
b.select_bouts_in_range("1", T(100), T(230)); B.Bento.deleteSelectedBout(b); assert state() == []
B.Bento.undo(b); assert state() == [(100, 130, "attack"), (200, 229, "rest")], state()
B.Bento.redo(b); assert state() == []
B.Bento.undo(b)
# relabel + undo
b.select_bouts_in_range("1", T(100), T(130)); B.Bento.relabel_selected_bout(b, beh.get("chase"))
assert state()[0][2] == "chase"; B.Bento.undo(b); assert state()[0][2] == "attack"
# undo back through the chain and the first bout
B.Bento.undo(b); assert state() == [(100, 130, "attack")], state()
B.Bento.undo(b); assert state() == [], state()
B.Bento.undo(b)   # nothing to undo
B.Bento.redo(b); B.Bento.redo(b); assert state() == [(100, 130, "attack"), (200, 229, "rest")], state()
# edit after undo clears redo
B.Bento.undo(b); b.set_time(T(500)); B.Bento.processHotKey(b, Ev(kr)); b.set_time(T(520)); B.Bento.processHotKey(b, Ev(kr))
assert not b.redo_stack and state() == [(100, 130, "attack"), (500, 520, "rest")]
# reopen end edge of attack then press a different key: attack completes at the frame, new pending
b.select_bout("1", list(ann.channel("1"))[0]); B.Bento.reopen_bout_edge(b, "1", list(ann.channel("1"))[0], "end")
assert b.pending_bout and b.reopened_bout
b.set_time(T(150)); B.Bento.processHotKey(b, Ev(kr))
assert state()[0] == (100, 149, "attack") and b.pending_bout.name() == "rest" and b.current_time.frames == 150 and b.reopened_bout is None, state()
B.Bento.processHotKey(b, Ev(Qt.Key_Escape))
B.Bento.undo(b); assert state()[0] == (100, 130, "attack"), state()   # single undo step for the reopen edit
# edge drag + undo
b.select_bout("1", list(ann.channel("1"))[0]); assert b.begin_edge_drag("end"); B.Bento.drag_bout_edge(b, T(140)); B.Bento.end_edge_drag(b)
assert state()[0] == (100, 140, "attack"); B.Bento.undo(b); assert state()[0] == (100, 130, "attack")
print("undo OK")
