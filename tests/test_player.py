import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject
app = QApplication([])
import bento as B

class Stub(QObject):
    def __init__(self):
        super().__init__(); self.t = 100
    def incrementTime(self): self.t += 1
    def decrementTime(self): self.t -= 1
b = Stub()
p = B.Player(b)
p.togglePlayer(); assert p.playing and p.direction == 1 and p.timer.isActive()
p._tick(); assert b.t == 101
p.toggleReverse(); assert p.playing and p.direction == -1 and p.timer.isActive()   # switch, not stop
p._tick(); assert b.t == 100
p.toggleReverse(); assert not p.playing and not p.timer.isActive()                  # same again -> stop
p.togglePlayer(); p.togglePlayer(); assert not p.playing
# suspend / resume only while playing
p.suspend(); p.resume(); assert not p.playing and not p.timer.isActive()
p.play(-1); p.suspend(); assert p.playing and p.suspended and not p.timer.isActive()
p.suspend(); p.resume(); assert p.playing and not p.suspended and p.timer.isActive() and p.direction == -1
p.stop(); assert not p.suspended
print("player OK")
