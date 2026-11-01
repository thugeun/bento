# annotationWidget.py
"""
"""

from qtpy.QtCore import Qt, QPointF, QRectF, Slot
from qtpy.QtGui import (QBrush, QColor, QIcon, QPen, QKeyEvent, QMouseEvent, QPixmap,
    QTransform, QWheelEvent)
from qtpy.QtWidgets import QGraphicsScene, QGraphicsView, QMenu
from timecode import Timecode

class HotKeyMenu(QMenu):
    """
    QMenu whose items can also be triggered by a single key while the menu is
    open (behavior hot keys for the relabel menu, Delete/Backspace for delete).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hot_keys = {}   # Qt.Key -> QAction

    def bind_hot_key(self, key, action):
        if isinstance(key, str):
            if not key:
                return
            key = getattr(Qt, 'Key_' + key.upper(), None)
            if key is None:
                return
        self._hot_keys[key] = action

    def keyPressEvent(self, event):
        act = self._hot_keys.get(event.key())
        if act is not None and act.isEnabled() and not (event.modifiers() & ~Qt.ShiftModifier):
            self.close()
            act.trigger()
            event.accept()
            return
        super().keyPressEvent(event)


class AnnotationsView(QGraphicsView):
    """
    AnnotationsView is a Qt viewer class that supports horizontal display
    of annotation bouts along a timeline.  The scale of the timeline and the
    position in time can be changed by pinch gestures and mouse drags respectively,
    as well as external input via setters.
    The annotation bouts themselves are represented in an AnnotationsScene, derived
    from QtGraphicsScene
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bento = None
        self.start_x = 0.
        self.scale_h = 1.
        self.scale_v = 10.
        #self.v_factor = self.height()
        self.scale(self.scale_v, self.scale_h)
        self.sample_rate = 30.
        self.time_x = Timecode(str(self.sample_rate), '0:0:0:1')
        self.horizontalScrollBar().sliderReleased.connect(self.updateFromScroll)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ticksScale = 1.
        self.press_pos = None
        self.moved = False
        self.dragging_edge = None
        self.skip_release = False
        self.band = None              # (row, t0, t1) while Ctrl+drag selects a time range
        self.ctrl_press = False
        self.setMouseTracking(True)   # needed for the hover cursor near bout edges
        self.setInteractive(False)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

    def set_bento(self, bento):
        self.bento = bento

    #def set_v_factor(self, v_factor):
    #    self.v_factor = self.height

    @Slot(Timecode)
    def updatePosition(self, t):
        pt = QPointF(t.float, self.scene().height/2.)
        self.centerOn(pt)
        self.show()

    def setTransformScale(self, t, scale_h: float=None, scale_v: float=None):
        if scale_h == None:
            scale_h = t.m11()
        if scale_v == None:
            scale_v = t.m22()
        t.setMatrix(
                scale_h,
                t.m12(),
                t.m13(),
                t.m21(),
                scale_v,
                t.m23(),
                t.m31(),
                t.m32(),
                t.m33()
            )
        self.setTransform(t, combine=False)

    def setScale(self, hScale: float, vScale: float) -> None:
        self.setTransformScale(self.transform(), scale_h=hScale, scale_v=vScale)

    def setHScale(self, hScale):
        self.setTransformScale(self.transform(), scale_h=hScale)

    def setVScale(self, vScale):
        self.setTransformScale(self.transform(), scale_v=vScale)

    @Slot(float)
    def setHScaleAndShow(self, hScale):
        self.scale_h = hScale
        self.setHScale(hScale)
        self.show()

    @Slot(float)
    def setVScaleAndShow(self, v_factor):
        self.v_factor = v_factor
        self.scale_v = self.height()/v_factor
        self.setVScale(self.scale_v)
        self.show()

    def resizeEvent(self, event):
        # keep every channel row filling the view's height when the window is
        # resized (the time scale is untouched), and stay centered on the time
        super().resizeEvent(event)
        if getattr(self, 'v_factor', None):
            self.scale_v = self.height() / self.v_factor
            self.setVScale(self.scale_v)
        if self.bento is not None:
            self.updatePosition(self.bento.get_time())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # Override the widget behavior on key strokes
        # to let the parent window handle the event
        event.ignore()

    # horizontal zoom (Alt + wheel): pixels per second of timeline
    ZOOM_FACTOR = 1.25
    MIN_H_SCALE = 0.2
    MAX_H_SCALE = 3000.
    TICK_STEPS = (0.1, 0.5, 1., 5., 10., 30., 60., 300., 600.)
    MIN_TICK_PX = 40.

    def zoom_time_scale(self, event: QWheelEvent) -> bool:
        """
        Alt + wheel: zoom the time axis around the current time.
        Wheel up zooms in.  Returns True if consumed.
        """
        delta = event.angleDelta()
        d = delta.y() if delta.y() != 0 else delta.x()   # Qt reports Alt+wheel as horizontal
        if d == 0:
            return False
        factor = self.ZOOM_FACTOR if d > 0 else 1. / self.ZOOM_FACTOR
        new_scale = min(self.MAX_H_SCALE, max(self.MIN_H_SCALE, self.transform().m11() * factor))
        self.setHScaleAndShow(new_scale)
        # keep tick marks readable: pick the smallest step that is >= MIN_TICK_PX wide
        self.ticksScale = next((s for s in self.TICK_STEPS if s * new_scale >= self.MIN_TICK_PX),
                               self.TICK_STEPS[-1])
        self.updatePosition(self.bento.get_time())
        self.viewport().update()
        return True

    def wheelEvent(self, event: QWheelEvent) -> None:
        # Override the widget behavior on wheel events:
        #   Alt + wheel  -> zoom the time axis
        #   wheel/swipe  -> scroll time (see Bento.wheel_time_step)
        if event.modifiers() & Qt.AltModifier:
            consumed = self.zoom_time_scale(event)
        else:
            consumed = self.bento.wheel_time_step(event)
        if consumed:
            event.accept()
        else:
            event.ignore()
        # super().wheelEvent(event)

    # Mouse interaction
    #   click on a bout            -> select it (outlined); click elsewhere -> deselect
    #   drag a selected bout edge  -> move its start/end (hatched preview), video follows
    #   drag anywhere else         -> scrub time (original behavior)
    #   Delete key                 -> delete selected bout (handled in MainWindow)

    EDGE_GRAB_PX = 6      # pixel tolerance for grabbing a bout edge
    CLICK_SLOP_PX = 4     # max mouse travel for a press/release to count as a click

    def _time_at(self, event):
        x = self.mapToScene(event.pos()).x()
        return Timecode(self.time_x.framerate, start_seconds=max(0., x))

    def _edge_under(self, event):
        """
        Return 'start' | 'end' if the cursor is within EDGE_GRAB_PX of a
        selected bout's edge (on the bout's channel row), else None.
        """
        sel = self.bento.selected_bout if self.bento else None
        if not sel:
            return None
        chan, bout = sel
        scene_pt = self.mapToScene(event.pos())
        row = self.bento.channel_row(chan)
        if row is None or not (row <= scene_pt.y() < row + 1.):
            return None
        tol = self.EDGE_GRAB_PX / max(self.transform().m11(), 1e-9)
        d_start = abs(scene_pt.x() - bout.start().float)
        d_end = abs(scene_pt.x() - (bout.start().float + bout.len().float))
        if min(d_start, d_end) > tol:
            return None
        return 'start' if d_start <= d_end else 'end'

    def _any_edge_under(self, event):
        """
        (chan, bout, 'start'|'end') for the bout edge closest to the cursor on
        the row under it, within EDGE_GRAB_PX, among visible bouts; else None.
        Unlike _edge_under this does not require the bout to be selected.
        """
        if not self.bento:
            return None
        scene_pt = self.mapToScene(event.pos())
        chan = self.bento.channel_name_at_row(int(scene_pt.y()))
        if chan is None or chan not in self.bento.annotations.channel_names():
            return None
        tol = self.EDGE_GRAB_PX / max(self.transform().m11(), 1e-9)
        fr = self.bento.get_time().framerate
        t0 = Timecode(fr, start_seconds=max(0., scene_pt.x() - tol))
        t1 = Timecode(fr, start_seconds=scene_pt.x() + tol)
        best = None
        for bout in self.bento.annotations.channel(chan).get_in_range(t0, t1):
            if not bout.is_visible():
                continue
            for edge, x in (('start', bout.start().float), ('end', bout.start().float + bout.len().float)):
                d = abs(scene_pt.x() - x)
                if d <= tol and (best is None or d < best[0]):
                    best = (d, chan, bout, edge)
        return best[1:] if best else None

    def mousePressEvent(self, event):
        assert isinstance(event, QMouseEvent)
        assert self.bento
        assert not self.transform().isRotating()
        self.scale_h = self.transform().m11()
        self.start_x = event.localPos().x() / self.scale_h
        self.press_pos = event.pos()
        self.moved = False
        self.time_x = self.bento.get_time()
        self.dragging_edge = None
        self.band = None
        self.ctrl_press = bool(event.modifiers() & Qt.ControlModifier)
        if event.button() == Qt.LeftButton and self.bento.player:
            # the mouse owns the time line until it is released; playback resumes then
            self.bento.player.suspend()
        if event.button() == Qt.LeftButton and not self.ctrl_press:
            edge = self._edge_under(event)
            if edge and self.bento.begin_edge_drag(edge):
                self.dragging_edge = edge
        event.accept()

    def mouseMoveEvent(self, event):
        assert isinstance(event, QMouseEvent)
        assert self.bento
        if not (event.buttons() & Qt.LeftButton):
            # hover: show a resize cursor near a selected bout's edge
            self.setCursor(Qt.SizeHorCursor if self._edge_under(event) else Qt.ArrowCursor)
            event.accept()
            return
        if (event.pos() - self.press_pos).manhattanLength() > self.CLICK_SLOP_PX:
            self.moved = True
        if self.ctrl_press:
            # Ctrl+drag: rubber-band time range on the row where the press happened
            if self.moved:
                row = int(self.mapToScene(self.press_pos).y())
                t0 = Timecode(self.time_x.framerate, start_seconds=max(0., self.mapToScene(self.press_pos).x()))
                self.band = (row, t0, self._time_at(event))
                self.viewport().update()
            event.accept()
            return
        if self.dragging_edge:
            # delta from the press point (scene units) keeps the drag stable
            # even if the view scrolls; the video follows on release
            dx = event.localPos().x() / self.scale_h - self.start_x
            orig = self.bento.edge_drag['orig'].float
            self.bento.drag_bout_edge(Timecode(self.time_x.framerate, start_seconds=max(0., orig + dx)))
        else:
            x = event.localPos().x() / self.scale_h
            self.bento.set_time(Timecode(
                self.time_x.framerate,
                start_seconds=self.time_x.float + (self.start_x - x)
            ))
        event.accept()

    def mouseDoubleClickEvent(self, event):
        """
        Double-click on an edge of any bout: reopen that edge with the hot-key
        mechanism (hatched pending region that follows the current time,
        confirmed with the behavior's hot key, cancelled with Esc).  While a
        bout is pending, a double-click commits it at the clicked time.
        Double-click away from any edge: jump to that time.
        """
        assert self.bento
        self.skip_release = True
        if event.button() == Qt.LeftButton and self.bento.pending_bout:
            # pending state: double-click commits the bout at the clicked time
            # (same as pressing the behavior's hot key there)
            self.bento.set_time(self._time_at(event))
            self.bento.complete_pending_bout()
        elif event.button() == Qt.LeftButton:
            hit = self._any_edge_under(event)
            if hit:
                chan, bout, edge = hit
                if self.dragging_edge:
                    # the first click of the double-click started an edge drag; drop it
                    self.bento.end_edge_drag()
                    self.dragging_edge = None
                self.bento.reopen_bout_edge(chan, bout, edge)
            else:
                # double-click away from any edge: jump the time there
                self.bento.set_time(self._time_at(event))
        event.accept()

    def mouseReleaseEvent(self, event):
        assert self.bento
        if self.skip_release:
            # release that follows a double-click: don't re-select
            self.skip_release = False
            self.dragging_edge = None
            if self.bento.player:
                self.bento.player.resume()
            event.accept()
            return
        if self.dragging_edge:
            self.bento.end_edge_drag()
            self.dragging_edge = None
        elif event.button() == Qt.LeftButton and self.ctrl_press and self.band:
            # Ctrl+drag: select every bout intersecting the band on that row
            row, t0, t1 = self.band
            self.band = None
            self.bento.select_bouts_in_range(self.bento.channel_name_at_row(row), t0, t1, extend=True)
        elif event.button() == Qt.LeftButton and not self.moved:
            scene_pt = self.mapToScene(event.pos())
            chan = self.bento.channel_name_at_row(int(scene_pt.y()))
            bout = self.bento.bout_at(chan, self._time_at(event))
            if self.ctrl_press:
                # Ctrl+click: add to / remove from the selection
                self.bento.toggle_bout_selection(chan, bout)
            else:
                # plain click: select the bout under the cursor (or clear selection)
                self.bento.select_bout(chan, bout)
        self.band = None
        self.ctrl_press = False
        if event.button() == Qt.LeftButton and self.bento.player:
            self.bento.player.resume()
        event.accept()

    def contextMenuEvent(self, event):
        """
        Right-click on a bout: select it and offer the active behaviors to
        relabel it with (color swatch + hot key shown).
        """
        assert self.bento
        scene_pt = self.mapToScene(event.pos())
        chan = self.bento.channel_name_at_row(int(scene_pt.y()))
        bout = self.bento.bout_at(chan, Timecode(self.time_x.framerate, start_seconds=max(0., scene_pt.x())))
        if bout is None:
            event.ignore()
            return
        self.bento.select_bout(chan, bout)
        menu = HotKeyMenu(self)
        title = menu.addAction(f"Relabel '{bout.name()}' as:")
        title.setEnabled(False)
        menu.addSeparator()
        for beh in self.bento.behaviors:
            if not beh.is_active() or beh is bout.behavior():
                continue
            pix = QPixmap(12, 12)
            pix.fill(beh.get_color())
            hk = beh.get_hot_key()
            label = f"{beh.get_name()}" + (f"   [{hk}]" if hk else "")
            act = menu.addAction(QIcon(pix), label)
            act.triggered.connect(lambda checked=False, b=beh: self.bento.relabel_selected_bout(b))
            if hk:
                menu.bind_hot_key(hk, act)
        menu.addSeparator()
        t_click = Timecode(self.time_x.framerate, start_seconds=max(0., scene_pt.x()))
        split_act = menu.addAction("Split bout here")
        split_act.setEnabled(bout.start() < t_click <= bout.end())
        split_act.triggered.connect(
            lambda checked=False, c=chan, b=bout, t=t_click: self.bento.split_bouts_at([(c, b)], t))
        del_act = menu.addAction("Delete bout")
        del_act.triggered.connect(self.bento.deleteSelectedBout)
        menu.bind_hot_key(Qt.Key_Delete, del_act)
        menu.bind_hot_key(Qt.Key_Backspace, del_act)
        menu.exec_(event.globalPos())
        event.accept()

    def maybeDrawSelection(self, painter, rect):
        if self.band:
            # Ctrl+drag rubber band
            row, t0, t1 = self.band
            x0, x1 = sorted((t0.float, t1.float))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 60)))
            painter.drawRect(QRectF(x0, float(row), x1 - x0, 1.))
        sel = self.bento.selected_bout
        if not sel:
            return
        pen = QPen(Qt.black)
        pen.setWidth(2)
        pen.setCosmetic(True)
        for chan, bout in self.bento.selected_bouts:
            row = self.bento.channel_row(chan)
            if row is None:
                continue
            sel_rect = QRectF(bout.start().float, float(row), bout.len().float, 1.)
            # repaint the selected bout in its own color so it sits on top of any
            # overlapping bouts in the same channel, then outline it
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(bout.color()))
            painter.drawRect(sel_rect)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(sel_rect)
        chan, bout = sel
        row = self.bento.channel_row(chan)
        drag = self.bento.edge_drag
        if drag and row is not None:
            # hatch the region between the edge's original and current position
            cur = bout.start().float if drag['edge'] == 'start' else bout.end().float
            brush = QBrush(bout.color(), bs=Qt.DiagCrossPattern)
            painterTransform = painter.transform()
            brush.setTransform(QTransform.fromScale(
                1./painterTransform.m11(), 1./painterTransform.m22()))
            painter.setBrush(brush)
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(QPointF(drag['orig'].float, float(row)), QPointF(cur, float(row) + 1.)))
            painter.setBrush(Qt.NoBrush)

    def updateFromScroll(self):
        assert self.bento
        center = self.viewport().rect().center()
        sceneCenter = self.mapToScene(center)
        self.bento.set_time(Timecode(
            self.time_x.framerate,
            start_seconds=sceneCenter.x()
        ))

    def maybeDrawPendingBout(self, painter, rect):
        bout = self.bento.pending_bout
        if not bout:
            return
        now = self.bento.get_time().float
        brush = QBrush(bout.color(), bs=Qt.DiagCrossPattern)
        painterTransform = painter.transform()
        brushTransform = QTransform.fromScale(
            1./painterTransform.m11(),
            1./painterTransform.m22())
        brush.setTransform(brushTransform)
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        # only the channel the bout will land in: a reopened bout's own channel,
        # otherwise the active channel (whole height if that is unknown)
        reopened = self.bento.reopened_bout
        chan = reopened[0] if reopened else (self.bento.active_channels[0] if self.bento.active_channels else None)
        row = self.bento.channel_row(chan) if chan is not None else None
        top, bottom = (float(row), float(row) + 1.) if row is not None else (rect.top(), rect.bottom())
        painter.drawRect(QRectF(QPointF(bout.start().float, top), QPointF(now, bottom)))
        painter.setBrush(Qt.NoBrush)

    def drawForeground(self, painter, rect):
        self.maybeDrawPendingBout(painter, rect)
        self.maybeDrawSelection(painter, rect)
        # draw current time indicator
        now = self.bento.get_time().float
        pen = QPen(Qt.black)
        pen.setWidth(0)
        painter.setPen(pen)
        painter.drawLine(
            QPointF(now, rect.top()),
            QPointF(now, rect.bottom())
            )
        # draw tick marks
        if self.scene().loaded:
            offset = self.ticksScale
            eighth = (rect.bottom() - rect.top()) / 8.
            eighthDown = rect.top() + eighth
            eighthUp = rect.bottom() - eighth
            while now + offset < rect.right():
                painter.drawLine(
                    QPointF(now + offset, rect.top()),
                    QPointF(now + offset, eighthDown)
                )
                painter.drawLine(
                    QPointF(now + offset, eighthUp),
                    QPointF(now + offset, rect.bottom())
                )
                painter.drawLine(
                    QPointF(now - offset, rect.top()),
                    QPointF(now - offset, eighthDown)
                )
                painter.drawLine(
                    QPointF(now - offset, eighthUp),
                    QPointF(now - offset, rect.bottom())
                )
                offset += self.ticksScale

