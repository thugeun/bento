import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject
app = QApplication([])
import bento as B

class Stub(QObject):
    def incrementTime(self): pass
    def decrementTime(self): pass
p = B.Player(Stub())
seen = []
p.speedChanged.connect(lambda v: seen.append(v))
assert p.speed() == 1.
p.doubleFrameRate(); assert p.speed() == 1.5
p.doubleFrameRate(); assert p.speed() == 2.
p.halveFrameRate(); p.halveFrameRate(); p.halveFrameRate(); assert p.speed() == 0.5
p.halveFrameRate(); assert p.speed() == 0.5           # floor
for _ in range(20): p.doubleFrameRate()
assert p.speed() == 8.                                # ceiling
p.set_speed(1.3); assert p.speed() == 1.5             # snapped to the 0.5 grid
p.resetFrameRate(); assert p.speed() == 1. and seen[-1] == 1.
assert abs(p.timer.interval() - 1000/30) <= 1
p.set_speed(2.); assert abs(p.timer.interval() - 1000/60) <= 1
print("speed OK")
