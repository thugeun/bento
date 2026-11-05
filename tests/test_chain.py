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
b.annotationsScene = Scene()
b.noteAnnotationsChanged = lambda *a, **k: None
b.update_current_annotations = lambda: None
class Ev:
    def __init__(self, k, mods=Qt.NoModifier): self.k, self.m = k, mods
    def key(self): return self.k
    def modifiers(self): return self.m
keys = {bh.get_name(): bh.get_hot_key() for bh in beh if bh.get_hot_key()}
print({k: keys[k] for k in ("attack", "rest") if k in keys})
ka, kr = ord(keys["attack"].upper()), ord(keys["rest"].upper())
B.Bento.processHotKey(b, Ev(ka)); assert b.pending_bout.name() == "attack"
b.set_time(T(130))
B.Bento.processHotKey(b, Ev(kr))          # different key: close attack 100-130, rest pending at 131
bouts = [(x.start().frames, x.end().frames, x.name()) for x in ann.channel("1")]
assert bouts == [(100, 129, "attack")], bouts
assert b.pending_bout.name() == "rest" and b.pending_bout.start().frames == 130 and b.current_time.frames == 130
b.set_time(T(160)); B.Bento.processHotKey(b, Ev(kr))   # same key completes
bouts = [(x.start().frames, x.end().frames, x.name()) for x in ann.channel("1")]
assert bouts == [(100, 129, "attack"), (130, 160, "rest")], bouts
assert b.pending_bout is None
# reverse direction: pending at 300, go back to 250, press attack -> rest 250-300, attack pending at 249
b.set_time(T(300)); B.Bento.processHotKey(b, Ev(kr)); b.set_time(T(250)); B.Bento.processHotKey(b, Ev(ka))
bouts = [(x.start().frames, x.end().frames, x.name()) for x in ann.channel("1")]
assert (251, 300, "rest") in bouts and b.pending_bout.name() == "attack" and b.pending_bout.start().frames == 250 and b.current_time.frames == 250, (bouts, b.current_time.frames)
# Esc cancels
B.Bento.processHotKey(b, Ev(Qt.Key_Escape)); assert b.pending_bout is None
# Backspace(delete) pending then other key: deletion applied up to frame, new pending
b.set_time(T(110)); B.Bento.processHotKey(b, Ev(Qt.Key_Backspace)); b.set_time(T(120)); B.Bento.processHotKey(b, Ev(kr))
bouts = [(x.start().frames, x.end().frames, x.name()) for x in ann.channel("1")]
print(bouts); assert b.pending_bout.name() == "rest" and b.current_time.frames == 120 and bouts[:2] == [(100, 110, "attack"), (119, 129, "attack")], bouts
# same frame as pending start: nothing closed, new pending
B.Bento.processHotKey(b, Ev(Qt.Key_Escape)); b.set_time(T(600)); B.Bento.processHotKey(b, Ev(ka)); B.Bento.processHotKey(b, Ev(kr))
assert b.pending_bout.name() == "rest" and not any(x.start().frames == 600 for x in ann.channel("1"))
print("chain OK")
