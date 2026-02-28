from PySide6.QtWidgets import QApplication
import sys

from src.ui.janela import MainWindow


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())