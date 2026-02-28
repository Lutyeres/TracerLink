from pathlib import Path

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import (
    get_parametros_host,
    get_parametros_pasta,
    get_parametros_ext,
    _get_parametros,
    salvar_config,
)
from src.infrastructure.repository.os_repository import carregar
from src.log.logger_gui import fila_logs, log
from src.service.bot_service import RoboService
from src.service.config_service import validar_caminhos


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # self.setWindowIcon(QIcon("ObserverBotIcon.ico"))
        self.setWindowTitle("GetTess Server")
        self.resize(580, 500)

        self.robo = RoboService()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._build_monitoramento_tab()
        self._build_historico_tab()
        self._build_config_tab()

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._troca_programatica = False
        self._ultimo_indice = 0
        self._acesso_config_liberado = False
        self.tabs.tabBar().installEventFilter(self)

        self._carregar_config_campos()
        self._atualizar_historico()

        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self._processar_fila_logs)
        self.log_timer.start(300)

    def _build_monitoramento_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        controls = QHBoxLayout()

        self.btn_iniciar = QPushButton("Iniciar")
        self.btn_iniciar.clicked.connect(self._iniciar_robo)
        controls.addWidget(self.btn_iniciar)

        self.btn_parar = QPushButton("Parar")
        self.btn_parar.clicked.connect(self._parar_robo)
        controls.addWidget(self.btn_parar)

        controls.addSpacing(16)
        controls.addWidget(QLabel("Status atual:"))

        self.lbl_status = QLabel("Inativo")
        self.lbl_status.setStyleSheet("font-weight: bold;")
        controls.addWidget(self.lbl_status)
        controls.addStretch()

        layout.addLayout(controls)

        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        layout.addWidget(self.logs_text)

        self.tabs.addTab(tab, "Monitoramento")

    def _build_config_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QFormLayout()

        self.url_input = QLineEdit()
        self.pasta_input = QLineEdit()
        self.ext_input = QLineEdit()


        form.addRow("URl", self.url_input)
        form.addRow("Pasta", self.pasta_input)
        form.addRow("Ext", self.ext_input)


        layout.addLayout(form)

        salvar_layout = QHBoxLayout()
        salvar_layout.addStretch()

        self.btn_salvar_config = QPushButton("Salvar Config")
        self.btn_salvar_config.clicked.connect(self._salvar_config)
        salvar_layout.addWidget(self.btn_salvar_config)

        layout.addLayout(salvar_layout)
        layout.addStretch()

        self._config_tab_index = self.tabs.addTab(tab, "Configuração")

    # def _build_historico_tab(self):
    #     tab = QWidget()
    #     layout = QVBoxLayout(tab)
    #
    #     self.historico_table = QTableWidget(0, 5)
    #     self.historico_table.setHorizontalHeaderLabels(
    #         [
    #             "OS do laboratório",
    #             "Índice Encontrado",
    #             "Arquivos renomeados",
    #             "Status",
    #             "Data",
    #         ]
    #     )
    #     self.historico_table.horizontalHeader().setStretchLastSection(True)
    #     self.historico_table.setEditTriggers(QTableWidget.NoEditTriggers)
    #     self.historico_table.setSelectionBehavior(QTableWidget.SelectRows)
    #
    #     layout.addWidget(self.historico_table)
    #
    #     refresh_layout = QHBoxLayout()
    #     refresh_layout.addStretch()
    #
    #     btn_refresh = QPushButton("Atualizar")
    #     btn_refresh.clicked.connect(self._atualizar_historico)
    #     refresh_layout.addWidget(btn_refresh)
    #     layout.addLayout(refresh_layout)
    #
    #     self.tabs.addTab(tab, "Histórico")

    def _iniciar_robo(self):
        try:
            licenca_info = self.robo.iniciar()
            self.lbl_status.setText("Ativo")
            self.lbl_status.setStyleSheet("font-weight: bold; color: #0b7a0b;")

            if (
                licenca_info
                and licenca_info.get("tipo") != "permanente"
                and licenca_info.get("dias_restantes") is not None
                and licenca_info.get("dias_restantes") <= 10
            ):
                dias = licenca_info.get("dias_restantes")
                QMessageBox.warning(
                    self,
                    "Licença",
                    f"Sua licença vai vencer daqui a {dias} dias.",
                )
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))

    def _parar_robo(self):
        self.robo.parar()
        self.lbl_status.setText("Inativo")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #8b0000;")

    def _salvar_config(self):
        formas = Path(self.formas_input.text().strip())
        txt = Path(self.txt_input.text().strip())
        processados = Path(self.processados_input.text().strip())
        indice_texto = self.indice_input.text().strip()

        if not (formas.exists() and formas.is_dir()):
            QMessageBox.critical(self, "Validação", f"Pasta de formas inválida: {formas}")
            return

        if not (txt.exists() and txt.is_dir()):
            QMessageBox.critical(self, "Validação", f"Pasta de txt inválida: {txt}")
            return

        if not (processados.exists() and processados.is_dir()):
            QMessageBox.critical(self, "Validação", f"Pasta de processados inválida: {processados}")
            return

        try:
            indice = int(indice_texto)
            if indice < 0:
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, "Validação", "Índice inválido. Informe um número inteiro maior ou igual a 0.")
            return

        salvar_config(formas, txt, processados, indice)


        try:
            validar_caminhos()
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))
            return

        log("[CONFIG] Configurações salvas com sucesso.")
        QMessageBox.information(self, "Configuração", "Configuração salva com sucesso.")

    def _carregar_config_campos(self):
        self.formas_input.setText(str(get_pasta_formas() or ""))
        self.txt_input.setText(str(get_pasta_txt() or ""))
        self.processados_input.setText(str(get_pasta_processados() or ""))
        self.indice_input.setText(str(get_indice()))

    def _atualizar_historico(self):
        historico = carregar()
        self.historico_table.setRowCount(0)

        for os_lab, dados in historico.items():
            row = self.historico_table.rowCount()
            self.historico_table.insertRow(row)

            renomeados = ", ".join(dados.get("arquivos_renomeados", []))
            valores = [
                os_lab,
                dados.get("indice_encontrado", ""),
                renomeados,
                dados.get("status", ""),
                dados.get("data_processamento", ""),
            ]

            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                item.setTextAlignment(Qt.AlignCenter if col != 2 else Qt.AlignLeft | Qt.AlignVCenter)
                self.historico_table.setItem(row, col, item)

        self.historico_table.resizeColumnsToContents()

    def _processar_fila_logs(self):
        while not fila_logs.empty():
            linha = fila_logs.get_nowait()
            self.logs_text.append(linha)

    def _on_tab_changed(self, index):
        if self._troca_programatica:
            return

        nome_aba = self.tabs.tabText(index)

        if index == self._config_tab_index:
            if not self._acesso_config_liberado:
                self._troca_programatica = True
                self.tabs.setCurrentIndex(self._ultimo_indice)
                self._troca_programatica = False
                return

            self._acesso_config_liberado = False

            if self.robo.ativo:
                self._parar_robo()
                log("[CONFIG] Robô pausado ao abrir configurações.")

        if nome_aba == "Histórico":
            self._atualizar_historico()

        self._ultimo_indice = index

    def _autenticar_configuracoes(self):
        dialog = LoginDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False

        if dialog.usuario == "admin" and dialog.senha == "superadmin":
            return True

        QMessageBox.critical(self, "Acesso negado", "Usuário ou senha inválidos.")
        return False

    def eventFilter(self, watched, event):
        if watched is self.tabs.tabBar() and event.type() == QEvent.Type.MouseButtonPress:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            indice_clicado = self.tabs.tabBar().tabAt(pos)

            if indice_clicado == self._config_tab_index:
                if self._autenticar_configuracoes():
                    self._acesso_config_liberado = True
                    self.tabs.setCurrentIndex(self._config_tab_index)
                return True

        return super().eventFilter(watched, event)

    def closeEvent(self, event):
        self.robo.parar()
        event.accept()


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, False)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)

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