class AnnotationsScene(QGraphicsScene):
    """
    AnnotationsScene is a class to contain annotation bouts for display in an
    AnnotationsView widget.  The horizontal axis is scaled in seconds, represented
    as a float, which can be produced directly by the timecode class.
    Multiple views of the AnnotationsScene can be supported, so that the annotation
    bouts can easily be shown against a variety of data, as well as separately in
    the main annotations view.
    """

    def __init__(self, sample_rate=30.):
        super().__init__()
        self.setBackgroundBrush(QBrush(Qt.white))
        self.height = 1.
        self.sample_rate = sample_rate
        self.chan_map = {}
        self.loaded = False

    def addBout(self, bout, chan):
        """
        Add a bout to the scene according to its timecode and channel name or number.
        """
        if isinstance(chan, int):
            chan_num = chan
        elif isinstance(chan, str):
            if chan not in self.chan_map.keys():
                self.chan_map[chan] = len(self.chan_map.keys()) # add the new channel
            chan_num = self.chan_map[chan]
        else:
            raise RuntimeError(f"addBout: expected int or str, but got {type(chan)}")
        color = bout.color
        self.addRect(bout.start().float, float(chan_num), bout.len().float, 1., QPen(QBrush(), 0, s=Qt.NoPen), QBrush(color()))
        self.loaded = True

    def loadAnnotations(self, annotations, activeChannels, sample_rate):
        self.setSampleRate(sample_rate)
        self.height = float(len(activeChannels))
        for ix, chan in enumerate(activeChannels):
            self.chan_map[chan] = ix
            channel = annotations.channel(chan)
            channel.set_top(float(ix))
            self.addItem(channel)
            # channel.contentChanged.connect(self.sceneChanged)
            # self.loadBouts(annotations.channel(chan),  ix)
        self.loaded = True

    def loadBouts(self, channel, chan_num):
        print(f"Loading bouts for channel {chan_num}")
        for bout in channel:
            self.addBout(bout, chan_num)

    def setSampleRate(self, sample_rate):
        self.sample_rate = sample_rate

    @Slot(float, float)
    def sceneChanged(self, start, end):
        self.invalidate(start, 0., end - start, self.height)
