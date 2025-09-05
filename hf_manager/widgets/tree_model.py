from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

class TreeModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_changed_callback = None

    def supportedDropActions(self):
        return Qt.MoveAction

    def dropMimeData(self, data, action, row, column, parent):
        if not data.hasFormat("application/x-qabstractitemmodeldatalist"):
            return False

        if action == Qt.IgnoreAction:
            return True

        # Get the destination item
        dest_item = self.itemFromIndex(parent)

        # We can only drop onto virtual folders or the root
        dest_data = None
        if dest_item:
            dest_data = dest_item.data(Qt.UserRole)

        if dest_data and dest_data.get("type") not in ["virtual_folder", "folder"]:
             # Cannot drop onto a file
            return False

        # Call the base class implementation to perform the move in the view
        result = super().dropMimeData(data, action, row, column, parent)

        # Now, update our underlying data model
        # The base class moves the item, we need to find out which one it was
        # and update its parent_uuid.
        # A simple way is to iterate and update all parent_uuids from the view state.
        if result and self.data_changed_callback:
            self.data_changed_callback()

        return result
