from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QTableView, QMenu, QLineEdit, QInputDialog

from posted_gui.edit_window.PGTableModel import PGTableModel


class PGTableView(QTableView):
    def __init__(self, model: PGTableModel):
        super(PGTableView, self).__init__()
        self._model = model

        self.setModel(model)

        self.setAlternatingRowColors(True)
        self.setStyleSheet('alternate-background-color: grey;background-color: white;')

        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.__horizontalHeaderMenuPopup)

        self.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.verticalHeader().customContextMenuRequested.connect(self.__verticalHeaderMenuPopup)


    def __horizontalHeaderMenuPopup(self, pos):
        menu = QMenu()
        actionRename = QAction('Rename', self)
        menu.addAction(actionRename)
        actionDelete = QAction('Delete', self)
        menu.addAction(actionDelete)

        action = menu.exec_(self.mapToGlobal(pos))

        col = self.columnAt(pos.x())

        if action == actionRename:
            self.__updateCatKey(col)
        elif action == actionDelete:
            # TODO: Implement
            print("delete col", col)
            raise Exception("Not implemented yet!")


    def __verticalHeaderMenuPopup(self, pos):
        # list of actions
        actions = {
            'rnm': 'Rename',
            'hide': 'Hide',
            'dupl': 'Duplicate',
            'del': 'Delete',
        }

        # create and display context menu
        menu = QMenu()
        menuActions = {}
        for key, val in actions.items():
            menuActions[key] = QAction(val, self)
            menu.addAction(menuActions[key])

        action = menu.exec_(self.mapToGlobal(pos))

        rowEnd = self.rowAt(pos.y())

        # find triggered action
        try:
            selectedAction = next(key for key, a in menuActions.items() if a == action)
        except StopIteration:
            return

        # execute action
        if selectedAction == 'rnm':
            currentTitle = self._model.getRowTitle(rowEnd)
            newTitle, ok = QInputDialog().getText(self, 'Rename scenario', 'Title:', QLineEdit.Normal, currentTitle)
            if ok and newTitle:
                self._model.setRowTitle(rowEnd, newTitle)
        elif selectedAction == 'hide':
            self._model.hideRow(rowEnd)
        elif selectedAction == 'dupl':
            self._model.duplicateRow(rowEnd)
        elif selectedAction == 'del':
            self._model.deleteRow(rowEnd)

