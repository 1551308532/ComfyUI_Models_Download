from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                               QDialogButtonBox, QLabel)

class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        self.settings = settings

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.root_dir_input = QLineEdit(self.settings.get("root_download_dir", "./downloads"))
        form_layout.addRow(QLabel("Root Download Directory:"), self.root_dir_input)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept(self):
        self.settings["root_download_dir"] = self.root_dir_input.text()
        super().accept()

    def get_settings(self):
        return self.settings
