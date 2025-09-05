from PySide6.QtWidgets import (QDialog, QVBoxLayout, QListWidget, QListWidgetItem,
                               QPushButton, QDialogButtonBox, QCheckBox)
from PySide6.QtCore import Qt

class FolderSelectionDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Folder Contents")
        self.setGeometry(200, 200, 500, 400)

        self.items = items
        self.selected_items = []

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        for item in self.items:
            # item is a huggingface_hub.hf_api.RepoFile or RepoFolder object
            # We just need the path for display
            list_item = QListWidgetItem(item.path)
            list_item.setFlags(list_item.flags() | Qt.ItemIsUserCheckable)
            list_item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(list_item)

        layout.addWidget(self.list_widget)

        # Add "Add as single directory" checkbox
        self.add_as_dir_checkbox = QCheckBox("Add as a single directory (folder/*)")
        layout.addWidget(self.add_as_dir_checkbox)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept(self):
        if self.add_as_dir_checkbox.isChecked():
            # Special case: user wants to add the whole folder as one item
            self.selected_items = ["__all__"]
        else:
            self.selected_items = []
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    # Find the original item object from the path
                    original_item = next((x for x in self.items if x.path == item.text()), None)
                    if original_item:
                        self.selected_items.append(original_item)

        super().accept()

    def get_selected_items(self):
        return self.selected_items
