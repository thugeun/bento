import os, sys, tempfile, glob
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject
app = QApplication([])
import bento as B

b = B.Bento.__new__(B.Bento); QObject.__init__(b)
b.trial_id = 1; b.video_widgets = []; b.current_annot_path = None
b.trial_label = lambda: "20260923 m1 trial9 a10"
class MW:
    title = None
    def setWindowTitle(self, t): self.title = t
b.mainWindow = MW()

# updateWindowTitles tracks the open file
b.updateWindowTitles(r"C:\x\A11.annot"); assert b.current_annot_path == r"C:\x\A11.annot"
b.updateWindowTitles(None); assert b.current_annot_path is None

# backup_file_before_save: copy into <base>/_bento_autosave, prune to AUTOSAVE_KEEP
tmp = tempfile.mkdtemp()
annot = os.path.join(tmp, "A11.annot")
open(annot, "w").write("v1")
dst = B.Bento.backup_file_before_save(b, annot, tmp)
assert dst and os.path.isfile(dst) and os.path.dirname(dst) == os.path.join(tmp, B.AUTOSAVE_DIR), dst
assert os.path.basename(dst).startswith("A11_presave_") and open(dst).read() == "v1"
for i in range(B.AUTOSAVE_KEEP + 3):
    d = os.path.join(tmp, B.AUTOSAVE_DIR, f"A11_presave_2000010{i:02d}_000000.annot")
    open(d, "w").write("old")
B.Bento.backup_file_before_save(b, annot, tmp)
left = glob.glob(os.path.join(tmp, B.AUTOSAVE_DIR, "A11_presave_*.annot"))
assert len(left) == B.AUTOSAVE_KEEP, len(left)
# missing file / no folder -> None, no crash
assert B.Bento.backup_file_before_save(b, os.path.join(tmp, "nope.annot"), tmp) is None
assert B.Bento.backup_file_before_save(b, annot, "", []) is None
print("ctrls OK")
