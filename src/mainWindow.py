# mainWindow.py

from mainWindow_ui import Ui_MainWindow
import timecode as tc

from qtpy.QtCore import Qt, QEvent, Signal, Slot
from qtpy.QtWidgets import QMainWindow, QMenuBar
from db.trialWindow import TrialDockWidget

class MainWindow(QMainWindow):

    quitting = Signal()

    def __init__(self, bento):
        super().__init__()

        self.bento = bento
        self.flag = "close"
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.stepButton.clicked.connect(bento.incrementTime)
        self.ui.backButton.clicked.connect(bento.decrementTime)
        self.ui.ffButton.clicked.connect(bento.skipForward)
        self.ui.fbButton.clicked.connect(bento.skipBackward)
        self.ui.toStartButton.clicked.connect(bento.toStart)
        self.ui.toEndButton.clicked.connect(bento.toEnd)
        self.ui.nextButton.clicked.connect(bento.toNextEvent)
        self.ui.previousButton.clicked.connect(bento.toPrevEvent)
        self.ui.quitButton.clicked.connect(bento.quit)
        bento.quitting.connect(self.close)
        self.quitting.connect(bento.quit)

        self.ui.trialPushButton.clicked.connect(self.selectTrial)
        self.ui.playButton.clicked.connect(bento.player.togglePlayer)
        self.ui.halveFrameRateButton.clicked.connect(bento.player.halveFrameRate)
        self.ui.doubleFrameRateButton.clicked.connect(bento.player.doubleFrameRate)
        self.ui.oneXFrameRateButton.clicked.connect(bento.player.resetFrameRate)
        self.ui.annotationsView.set_bento(bento)
        self.ui.annotationsView.setScene(bento.annotationsScene)
        bento.annotationsScene.sceneRectChanged.connect(self.ui.annotationsView.update)
        self.ui.annotationsView.scale(10., self.ui.annotationsView.height())
        self.ui.annotationsView.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        bento.annotationsSceneHeightChanged.connect(self.ui.annotationsView.setVScaleAndShow)
        self.populateChannelsCombo()
        self.ui.channelComboBox.currentTextChanged.connect(bento.setActiveChannel)
        self.ui.newChannelPushButton.clicked.connect(bento.newChannel)

        # Keep keyboard focus on the main window: buttons/combo must not take
        # focus on click, otherwise arrow keys move focus between buttons
        # instead of scrolling time (QAbstractButton eats Left/Right/Up/Down).
        from qtpy.QtWidgets import QAbstractButton, QComboBox
        for w in self.findChildren(QAbstractButton) + self.findChildren(QComboBox):
            w.setFocusPolicy(Qt.NoFocus)
        self.ui.annotationsView.setFocusPolicy(Qt.NoFocus)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        # annotation label: clickable lines (see eventFilter)
        self.current_annots = []
        self.ui.annotLabel.installEventFilter(self)
        self.ui.annotLabel.setCursor(Qt.PointingHandCursor)

        # menus
        self.menuBar = QMenuBar(self)
        self.setMenuBar(self.menuBar)
        self.fileMenu = self.menuBar.addMenu("File")
        self.saveAnnotationsAction = self.fileMenu.addAction("Save Annotations...")
        self.saveAnnotationsAction.triggered.connect(bento.save_annotations)
        self.fileMenuSeparatorAction = self.fileMenu.addSeparator()
        self.setInvestigatorAction = self.fileMenu.addAction("Set Investigator...")
        self.setInvestigatorAction.triggered.connect(bento.set_investigator)
        self.importTrialsAction = self.fileMenu.addAction("Import Trials...")
        self.importTrialsAction.triggered.connect(bento.import_trials)
        self.importAnimalsAction = self.fileMenu.addAction("Import Animals (Tomomi)...")
        self.importAnimalsAction.triggered.connect(bento.import_animals_tomomi)

        self.dbMenu = self.menuBar.addMenu("Database")
        self.animalAction = self.dbMenu.addAction("Animal...")
        self.animalAction.triggered.connect(bento.edit_animal)
        self.investigatorAction = self.dbMenu.addAction("Investigator...")
        self.investigatorAction.triggered.connect(bento.edit_investigator)
        self.cameraAction = self.dbMenu.addAction("Camera...")
        self.cameraAction.triggered.connect(bento.edit_camera)
        self.separatorAction = self.dbMenu.addSeparator()
        self.configAction = self.dbMenu.addAction("Host Config...")
        self.configAction.triggered.connect(bento.edit_config)
        self.createDBAction = self.dbMenu.addAction("Create Database")
        self.createDBAction.triggered.connect(bento.create_db)

        self.channelMenu = self.menuBar.addMenu("Channel")
        self.newChannelAction = self.channelMenu.addAction("New Channel...")
        self.newChannelAction.triggered.connect(bento.newChannel)
        self.renameChannelAction = self.channelMenu.addAction("Rename Active Channel...")
        self.renameChannelAction.triggered.connect(bento.renameActiveChannel)
        self.channelMenu.addSeparator()
        self.copyChannelAction = self.channelMenu.addAction("Copy Channel Annotations")
        self.copyChannelAction.setShortcut("Ctrl+C")
        self.copyChannelAction.triggered.connect(bento.copyChannelAnnotations)
        self.pasteChannelAction = self.channelMenu.addAction("Paste Annotations (same times)")
        self.pasteChannelAction.setShortcut("Ctrl+V")
        self.pasteChannelAction.triggered.connect(bento.pasteChannelAnnotations)
        self.pasteChannelAtTimeAction = self.channelMenu.addAction("Paste Annotations at Current Time")
        self.pasteChannelAtTimeAction.setShortcut("Ctrl+Shift+V")
        self.pasteChannelAtTimeAction.triggered.connect(bento.pasteChannelAnnotationsAtCurrentTime)

        self.windowsMenu = self.menuBar.addMenu("Windows")
        self.toggleBehaviorVisibilityAction = self.windowsMenu.addAction("Show/Hide Behavior List")
        self.toggleBehaviorVisibilityAction.triggered.connect(bento.toggleBehaviorVisibility)

    def closeEvent(self, event):
        if event.type()==QEvent.Type.Close and self.flag=="close":
            self.bento.quit(event)
        else:
            pass
        event.accept()

    def wheelEvent(self, event):
        # mouse wheel anywhere over the main window scrolls time;
        # Alt + wheel zooms the annotations timeline
        if event.modifiers() & Qt.AltModifier:
            consumed = self.ui.annotationsView.zoom_time_scale(event)
        else:
            consumed = self.bento.wheel_time_step(event)
        if consumed:
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        if (event.modifiers() & Qt.ControlModifier) and Qt.Key_1 <= event.key() <= Qt.Key_9:
            # Ctrl+1..9: select channel by position
            self.bento.selectChannelByIndex(event.key() - Qt.Key_1)
            event.accept()
            return
        if event.key() == Qt.Key_Left:
            if event.modifiers() & Qt.ShiftModifier:
                self.bento.skipBackward()
            else:
                self.bento.decrementTime()
        elif event.key() == Qt.Key_Right:
            if event.modifiers() & Qt.ShiftModifier:
                self.bento.skipForward()
            else:
                self.bento.incrementTime()
        elif event.key() == Qt.Key_Up:
            if event.modifiers() & Qt.ShiftModifier:
                self.bento.player.doubleFrameRate()
            else:
                self.bento.toPrevEvent()
        elif event.key() == Qt.Key_Down:
            if event.modifiers() & Qt.ShiftModifier:
                self.bento.player.halveFrameRate()
            else:
                self.bento.toNextEvent()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.bento.selectBoutAtCursor()
        elif (event.key() == Qt.Key_Backspace and not self.bento.pending_bout
              and self.bento.reopenSelectedEdgeAtCursor()):
            # Backspace on an edge frame of the selected bout reopens that edge;
            # otherwise Backspace keeps its delete-hot-key meaning below
            pass
        elif (not (event.modifiers() & ~Qt.ShiftModifier)  # not a modifier other than shift
         and (event.key() in range(Qt.Key_A, Qt.Key_Z + 1) or
            event.key() == Qt.Key_Backspace or
            event.key() == Qt.Key_Escape)):
            self.bento.processHotKey(event)
        elif event.key() == Qt.Key_Space and self.bento.player:
            self.bento.player.togglePlayer()
        elif event.key() == Qt.Key_Delete:
            self.bento.deleteSelectedBout()
        event.accept()

    @Slot(tc.Timecode)
    def updateTime(self, t):
        self.ui.timeLabel.setText(f"{t} ({t.frame_number})")
        self.ui.annotationsView.updatePosition(t)
        self.show()

    @staticmethod
    def annotEntryText(a):
        """(chan, name, color, bout, is_selected) -> label line; selected bout is marked."""
        selected = len(a) > 4 and a[4]
        return ('▶ ' if selected else '') + a[0] + ': ' + a[1]

    @Slot(list)
    def updateAnnotLabel(self, annots):
        self.current_annots = list(annots)
        label = '\n'.join(self.annotEntryText(a) for a in annots)
        self.ui.annotLabel.setText(label)
        self.show()

    def eventFilter(self, obj, event):
        # click on a line of the annotation label selects that bout
        if (obj is self.ui.annotLabel and event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton and self.current_annots):
            line_h = max(1, self.ui.annotLabel.fontMetrics().lineSpacing())
            ix = int(event.pos().y() // line_h)
            if 0 <= ix < len(self.current_annots):
                self.bento.selectBoutFromLabel(self.current_annots[ix])
            return True
        return super().eventFilter(obj, event)

    @Slot()
    def selectTrial(self):
        self.bento.trialWindow = TrialDockWidget(self.bento)
        self.bento.trialWindow.show()

    def addChannelToCombo(self, chanName):
        if isinstance(chanName, list):
            for item in chanName:
                self.addChannelToCombo(item)
            return
        if not isinstance(chanName, str):
            raise RuntimeError("addChannelToCombo can only accept a string or list of strings")
        self.ui.channelComboBox.addItem(chanName)
        self.ui.channelComboBox.setCurrentText(chanName)

    def populateChannelsCombo(self):
        for chanName in self.bento.annotations.channel_names():
            self.ui.channelComboBox.addItem(chanName)

    def clearChannelsCombo(self):
        self.ui.channelComboBox.clear()

    def renameChannelInCombo(self, old, new):
        ix = self.ui.channelComboBox.findText(old)
        if ix >= 0:
            self.ui.channelComboBox.setItemText(ix, new)

    @Slot(str)
    def selectChannelByName(self, chanName):
        self.ui.channelComboBox.setCurrentText(chanName)