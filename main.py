import sys
from PySide6.QtWidgets import QApplication
from hf_manager.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Load and apply stylesheet
    try:
        with open("style.qss", "r") as f:
            style = f.read()
            app.setStyleSheet(style)
    except FileNotFoundError:
        print("Stylesheet 'style.qss' not found. Using default style.")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
