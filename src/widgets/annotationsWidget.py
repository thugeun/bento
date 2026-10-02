# annotationWidget.py
"""
"""

from qtpy.QtCore import Qt, QPointF, QRectF, Slot
from qtpy.QtGui import (QBrush, QPen, QKeyEvent, QMouseEvent,
    QTransform, QWheelEvent)
from qtpy.QtWidgets import QGraphicsScene, QGraphicsView
from timecode import Timecode

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
        self.scale_v = self.height()/v_factor
        self.setVScale(self.scale_v)
        self.show()

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
        if event.button() == Qt.LeftButton:
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
        Double-click on an edge of the *selected* bout (click it first to
        focus it): reopen that edge with the hot-key mechanism (hatched
        pending region that follows the current time, confirmed with the
        behavior's hot key, cancelled with Esc).  Double-clicks elsewhere
        do nothing.
        """
        assert self.bento
        self.skip_release = True
        if event.button() == Qt.LeftButton and self.bento.pending_bout:
            # pending state: double-click commits the bout at the clicked time
            # (same as pressing the behavior's hot key there)
            self.bento.set_time(self._time_at(event))
            self.bento.complete_pending_bout()
        elif event.button() == Qt.LeftButton and self.bento.selected_bout:
            edge = self._edge_under(event)
            if edge:
                chan, bout = self.bento.selected_bout
                self.bento.reopen_bout_edge(chan, bout, edge)
        event.accept()

    def mouseReleaseEvent(self, event):
        assert self.bento
        if self.skip_release:
            # release that follows a double-click: don't re-select
            self.skip_release = False
            self.dragging_edge = None
            event.accept()
            return
        if self.dragging_edge:
            self.bento.end_edge_drag()
            self.dragging_edge = None
        elif event.button() == Qt.LeftButton and not self.moved:
            # plain click: select the bout under the cursor (or clear selection)
            scene_pt = self.mapToScene(event.pos())
            chan = self.bento.channel_name_at_row(int(scene_pt.y()))
            bout = self.bento.bout_at(chan, self._time_at(event))
            self.bento.select_bout(chan, bout)
        event.accept()

    def maybeDrawSelection(self, painter, rect):
        sel = self.bento.selected_bout
        if not sel:
            return
        chan, bout = sel
        row = self.bento.channel_row(chan)
        if row is None:
            return
        pen = QPen(Qt.black)
        pen.setWidth(2)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(bout.start().float, float(row), bout.len().float, 1.))
        drag = self.bento.edge_drag
        if drag:
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
        painter.drawRect(QRectF(QPointF(bout.start().float, rect.top()), QPointF(now, rect.bottom())))
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
