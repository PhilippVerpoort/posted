import re
from functools import partial

from PySide6 import QtWidgets
from PySide6.QtWidgets import QApplication

from posted_gui.edit_window.PGEditWindowMenu import PGEditWindowMenu
from posted_gui.edit_window.PGTableModel import PGTableModel
from posted_gui.edit_window.PGTableView import PGTableView
from posted.path import pathOfTEDFile


class PGEditWindow(QtWidgets.QMainWindow):
    def __init__(self, app: QApplication, tid: str):
        # super constructor
        super(PGEditWindow, self).__init__(parent=None)

        # store arguments
        self._tid = tid
        self._app = app

        # add models
        self._tableModel = PGTableModel(self._tid, pathOfTEDFile(self._tid))

        # setup window
        self._setupWindow(self._app, self._tid)

        # create UI
        self._createUi()

        # attach main menu triggers
        self._attachTriggers()

        # initially load data from file
        self._load()


    def _setupWindow(self, app: QApplication, tid: str):
        # set style
        self.setWindowTitle(f"POSTED GUI — TED Editor: {tid}")

        #app.setStyle(QStyleFactory.create('Fusion'))
        self.originalPalette = app.palette()

        size = app.primaryScreen().size()
        height = size.height()
        width = size.width()
        self.setGeometry(.1*width, .1*height, .8*width, .8*height)
        self.showMaximized()


    def _createUi(self):
        # set main menu
        self._mainMenu = PGEditWindowMenu(self)
        self.setMenuBar(self._mainMenu)
        # self.__setupMainMenuTriggers()

        # set main table widget
        t = PGTableView(self._tableModel)
        self.setCentralWidget(t)


    def _attachTriggers(self):
        trigItems = self._mainMenu.getTriggerItems()

        trigItems['file:reload'].triggered.connect(self._load)
        trigItems['file:save'].triggered.connect(self._save)
        trigItems['file:close'].triggered.connect(self._close)

        trigItems['view:consistency'].triggered.connect(self._toggleViewConsistency)

        for itemID, itemObj in trigItems.items():
            if itemID.startswith('view:columns:'):
                colID = re.match(r'^view:columns:([^:]*)$', itemID).group(1)
                itemObj.triggered.connect(partial(self._toggleViewColumn, colID))


    def _load(self):
        self._tableModel.load()


    def _save(self):
        self._tableModel.save()


    def _close(self):
        self.close()


    def _toggleViewConsistency(self):
        self._tableModel.toggleViewConsistency()


    def _toggleViewColumn(self, colID: str):
        self._tableModel.toggleViewColumn(colID)
