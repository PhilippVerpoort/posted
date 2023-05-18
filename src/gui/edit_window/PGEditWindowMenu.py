from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar

from src.python.config.config import dataFormat

menuDict = {
    'file': {
        'name': 'File',
        'items': {
            'file:reload': {
                'name': '&Reload',
                'shortcut': 'Ctrl+R',
                'desc': 'Reload TED CSV file to get changes made in an external program',
            },
            'file:save': {
                'name': '&Save',
                'shortcut': 'Ctrl+S',
                'desc': 'Save changes made to the TED CSV file',
            },
            'file:close': {
                'name': '&Close',
                'shortcut': 'Ctrl+Q',
                'desc': 'Close this window',
            },
        }
    },
    'view': {
        'name': 'View',
        'items': {
            'view:consistency': {
                'name': 'Show &errors',
                'shortcut': 'Ctrl+Shift+T',
                'desc': 'Highlight data inconsistencies through cell colours',
                'checkable': True,
                'checked': True,
            },
        }
    },
}


class PGEditWindowMenu(QMenuBar):
    def __init__(self, main_window: 'PGEditWindow', parent=None):
        super(PGEditWindowMenu, self).__init__(parent)

        self.__mainWindow = main_window

        self.__setupUi()


    def __setupUi(self):
        menus = {}
        self._items = {}

        # add menu items from dict
        for menuID, menuSpecs in menuDict.items():
            menus[menuID] = self.addMenu(menuSpecs['name'])

            for itemID, itemSpecs in menuSpecs['items'].items():
                item = QAction(itemSpecs['name'], self)
                if 'shortcut' in itemSpecs: item.setShortcut(itemSpecs['shortcut'])
                if 'desc' in itemSpecs: item.setStatusTip(itemSpecs['desc'])
                if 'checkable' in itemSpecs: item.setCheckable(itemSpecs['checkable'])
                if 'checked' in itemSpecs: item.setChecked(itemSpecs['checked'])
                menus[menuID].addAction(item)

                self._items[itemID] = item

        # add submenu for viewing/hiding columns
        submenu = menus['view'].addMenu('Show &columns')
        submenu.setStatusTip('Select the columns to show/hide')
        for colID, colSpecs in dataFormat.items():
            item = QAction(colSpecs['name'], self)
            item.setCheckable(True)
            item.setChecked(True)
            submenu.addAction(item)

            self._items[f"view:columns:{colID}"] = item


    def getTriggerItems(self):
        return self._items
