import os, sys, tempfile, contextlib
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import py_compile; py_compile.compile(r"D:\util\bento-0.2.1-beta\src\bento.py", doraise=True)
from qtpy.QtWidgets import QApplication
app = QApplication([])
import bento as B
from annot.annot import Annotations, Bout
from annot.behavior import Behaviors
from timecode import Timecode

tmp = tempfile.mkdtemp()
class Obj: pass
class FakeQuery:
    def __init__(self, obj): self.obj = obj
    def filter(self, *a): return self
    def one(self): return self.obj
    def one_or_none(self): return self.obj
class FakeSess:
    def __init__(self, trial, session): self.t, self.s = trial, session
    def query(self, cls):
        return FakeQuery({B.Trial: self.t, B.Session: self.s, B.Investigator: inv, B.Animal: ani}[cls])
    def __enter__(self): return self
    def __exit__(self, *a): return False
import datetime
trial = Obj(); trial.video_data = []; trial.stimulus = "toy mouse/A"; trial.trial_num = 3; trial.session_id = 1
sess = Obj(); sess.base_directory = tmp; sess.investigator_id = 1; sess.animal_id = 1
sess.experiment_date = datetime.date(2026, 10, 14)
inv = Obj(); inv.user_name = "thugeun"; ani = Obj(); ani.nickname = "2HM"

beh = Behaviors(); beh.load(open(os.path.expanduser("~/.bento/color_profiles.txt")))
ann = Annotations(beh)
ann.set_sample_rate(30.); ann.set_start_frame(0); ann.set_end_frame(1000)
ann.addEmptyChannel("Ch1")
ann.add_bout(Bout(Timecode(30., frames=10), Timecode(30., frames=20), beh.get("attack")), "Ch1")

b = Obj()
b.trial_id = 1; b.session_id = None; b.annotations = ann
b.db_sessionMaker = lambda: FakeSess(trial, sess)
b.autosave_dir = lambda base, vf=(): B.Bento.autosave_dir(b, base, vf)
b._safe_name = B.Bento._safe_name
b._trial_name_parts = lambda db: B.Bento._trial_name_parts(b, db)
b.autosave_dirty = False
assert B.Bento.autosave_annotations(b) is None, "not dirty -> no write"
assert B.Bento.autosave_annotations(b, force=True) is not None, "force writes"
b.autosave_dirty = True
fn = B.Bento.autosave_annotations(b)
assert fn and os.path.exists(fn), fn
assert os.path.basename(fn).startswith("thugeun_20261014_2HM_trial3_toy-mouse-A_autosave_"), fn
assert not b.autosave_dirty
txt = open(fn).read(); assert ">attack" in txt and "10\t20\t10" in txt, txt
# prune: create many
import time
for i in range(B.AUTOSAVE_KEEP + 3):
    open(os.path.join(os.path.dirname(fn), f"thugeun_20261014_2HM_trial3_toy-mouse-A_autosave_2000010{i:02d}_000000.annot"), "w").close()
b.autosave_dirty = True; B.Bento.autosave_annotations(b)
n = len([f for f in os.listdir(os.path.dirname(fn)) if f.startswith("thugeun_20261014_2HM_trial3_toy-mouse-A_autosave_")])
assert n == B.AUTOSAVE_KEEP, n
# fallback dir when base unwritable
assert B.Bento.autosave_dir(b, os.path.join(fn, "under_a_file")) is None
assert B.Bento.autosave_dir(b, "") is None
d = B.Bento.autosave_dir(b, "", [os.path.join(tmp, "vid.mp4")]); assert d == os.path.join(tmp, B.AUTOSAVE_DIR), d
trial.stimulus = None; sess.experiment_date = None; b.autosave_dirty = True
fn2 = B.Bento.autosave_annotations(b); assert os.path.basename(fn2).startswith("thugeun_2HM_trial3_autosave_"), fn2
print("OK", fn, "kept", n, "fallback", d)

# window titles
b.trial_label = lambda: B.Bento.trial_label(b)
from video.videoWindow import VideoFrame
class MW: pass
b.mainWindow = MW(); b.mainWindow.setWindowTitle = lambda t: setattr(b.mainWindow, "title", t)
v = VideoFrame.__new__(VideoFrame); from qtpy.QtWidgets import QFrame; QFrame.__init__(v)
v.video_path = None; v.title_prefix = ""
v.video_path = r"C:/x/260203_2HM_1WT_2303_seg5.mp4"; v.updateTitle()
b.video_widgets = [v]
trial.stimulus = "a10"; sess.experiment_date = datetime.date(2026, 9, 23)
B.Bento.updateWindowTitles(b, r"C:/y/A11.annot")
print("main:", b.mainWindow.title); print("video:", v.windowTitle())
assert b.mainWindow.title == "Bento - 20260923 2HM trial3 a10 - A11.annot", b.mainWindow.title
assert v.windowTitle() == "20260923 2HM trial3 a10 - 260203_2HM_1WT_2303_seg5.mp4"
B.Bento.updateWindowTitles(b, None); assert b.mainWindow.title.endswith("new annotations")
print("titles OK")
