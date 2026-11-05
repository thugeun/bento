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
ann.addEmptyChannel("1"); ann.addEmptyChannel("2")
fr = 30.
T = lambda f: Timecode(fr, frames=f)
def add(chan, s, e, name): ann.add_bout(Bout(T(s), T(e), beh.get(name)), chan)
add("1", 10, 20, "attack"); add("1", 30, 40, "rest"); add("1", 50, 60, "attack"); add("1", 100, 120, "chase")
add("2", 500, 510, "rest")

b = B.Bento.__new__(B.Bento); QObject.__init__(b)
b.annotations = ann; b.active_channels = ["1"]; b.behaviors = beh
b.time_start = T(0); b.time_end = T(3000); b.current_time = T(1000)
b._selection = []; b.edge_drag = None; b.pending_bout = None; b.reopened_bout = None
b.current_annotations = []; b.newAnnotations = False; b.undo_stack = []; b.redo_stack = []; b.bout_clipboard = []
class Scene:
    chan_map = {}
    def sceneChanged(self, *a): pass
b.annotationsScene = Scene()
b.noteAnnotationsChanged = lambda *a, **k: None
b.update_current_annotations = lambda: None
bouts = lambda c="1": list(ann.channel(c))

# toggle
b.toggle_bout_selection("1", bouts()[0]); b.toggle_bout_selection("1", bouts()[2])
assert len(b.selected_bouts) == 2 and b.selected_bout[1] is bouts()[2]
b.toggle_bout_selection("1", bouts()[0]); assert len(b.selected_bouts) == 1
b.toggle_bout_selection("2", bouts("2")[0]); assert b.selected_bouts == [("2", bouts("2")[0])], "other channel -> new selection"
# range
b.select_bouts_in_range("1", T(35), T(55)); assert [x[1] for x in b.selected_bouts] == bouts()[1:3]
b.select_bouts_in_range("1", T(0), T(15), extend=True); assert len(b.selected_bouts) == 3
# all
b.selectAllBoutsInActiveChannel(); assert len(b.selected_bouts) == 4
# copy selected (2 bouts) -> paste into same channel at current time
b.select_bouts_in_range("1", T(10), T(40))
B.Bento.copyChannelAnnotations(b); assert len(b.bout_clipboard) == 2 and b.clipboard_channel == "1"
B.Bento.pasteChannelAnnotations(b)
names = [(x.start().frames, x.end().frames, x.name()) for x in bouts()]
assert (1000, 1010, "attack") in names and (1020, 1030, "rest") in names, names
# paste into other channel keeps times
b.active_channels = ["2"]; B.Bento.pasteChannelAnnotations(b)
assert (10, 20, "attack") in [(x.start().frames, x.end().frames, x.name()) for x in bouts("2")]
b.active_channels = ["1"]
# Ctrl+C with nothing selected copies the whole channel
b.selected_bout = None; B.Bento.copyChannelAnnotations(b); assert len(b.bout_clipboard) == 6
# relabel multi: attack@10-20 & rest@30-40 -> chase; merged? no (gap 20-30). count
b.select_bouts_in_range("1", T(10), T(40)); B.Bento.relabel_selected_bout(b, beh.get("chase"))
assert [x.name() for x in bouts()[:2]] == ["chase", "chase"] and len(b.selected_bouts) == 2
# delete multi
n = len(bouts()); b.select_bouts_in_range("1", T(10), T(40)); B.Bento.deleteSelectedBout(b)
assert len(bouts()) == n - 2 and b.selected_bout is None and b.newAnnotations
print("multisel OK")
