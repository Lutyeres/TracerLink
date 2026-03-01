from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QTextEdit, QTabWidget, QLineEdit,
    QLabel, QFormLayout, QHBoxLayout,
    QDialog, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QIcon

from src.server.server import Server
from src.config import settings
from src.utils.logger import set_panel_callback


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowIcon(QIcon("TraceLink.ico"))
        self.setWindowTitle("TraceLink Server")
        self.resize(580, 500)

        self.server = Server()

        self.tabs = QTabWidget()
        self.tab_monitor = QWidget()
        self.tab_config = QWidget()

        self.tabs.addTab(self.tab_monitor, "Server Monitor")
        self.tabs.addTab(self.tab_config, "Configuração")

        self._config_tab_index = 1
        self._acesso_config_liberado = False

        self._build_monitor_tab()
        self._build_config_tab()

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

        set_panel_callback(self.append_log)

        # Intercepta clique na aba
        self.tabs.tabBar().installEventFilter(self)

        settings.carregar_config()
        self._carregar_campos()

        self._update_status(False)

    # ======================================================
    # MONITOR TAB
    # ======================================================

    def _build_monitor_tab(self):

        layout = QVBoxLayout()

        # Linha superior
        top_layout = QHBoxLayout()

        self.btn_start = QPushButton("Iniciar")
        self.btn_stop = QPushButton("Parar")

        self.btn_start.setFixedWidth(90)
        self.btn_stop.setFixedWidth(90)
        self.btn_stop.setEnabled(False)

        self.btn_start.clicked.connect(self._start_server)
        self.btn_stop.clicked.connect(self._stop_server)

        self.status_label = QLabel("Desconectado")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")

        top_layout.addWidget(self.btn_start)
        top_layout.addWidget(self.btn_stop)
        top_layout.addSpacing(20)
        top_layout.addWidget(self.status_label)
        top_layout.addStretch()

        self.monitor = QTextEdit()
        self.monitor.setReadOnly(True)

        layout.addLayout(top_layout)
        layout.addWidget(self.monitor)

        self.tab_monitor.setLayout(layout)

    # ======================================================
    # CONFIG TAB
    # ======================================================

    def _build_config_tab(self):

        main_layout = QVBoxLayout()
        form = QFormLayout()

        self.input_host = QLineEdit()
        self.input_endpoint = QLineEdit()
        self.input_ext = QLineEdit()
        self.input_poll = QLineEdit()
        self.input_pasta = QLineEdit()

        form.addRow("Host:", self.input_host)
        form.addRow("Endpoint:", self.input_endpoint)
        form.addRow("Extensão:", self.input_ext)
        form.addRow("Intervalo (s):", self.input_poll)
        form.addRow("Pasta:", self.input_pasta)

        main_layout.addLayout(form)

        # Botão salvar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_salvar = QPushButton("Salvar Config")
        self.btn_salvar.setFixedWidth(140)
        self.btn_salvar.clicked.connect(self._salvar_config)

        btn_layout.addWidget(self.btn_salvar)
        main_layout.addLayout(btn_layout)

        self.tab_config.setLayout(main_layout)

    # ======================================================
    # SERVER CONTROLE
    # ======================================================

    def _start_server(self):
        self.server.start()
        self._update_status(True)

    def _stop_server(self):
        self.server.stop()
        self._update_status(False)

    def _update_status(self, conectado: bool):

        if conectado:
            self.status_label.setText("Conectado")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
        else:
            self.status_label.setText("Desconectado")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

    def _salvar_config(self):

        host = self.input_host.text().strip()
        endpoint = self.input_endpoint.text().strip()
        ext = self.input_ext.text().strip()
        poll = self.input_poll.text().strip()
        pasta = self.input_pasta.text().strip()

        # Validação simples
        if not host:
            QMessageBox.critical(self, "Erro", "Host não pode ser vazio.")
            return

        try:
            poll = int(poll)
            if poll <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, "Erro", "Intervalo deve ser número maior que 0.")
            return

        try:
            settings.atualizar_config(
                host=host,
                endpoint=endpoint,
                ext=ext,
                poll_seconds=poll,
                pasta=pasta,
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
            return

        QMessageBox.information(self, "Sucesso", "Configuração salva com sucesso.")
        self.append_log("[CONFIG] Configuração salva.")
    # ======================================================
    # LOGIN CONFIG
    # ======================================================

    def _autenticar_configuracoes(self):

        dialog = LoginDialog(self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False

        if dialog.usuario == "admin" and dialog.senha == "superadmin":
            return True

        QMessageBox.critical(self, "Acesso negado", "Usuário ou senha inválidos.")
        return False

    # ======================================================
    # EVENT FILTER PARA ABA
    # ======================================================

    def eventFilter(self, watched, event):

        if watched is self.tabs.tabBar() and event.type() == QEvent.Type.MouseButtonPress:

            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            indice_clicado = self.tabs.tabBar().tabAt(pos)

            if indice_clicado == self._config_tab_index:

                # Sempre parar o server ao abrir config
                if self.server.is_running():
                    self.server.stop()
                    self._update_status(False)

                if self._autenticar_configuracoes():
                    self.tabs.setCurrentIndex(self._config_tab_index)

                return True

        return super().eventFilter(watched, event)

    # ======================================================
    # OUTROS
    # ======================================================

    def append_log(self, text):
        self.monitor.append(text)

    def _carregar_campos(self):
        self.input_host.setText(settings.get_host())
        self.input_endpoint.setText(settings.get_endpoint())
        self.input_ext.setText(settings.get_ext())
        self.input_poll.setText(str(settings.get_poll_seconds()))
        self.input_pasta.setText(settings.get_pasta())

    def closeEvent(self, event):
        self.server.stop()
        event.accept()


# ==========================================================
# LOGIN DIALOG
# ==========================================================

class LoginDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Login")
        self.setModal(True)

        self.usuario_input = QLineEdit()
        self.senha_input = QLineEdit()
        self.senha_input.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.addRow("Usuário:", self.usuario_input)
        form.addRow("Senha:", self.senha_input)

        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

        self.setFixedSize(self.sizeHint())

    @property
    def usuario(self):
        return self.usuario_input.text().strip()

    @property
    def senha(self):
        return self.senha_input.text()