import sys
import json
import socket
import struct
import time
import ipaddress
import threading
import traceback
from dataclasses import dataclass
from typing import Optional, Dict

import requests
from pypresence import Presence
from PyQt6 import QtCore, QtGui, QtWidgets

# ====== Nom et organisation de l'application ======
APP_ORG = "Hya"
APP_NAME = "Switch Discord Presence GUIPy"

TCP_PORT = 0xCAFE
PACKETMAGIC = 0xFFAADD23
PACKET_STRUCT = struct.Struct('2Q612s')  # 628 bytes

QUEST_URL = "https://raw.githubusercontent.com/Sun-Research-University/PresenceClient/master/Resource/QuestApplicationOverrides.json"
SWITCH_URL = "https://raw.githubusercontent.com/Sun-Research-University/PresenceClient/master/Resource/SwitchApplicationOverrides.json"


# ----------------------------- i18n -----------------------------

class I18N:
    FR = "fr"
    EN = "en"

    STR = {
        # On ne s'en sert plus pour le titre de fenêtre, on force APP_NAME.
        "device_ip": {FR: "IP de l’appareil :", EN: "Device IP:"},
        "client_id": {FR: "Discord Client ID :", EN: "Discord Client ID:"},
        "ignore_home": {FR: "Ignorer l’écran d’accueil (Home Menu)", EN: "Ignore Home Screen (Home Menu)"},
        "connect": {FR: "Connecter", EN: "Connect"},
        "stop": {FR: "Arrêter", EN: "Stop"},
        "now_playing": {FR: "Titre en cours", EN: "Now Playing"},
        "logs": {FR: "Logs", EN: "Logs"},
        "ready": {FR: "Prêt.", EN: "Ready."},
        "starting": {FR: "Démarrage...", EN: "Starting..."},
        "stopping": {FR: "Arrêt en cours...", EN: "Stopping..."},
        "stopped": {FR: "Arrêté.", EN: "Stopped."},
        "invalid_ip_title": {FR: "IP invalide", EN: "Invalid IP"},
        "invalid_ip_msg": {FR: "Veuillez entrer une adresse IP IPv4 valide.", EN: "Please enter a valid IPv4 address."},
        "missing_client_title": {FR: "Client ID manquant", EN: "Missing Client ID"},
        "missing_client_msg": {FR: "Veuillez entrer le Client ID Discord.", EN: "Please enter the Discord Client ID."},
        "menu_settings": {FR: "Paramètres", EN: "Settings"},
        "menu_language": {FR: "Langue", EN: "Language"},
        "menu_theme": {FR: "Thème", EN: "Theme"},
        "lang_fr": {FR: "Français", EN: "French"},
        "lang_en": {FR: "English", EN: "English"},
        "theme_light": {FR: "Clair", EN: "Light"},
        "theme_dark": {FR: "Sombre", EN: "Dark"},
        "theme_auto": {FR: "Auto (système)", EN: "Auto (System)"},
        "socket_connected": {FR: "Connecté au socket {addr}", EN: "Connected to socket {addr}"},
        "socket_connecting": {FR: "Connexion au socket {addr} ...", EN: "Connecting to socket {addr} ..."},
        "socket_reconnect": {FR: "Reconnexion socket dans 1s... ({err})", EN: "Reconnecting socket in 1s... ({err})"},
        "rpc_connected": {FR: "RPC Discord connecté.", EN: "Discord RPC connected."},
        "rpc_failed": {FR: "Impossible de connecter RPC Discord: {err}", EN: "Failed to connect Discord RPC: {err}"},
        "no_data": {FR: "Aucune donnée depuis >5s. Appareil hors ligne ?", EN: "No data for >5s. Device offline?"},
        "presence_updated": {FR: "Présence mise à jour: {details}", EN: "Presence updated: {details}"},
        "fatal": {FR: "Exception fatale:\n{trace}", EN: "Fatal exception:\n{trace}"},
        "overrides_dl_try": {FR: "Téléchargement {name} (tentative {a}/{b})...", EN: "Downloading {name} (attempt {a}/{b})..."},
        "overrides_dl_ok": {FR: "{name} chargés.", EN: "{name} loaded."},
        "overrides_dl_fail": {FR: "Échec de récupération des {name}. Les remplacements ne seront pas appliqués.", EN: "Failed to load {name}. Overrides will not be applied."},
        "invalid_ip_status": {FR: "IP invalide.", EN: "Invalid IP."},
        "rpc_not_connected": {FR: "RPC non connecté, nouvelle tentative...", EN: "RPC not connected, retrying..."},
        "stopping_status": {FR: "Arrêt.", EN: "Stopped."},
        "home_dash": {FR: "—", EN: "—"},
    }

    def __init__(self, lang=FR):
        self.lang = lang

    def t(self, key: str, **kwargs) -> str:
        s = self.STR.get(key, {}).get(self.lang, key)
        return s.format(**kwargs) if kwargs else s


# ----------------------------- Theme helpers -----------------------------

class Theme:
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"

def apply_light_palette(app: QtWidgets.QApplication):
    pal = QtGui.QPalette()
    pal.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#F5F5F7"))
    pal.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#FFFFFF"))
    pal.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor("#F0F0F0"))
    pal.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#FFFFFF"))
    for role in (
        QtGui.QPalette.ColorRole.WindowText,
        QtGui.QPalette.ColorRole.Text,
        QtGui.QPalette.ColorRole.ButtonText,
        QtGui.QPalette.ColorRole.ToolTipText,
        QtGui.QPalette.ColorRole.PlaceholderText,
        QtGui.QPalette.ColorRole.HighlightedText,
        QtGui.QPalette.ColorRole.BrightText,
        QtGui.QPalette.ColorRole.Link,
    ):
        pal.setColor(role, QtGui.QColor("#111111"))
    pal.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor("#D0E3FF"))
    app.setPalette(pal)

def apply_dark_palette(app: QtWidgets.QApplication):
    pal = QtGui.QPalette()
    pal.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#121212"))
    pal.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#1C1C1C"))
    pal.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor("#171717"))
    pal.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#1F1F1F"))
    for role in (
        QtGui.QPalette.ColorRole.WindowText,
        QtGui.QPalette.ColorRole.Text,
        QtGui.QPalette.ColorRole.ButtonText,
        QtGui.QPalette.ColorRole.ToolTipText,
        QtGui.QPalette.ColorRole.PlaceholderText,
        QtGui.QPalette.ColorRole.HighlightedText,
        QtGui.QPalette.ColorRole.BrightText,
        QtGui.QPalette.ColorRole.Link,
    ):
        pal.setColor(role, QtGui.QColor("#F1F1F1"))
    pal.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor("#2F6FED"))
    app.setPalette(pal)

def apply_auto_palette(app: QtWidgets.QApplication):
    try:
        scheme = app.styleHints().colorScheme()
        if int(scheme) == int(QtCore.Qt.ColorScheme.Dark):
            apply_dark_palette(app)
        else:
            apply_light_palette(app)
    except Exception:
        apply_light_palette(app)

def apply_global_stylesheet(app: QtWidgets.QApplication):
    app.setStyleSheet("""
    QWidget { font-size: 14px; }
    QGroupBox {
        border: 1px solid rgba(127,127,127,0.3);
        border-radius: 12px;
        margin-top: 10px; padding: 10px;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
    QLineEdit, QPlainTextEdit {
        border: 1px solid rgba(127,127,127,0.35);
        border-radius: 8px; padding: 6px 8px;
    }
    QPushButton {
        border: 1px solid rgba(127,127,127,0.35);
        border-radius: 10px; padding: 8px 14px;
    }
    QPushButton:disabled { opacity: .6; }
    """)


# ----------------------------- Utils -----------------------------

def valid_ip(ip: str) -> bool:
    try:
        ipaddress.IPv4Address(ip)
        return True
    except Exception:
        return False

def icon_from_pid(pid: int) -> str:
    return '0' + format(int(pid), 'x')


@dataclass
class TitlePacket:
    magic: int
    pid: int
    name: str

    @staticmethod
    def parse(raw: bytes, quest_overrides: Dict[str, dict], switch_overrides: Dict[str, dict]) -> "TitlePacket":
        magic, pid, name_raw = PACKET_STRUCT.unpack(raw)
        if pid == 0:
            name = "Home Menu"
        else:
            name = name_raw.decode("utf-8", "ignore").split("\x00")[0]

        if magic == PACKETMAGIC:
            if name in quest_overrides and quest_overrides[name].get("CustomName"):
                name = quest_overrides[name]["CustomName"]
        else:
            if name in switch_overrides and switch_overrides[name].get("CustomName"):
                name = switch_overrides[name]["CustomName"]

        return TitlePacket(magic=int(magic), pid=int(pid), name=name or "")


# ----------------------------- Worker Thread -----------------------------

class RpcWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    status = QtCore.pyqtSignal(str)
    nowPlaying = QtCore.pyqtSignal(str)
    connectedChanged = QtCore.pyqtSignal(bool)

    def __init__(self, ip: str, client_id: str, ignore_home: bool, i18n: I18N, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.client_id = client_id
        self.ignore_home = ignore_home
        self.i18n = i18n

        self._stop = threading.Event()
        self._rpc: Optional[Presence] = None
        self._sock: Optional[socket.socket] = None

        self.quest_overrides: Dict[str, dict] = {}
        self.switch_overrides: Dict[str, dict] = {}

        self.last_program_name = ""
        self.connected_presence = False

    def stop(self):
        self._stop.set()

    def _fetch_overrides(self):
        def fetch_one(url: str, name: str) -> Dict[str, dict]:
            for attempt in range(3):
                try:
                    self.log.emit(self.i18n.t("overrides_dl_try", name=name, a=attempt+1, b=3))
                    r = requests.get(url, timeout=10)
                    r.raise_for_status()
                    self.log.emit(self.i18n.t("overrides_dl_ok", name=name))
                    return r.json()
                except Exception as e:
                    self.log.emit(f"{name}: {e}")
                    time.sleep(1.5)
            self.log.emit(self.i18n.t("overrides_dl_fail", name=name))
            return {}

        self.quest_overrides = fetch_one(QUEST_URL, "Overrides Quest")
        self.switch_overrides = fetch_one(SWITCH_URL, "Overrides Switch")

    def _connect_socket(self):
        addr = (self.ip, TCP_PORT)
        while not self._stop.is_set():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                self.log.emit(self.i18n.t("socket_connecting", addr=addr))
                s.connect(addr)
                s.settimeout(2)
                self.status.emit(self.i18n.t("socket_connected", addr=addr))
                self.log.emit(self.i18n.t("socket_connected", addr=addr))
                return s
            except Exception as e:
                self.status.emit(self.i18n.t("socket_reconnect", err=e))
                time.sleep(1)
        return None

    def _ensure_rpc(self):
        if self._rpc is None:
            try:
                self._rpc = Presence(self.client_id)
                self._rpc.connect()
                self._rpc.clear()
                self.connected_presence = False
                self.log.emit(self.i18n.t("rpc_connected"))
            except Exception as e:
                self._rpc = None
                self.log.emit(self.i18n.t("rpc_failed", err=e))

    def _clear_rpc(self):
        if self._rpc:
            try:
                self._rpc.clear()
            except Exception:
                pass
        self.connected_presence = False
        self.connectedChanged.emit(False)

    def _close_all(self):
        try:
            if self._sock:
                self._sock.close()
        except Exception:
            pass
        self._sock = None
        try:
            self._clear_rpc()
        except Exception:
            pass

    def _presence_payload(self, title: TitlePacket):
        smallimagetext = ""
        largeimagekey = ""
        details = ""
        largeimagetext = title.name or ""

        if title.name == "Home Menu":
            largeimagekey = "switch"
            details = "Navigating the Home Menu"
            largeimagetext = "Home Menu"
            smallimagetext = "On the Switch"
        elif int(title.pid) != PACKETMAGIC:
            smallimagetext = "SwitchPresence-Rewritten"
            if title.name not in self.switch_overrides:
                largeimagekey = icon_from_pid(title.pid)
                details = title.name
            else:
                orinfo = self.switch_overrides[title.name]
                largeimagekey = orinfo.get("CustomKey") or icon_from_pid(title.pid)
                details = (orinfo.get("CustomPrefix") or "Playing") + " " + title.name
        else:
            smallimagetext = "QuestPresence"
            if title.name not in self.quest_overrides:
                largeimagekey = title.name.lower().replace(" ", "")
                details = "Playing " + title.name
            else:
                orinfo = self.quest_overrides[title.name]
                largeimagekey = orinfo.get("CustomKey") or title.name.lower().replace(" ", "")
                details = (orinfo.get("CustomPrefix") or "Playing") + " " + title.name

        return dict(
            details=details,
            large_image=largeimagekey,
            large_text=largeimagetext,
            small_text=smallimagetext
        )

    def run(self):
        try:
            if not valid_ip(self.ip):
                self.log.emit(self.i18n.t("invalid_ip_status"))
                self.status.emit(self.i18n.t("invalid_ip_status"))
                return

            self.status.emit("...")
            self._fetch_overrides()

            self._ensure_rpc()

            self._sock = self._connect_socket()
            if not self._sock:
                return

            self.last_program_name = ""
            last_data_ts = time.time()

            while not self._stop.is_set():
                try:
                    data = self._sock.recv(PACKET_STRUCT.size)
                    if not data or len(data) < PACKET_STRUCT.size:
                        raise ConnectionResetError("Socket closed or incomplete packet")

                    last_data_ts = time.time()
                    title = TitlePacket.parse(data, self.quest_overrides, self.switch_overrides)

                    if self.ignore_home and title.name == "Home Menu":
                        self.nowPlaying.emit(self.i18n.t("home_dash"))
                        if self._rpc and self.connected_presence:
                            self._clear_rpc()
                        time.sleep(0.5)
                        continue

                    if title.name != self.last_program_name:
                        self.last_program_name = title.name
                        self.nowPlaying.emit(title.name or self.i18n.t("home_dash"))

                    self._ensure_rpc()

                    if self._rpc:
                        payload = self._presence_payload(title)
                        try:
                            self._rpc.update(**payload)
                            if not self.connected_presence:
                                self.connected_presence = True
                                self.connectedChanged.emit(True)
                            self.status.emit(self.i18n.t("presence_updated", details=payload.get('details','')))
                        except Exception as e:
                            self.log.emit(self.i18n.t("rpc_failed", err=e))
                            self._clear_rpc()
                    else:
                        self.status.emit(self.i18n.t("rpc_not_connected"))
                        time.sleep(1)

                except socket.timeout:
                    if time.time() - last_data_ts > 5:
                        self.log.emit(self.i18n.t("no_data"))
                        self._clear_rpc()
                        try:
                            self._sock.close()
                        except Exception:
                            pass
                        self._sock = self._connect_socket()
                        if not self._sock:
                            return
                        continue
                except Exception as e:
                    self.log.emit(f"Socket error: {e}. Reconnecting...")
                    self._clear_rpc()
                    try:
                        if self._sock:
                            self._sock.close()
                    except Exception:
                        pass
                    if self._stop.is_set():
                        break
                    self._sock = self._connect_socket()
                    if not self._sock:
                        return

                time.sleep(1)

        except Exception as e:
            self.log.emit(self.i18n.t("fatal", trace="".join(traceback.format_exception(e))))
        finally:
            self._close_all()
            self.status.emit(self.i18n.t("stopping_status"))
            self.nowPlaying.emit(self.i18n.t("home_dash"))


# ----------------------------- GUI -----------------------------

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, i18n: I18N, theme: str):
        super().__init__()
        self.i18n = i18n
        self.theme = theme

        # Forcer le titre tout de suite
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(780, 560)
        self.setWindowIcon(QtGui.QIcon.fromTheme("applications-games"))

        # Central widgets
        self.ipEdit = QtWidgets.QLineEdit()
        self.ipEdit.setPlaceholderText("192.168.1.50")

        self.clientEdit = QtWidgets.QLineEdit()
        self.clientEdit.setPlaceholderText("Application ID (Dev Portal)")

        self.ignoreHome = QtWidgets.QCheckBox()

        self.btnConnect = QtWidgets.QPushButton()
        self.btnStop = QtWidgets.QPushButton()
        self.btnStop.setEnabled(False)

        self.nowPlayingLbl = QtWidgets.QLabel(self.i18n.t("home_dash"))
        f = self.nowPlayingLbl.font()
        f.setPointSize(15)
        f.setBold(True)
        self.nowPlayingLbl.setFont(f)
        self.nowPlayingLbl.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)

        self.logView = QtWidgets.QPlainTextEdit()
        self.logView.setReadOnly(True)
        self.logView.setMaximumBlockCount(4000)
        mono = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        mono.setPointSize(11)
        self.logView.setFont(mono)

        # Status bar
        self.statusLbl = QtWidgets.QLabel(self.i18n.t("ready"))
        self.statusBar().addPermanentWidget(self.statusLbl)

        # ---- Layout ----
        form = QtWidgets.QFormLayout()
        self.lblDevice = QtWidgets.QLabel()
        self.lblClient = QtWidgets.QLabel()
        form.addRow(self.lblDevice, self.ipEdit)
        form.addRow(self.lblClient, self.clientEdit)
        form.addRow(self.ignoreHome)

        self.topBox = QtWidgets.QGroupBox()
        topLay = QtWidgets.QVBoxLayout(self.topBox)
        topLay.addLayout(form)

        btnRow = QtWidgets.QHBoxLayout()
        btnRow.addWidget(self.btnConnect)
        btnRow.addWidget(self.btnStop)
        btnRow.addStretch(1)

        self.nowBox = QtWidgets.QGroupBox()
        nowRow = QtWidgets.QHBoxLayout(self.nowBox)
        nowRow.addWidget(self.nowPlayingLbl)

        center = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(center)
        v.setSpacing(10)
        v.addWidget(self.topBox)
        v.addLayout(btnRow)
        v.addWidget(self.nowBox)
        self.lblLogs = QtWidgets.QLabel()
        v.addWidget(self.lblLogs)
        v.addWidget(self.logView, 1)
        self.setCentralWidget(center)

        # ---- Menu ----
        self.menu = self.menuBar().addMenu(self.i18n.t("menu_settings"))
        self.langMenu = self.menu.addMenu(self.i18n.t("menu_language"))
        self.themeMenu = self.menu.addMenu(self.i18n.t("menu_theme"))

        self.actLangFR = self.langMenu.addAction(self.i18n.t("lang_fr"))
        self.actLangEN = self.langMenu.addAction(self.i18n.t("lang_en"))
        self.actThemeLight = self.themeMenu.addAction(self.i18n.t("theme_light"))
        self.actThemeDark = self.themeMenu.addAction(self.i18n.t("theme_dark"))
        self.actThemeAuto = self.themeMenu.addAction(self.i18n.t("theme_auto"))

        for a in (self.actLangFR, self.actLangEN, self.actThemeLight, self.actThemeDark, self.actThemeAuto):
            a.setCheckable(True)

        # State
        self.worker: Optional[RpcWorker] = None

        # Signals
        self.actLangFR.triggered.connect(lambda: self.changeLanguage(I18N.FR))
        self.actLangEN.triggered.connect(lambda: self.changeLanguage(I18N.EN))
        self.actThemeLight.triggered.connect(lambda: self.changeTheme(Theme.LIGHT))
        self.actThemeDark.triggered.connect(lambda: self.changeTheme(Theme.DARK))
        self.actThemeAuto.triggered.connect(lambda: self.changeTheme(Theme.AUTO))
        self.btnConnect.clicked.connect(self.startWorker)
        self.btnStop.clicked.connect(self.stopWorker)

        # Initial labels & checks
        self.retranslate()
        self.syncThemeChecks()

    def changeEvent(self, e: QtCore.QEvent):
        super().changeEvent(e)
        # Si la langue change, on re-force le titre
        if e.type() == QtCore.QEvent.Type.LanguageChange:
            self.setWindowTitle(APP_NAME)

    # ----- UI text refresh -----
    def retranslate(self):
        # Titre toujours forcé
        self.setWindowTitle(APP_NAME)
        self.lblDevice.setText(self.i18n.t("device_ip"))
        self.lblClient.setText(self.i18n.t("client_id"))
        self.ignoreHome.setText(self.i18n.t("ignore_home"))
        self.btnConnect.setText(self.i18n.t("connect"))
        self.btnStop.setText(self.i18n.t("stop"))
        self.topBox.setTitle(" ")
        self.nowBox.setTitle(self.i18n.t("now_playing"))
        self.lblLogs.setText(self.i18n.t("logs"))
        self.menu.setTitle(self.i18n.t("menu_settings"))
        self.langMenu.setTitle(self.i18n.t("menu_language"))
        self.themeMenu.setTitle(self.i18n.t("menu_theme"))
        self.actLangFR.setText(self.i18n.t("lang_fr"))
        self.actLangEN.setText(self.i18n.t("lang_en"))
        self.actThemeLight.setText(self.i18n.t("theme_light"))
        self.actThemeDark.setText(self.i18n.t("theme_dark"))
        self.actThemeAuto.setText(self.i18n.t("theme_auto"))
        self.statusLbl.setText(self.i18n.t("ready"))

    # ----- Theme handling -----
    def changeTheme(self, theme: str):
        self.theme = theme
        app = QtWidgets.QApplication.instance()
        if theme == Theme.DARK:
            apply_dark_palette(app)
        elif theme == Theme.LIGHT:
            apply_light_palette(app)
        else:
            apply_auto_palette(app)
        apply_global_stylesheet(app)
        self.syncThemeChecks()
        QtCore.QSettings(APP_ORG, APP_NAME).setValue("theme", theme)

    def syncThemeChecks(self):
        self.actThemeLight.setChecked(self.theme == Theme.LIGHT)
        self.actThemeDark.setChecked(self.theme == Theme.DARK)
        self.actThemeAuto.setChecked(self.theme == Theme.AUTO)

    # ----- Language handling -----
    def changeLanguage(self, lang: str):
        self.i18n.lang = lang
        self.retranslate()
        QtCore.QSettings(APP_ORG, APP_NAME).setValue("lang", lang)

    # ----- Worker control -----
    def appendLog(self, text: str):
        self.logView.appendPlainText(text)

    def setStatus(self, text: str):
        self.statusLbl.setText(text)

    def setNowPlaying(self, text: str):
        self.nowPlayingLbl.setText(text)

    def onConnectedChanged(self, yes: bool):
        self.statusLbl.setStyleSheet("color: #4caf50;" if yes else "color: #ffb74d;")

    def startWorker(self):
        ip = self.ipEdit.text().strip()
        client_id = self.clientEdit.text().strip()
        if not ip or not valid_ip(ip):
            QtWidgets.QMessageBox.warning(self, self.i18n.t("invalid_ip_title"), self.i18n.t("invalid_ip_msg"))
            return
        if not client_id:
            QtWidgets.QMessageBox.warning(self, self.i18n.t("missing_client_title"), self.i18n.t("missing_client_msg"))
            return

        self.logView.clear()
        self.setStatus(self.i18n.t("starting"))
        self.setNowPlaying(self.i18n.t("home_dash"))

        self.worker = RpcWorker(ip, client_id, self.ignoreHome.isChecked(), self.i18n)
        self.worker.log.connect(self.appendLog)
        self.worker.status.connect(self.setStatus)
        self.worker.nowPlaying.connect(self.setNowPlaying)
        self.worker.connectedChanged.connect(self.onConnectedChanged)
        self.worker.finished.connect(self.onWorkerFinished)
        self.worker.start()

        self.btnConnect.setEnabled(False)
        self.btnStop.setEnabled(True)

    def stopWorker(self):
        if self.worker and self.worker.isRunning():
            self.setStatus(self.i18n.t("stopping"))
            self.worker.stop()
            self.worker.wait(3000)
        self.onWorkerFinished()

    def onWorkerFinished(self):
        self.btnConnect.setEnabled(True)
        self.btnStop.setEnabled(False)
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
        self.onConnectedChanged(False)
        self.setStatus(self.i18n.t("stopped"))

    def closeEvent(self, event: QtGui.QCloseEvent):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        event.accept()


# ----------------------------- main -----------------------------

def main():
    # Définir identifiants pour QSettings
    QtCore.QCoreApplication.setOrganizationName(APP_ORG)
    QtCore.QCoreApplication.setApplicationName(APP_NAME)

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    # Nom d'affichage (taskbar Windows / Dock macOS)
    app.setApplicationDisplayName(APP_NAME)

    # Load saved prefs
    settings = QtCore.QSettings(APP_ORG, APP_NAME)
    lang = settings.value("lang", I18N.FR)
    theme = settings.value("theme", Theme.AUTO)

    # Apply theme at startup
    if theme == Theme.DARK:
        apply_dark_palette(app)
    elif theme == Theme.LIGHT:
        apply_light_palette(app)
    else:
        apply_auto_palette(app)
    apply_global_stylesheet(app)

    i18n = I18N(lang=lang)
    w = MainWindow(i18n=i18n, theme=theme)
    # Reforce le titre encore une fois (au cas où)
    w.setWindowTitle(APP_NAME)
    # Et après l'event loop d'init :
    QtCore.QTimer.singleShot(0, lambda: w.setWindowTitle(APP_NAME))

    w.resize(880, 640)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
import sys
import json
import socket
import struct
import time
import ipaddress
import threading
import traceback
from dataclasses import dataclass
from typing import Optional, Dict

import requests
from pypresence import Presence
from PyQt6 import QtCore, QtGui, QtWidgets

# ====== Nom et organisation de l'application ======
APP_ORG = "Hya"
APP_NAME = "Switch Discord Presence GUIPy"

TCP_PORT = 0xCAFE
PACKETMAGIC = 0xFFAADD23
PACKET_STRUCT = struct.Struct('2Q612s')  # 628 bytes

QUEST_URL = "https://raw.githubusercontent.com/Sun-Research-University/PresenceClient/master/Resource/QuestApplicationOverrides.json"
SWITCH_URL = "https://raw.githubusercontent.com/Sun-Research-University/PresenceClient/master/Resource/SwitchApplicationOverrides.json"


# ----------------------------- i18n -----------------------------

class I18N:
    FR = "fr"
    EN = "en"

    STR = {
        "device_ip": {FR: "IP de l’appareil :", EN: "Device IP:"},
        "client_id": {FR: "Discord Client ID :", EN: "Discord Client ID:"},
        "ignore_home": {FR: "Ignorer l’écran d’accueil (Home Menu)", EN: "Ignore Home Screen (Home Menu)"},
        "connect": {FR: "Connecter", EN: "Connect"},
        "stop": {FR: "Arrêter", EN: "Stop"},
        "now_playing": {FR: "Titre en cours", EN: "Now Playing"},
        "logs": {FR: "Logs", EN: "Logs"},
        "ready": {FR: "Prêt.", EN: "Ready."},
        "starting": {FR: "Démarrage...", EN: "Starting..."},
        "stopping": {FR: "Arrêt en cours...", EN: "Stopping..."},
        "stopped": {FR: "Arrêté.", EN: "Stopped."},
        "invalid_ip_title": {FR: "IP invalide", EN: "Invalid IP"},
        "invalid_ip_msg": {FR: "Veuillez entrer une adresse IP IPv4 valide.", EN: "Please enter a valid IPv4 address."},
        "missing_client_title": {FR: "Client ID manquant", EN: "Missing Client ID"},
        "missing_client_msg": {FR: "Veuillez entrer le Client ID Discord.", EN: "Please enter the Discord Client ID."},
        "menu_settings": {FR: "Paramètres", EN: "Settings"},
        "menu_language": {FR: "Langue", EN: "Language"},
        "menu_theme": {FR: "Thème", EN: "Theme"},
        "lang_fr": {FR: "Français", EN: "French"},
        "lang_en": {FR: "English", EN: "English"},
        "theme_light": {FR: "Clair", EN: "Light"},
        "theme_dark": {FR: "Sombre", EN: "Dark"},
        "theme_auto": {FR: "Auto (système)", EN: "Auto (System)"},
        "socket_connected": {FR: "Connecté au socket {addr}", EN: "Connected to socket {addr}"},
        "socket_connecting": {FR: "Connexion au socket {addr} ...", EN: "Connecting to socket {addr} ..."},
        "socket_reconnect": {FR: "Reconnexion socket dans 1s... ({err})", EN: "Reconnecting socket in 1s... ({err})"},
        "rpc_connected": {FR: "RPC Discord connecté.", EN: "Discord RPC connected."},
        "rpc_failed": {FR: "Impossible de connecter RPC Discord: {err}", EN: "Failed to connect Discord RPC: {err}"},
        "no_data": {FR: "Aucune donnée depuis >5s. Appareil hors ligne ?", EN: "No data for >5s. Device offline?"},
        "presence_updated": {FR: "Présence mise à jour: {details}", EN: "Presence updated: {details}"},
        "fatal": {FR: "Exception fatale:\n{trace}", EN: "Fatal exception:\n{trace}"},
        "overrides_dl_try": {FR: "Téléchargement {name} (tentative {a}/{b})...", EN: "Downloading {name} (attempt {a}/{b})..."},
        "overrides_dl_ok": {FR: "{name} chargés.", EN: "{name} loaded."},
        "overrides_dl_fail": {FR: "Échec de récupération des {name}. Les remplacements ne seront pas appliqués.", EN: "Failed to load {name}. Overrides will not be applied."},
        "invalid_ip_status": {FR: "IP invalide.", EN: "Invalid IP."},
        "rpc_not_connected": {FR: "RPC non connecté, nouvelle tentative...", EN: "RPC not connected, retrying..."},
        "stopping_status": {FR: "Arrêt.", EN: "Stopped."},
        "home_dash": {FR: "—", EN: "—"},
    }

    def __init__(self, lang=FR):
        self.lang = lang

    def t(self, key: str, **kwargs) -> str:
        s = self.STR.get(key, {}).get(self.lang, key)
        return s.format(**kwargs) if kwargs else s

class Theme:
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"

def apply_light_palette(app: QtWidgets.QApplication):
    pal = QtGui.QPalette()
    pal.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#F5F5F7"))
    pal.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#FFFFFF"))
    pal.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor("#F0F0F0"))
    pal.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#FFFFFF"))
    for role in (
        QtGui.QPalette.ColorRole.WindowText,
        QtGui.QPalette.ColorRole.Text,
        QtGui.QPalette.ColorRole.ButtonText,
        QtGui.QPalette.ColorRole.ToolTipText,
        QtGui.QPalette.ColorRole.PlaceholderText,
        QtGui.QPalette.ColorRole.HighlightedText,
        QtGui.QPalette.ColorRole.BrightText,
        QtGui.QPalette.ColorRole.Link,
    ):
        pal.setColor(role, QtGui.QColor("#111111"))
    pal.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor("#D0E3FF"))
    app.setPalette(pal)

def apply_dark_palette(app: QtWidgets.QApplication):
    pal = QtGui.QPalette()
    pal.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#121212"))
    pal.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#1C1C1C"))
    pal.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor("#171717"))
    pal.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#1F1F1F"))
    for role in (
        QtGui.QPalette.ColorRole.WindowText,
        QtGui.QPalette.ColorRole.Text,
        QtGui.QPalette.ColorRole.ButtonText,
        QtGui.QPalette.ColorRole.ToolTipText,
        QtGui.QPalette.ColorRole.PlaceholderText,
        QtGui.QPalette.ColorRole.HighlightedText,
        QtGui.QPalette.ColorRole.BrightText,
        QtGui.QPalette.ColorRole.Link,
    ):
        pal.setColor(role, QtGui.QColor("#F1F1F1"))
    pal.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor("#2F6FED"))
    app.setPalette(pal)

def apply_auto_palette(app: QtWidgets.QApplication):
    try:
        scheme = app.styleHints().colorScheme()
        if int(scheme) == int(QtCore.Qt.ColorScheme.Dark):
            apply_dark_palette(app)
        else:
            apply_light_palette(app)
    except Exception:
        apply_light_palette(app)

def apply_global_stylesheet(app: QtWidgets.QApplication):
    app.setStyleSheet("""
    QWidget { font-size: 14px; }
    QGroupBox {
        border: 1px solid rgba(127,127,127,0.3);
        border-radius: 12px;
        margin-top: 10px; padding: 10px;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
    QLineEdit, QPlainTextEdit {
        border: 1px solid rgba(127,127,127,0.35);
        border-radius: 8px; padding: 6px 8px;
    }
    QPushButton {
        border: 1px solid rgba(127,127,127,0.35);
        border-radius: 10px; padding: 8px 14px;
    }
    QPushButton:disabled { opacity: .6; }
    """)

def valid_ip(ip: str) -> bool:
    try:
        ipaddress.IPv4Address(ip)
        return True
    except Exception:
        return False

def icon_from_pid(pid: int) -> str:
    return '0' + format(int(pid), 'x')


@dataclass
class TitlePacket:
    magic: int
    pid: int
    name: str

    @staticmethod
    def parse(raw: bytes, quest_overrides: Dict[str, dict], switch_overrides: Dict[str, dict]) -> "TitlePacket":
        magic, pid, name_raw = PACKET_STRUCT.unpack(raw)
        if pid == 0:
            name = "Home Menu"
        else:
            name = name_raw.decode("utf-8", "ignore").split("\x00")[0]

        if magic == PACKETMAGIC:
            if name in quest_overrides and quest_overrides[name].get("CustomName"):
                name = quest_overrides[name]["CustomName"]
        else:
            if name in switch_overrides and switch_overrides[name].get("CustomName"):
                name = switch_overrides[name]["CustomName"]

        return TitlePacket(magic=int(magic), pid=int(pid), name=name or "")

class RpcWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    status = QtCore.pyqtSignal(str)
    nowPlaying = QtCore.pyqtSignal(str)
    connectedChanged = QtCore.pyqtSignal(bool)

    def __init__(self, ip: str, client_id: str, ignore_home: bool, i18n: I18N, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.client_id = client_id
        self.ignore_home = ignore_home
        self.i18n = i18n

        self._stop = threading.Event()
        self._rpc: Optional[Presence] = None
        self._sock: Optional[socket.socket] = None

        self.quest_overrides: Dict[str, dict] = {}
        self.switch_overrides: Dict[str, dict] = {}

        self.last_program_name = ""
        self.connected_presence = False

    def stop(self):
        self._stop.set()

    def _fetch_overrides(self):
        def fetch_one(url: str, name: str) -> Dict[str, dict]:
            for attempt in range(3):
                try:
                    self.log.emit(self.i18n.t("overrides_dl_try", name=name, a=attempt+1, b=3))
                    r = requests.get(url, timeout=10)
                    r.raise_for_status()
                    self.log.emit(self.i18n.t("overrides_dl_ok", name=name))
                    return r.json()
                except Exception as e:
                    self.log.emit(f"{name}: {e}")
                    time.sleep(1.5)
            self.log.emit(self.i18n.t("overrides_dl_fail", name=name))
            return {}

        self.quest_overrides = fetch_one(QUEST_URL, "Overrides Quest")
        self.switch_overrides = fetch_one(SWITCH_URL, "Overrides Switch")

    def _connect_socket(self):
        addr = (self.ip, TCP_PORT)
        while not self._stop.is_set():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                self.log.emit(self.i18n.t("socket_connecting", addr=addr))
                s.connect(addr)
                s.settimeout(2)
                self.status.emit(self.i18n.t("socket_connected", addr=addr))
                self.log.emit(self.i18n.t("socket_connected", addr=addr))
                return s
            except Exception as e:
                self.status.emit(self.i18n.t("socket_reconnect", err=e))
                time.sleep(1)
        return None

    def _ensure_rpc(self):
        if self._rpc is None:
            try:
                self._rpc = Presence(self.client_id)
                self._rpc.connect()
                self._rpc.clear()
                self.connected_presence = False
                self.log.emit(self.i18n.t("rpc_connected"))
            except Exception as e:
                self._rpc = None
                self.log.emit(self.i18n.t("rpc_failed", err=e))

    def _clear_rpc(self):
        if self._rpc:
            try:
                self._rpc.clear()
            except Exception:
                pass
        self.connected_presence = False
        self.connectedChanged.emit(False)

    def _close_all(self):
        try:
            if self._sock:
                self._sock.close()
        except Exception:
            pass
        self._sock = None
        try:
            self._clear_rpc()
        except Exception:
            pass

    def _presence_payload(self, title: TitlePacket):
        smallimagetext = ""
        largeimagekey = ""
        details = ""
        largeimagetext = title.name or ""

        if title.name == "Home Menu":
            largeimagekey = "switch"
            details = "Navigating the Home Menu"
            largeimagetext = "Home Menu"
            smallimagetext = "On the Switch"
        elif int(title.pid) != PACKETMAGIC:
            smallimagetext = "SwitchPresence-Rewritten"
            if title.name not in self.switch_overrides:
                largeimagekey = icon_from_pid(title.pid)
                details = title.name
            else:
                orinfo = self.switch_overrides[title.name]
                largeimagekey = orinfo.get("CustomKey") or icon_from_pid(title.pid)
                details = (orinfo.get("CustomPrefix") or "Playing") + " " + title.name
        else:
            smallimagetext = "QuestPresence"
            if title.name not in self.quest_overrides:
                largeimagekey = title.name.lower().replace(" ", "")
                details = "Playing " + title.name
            else:
                orinfo = self.quest_overrides[title.name]
                largeimagekey = orinfo.get("CustomKey") or title.name.lower().replace(" ", "")
                details = (orinfo.get("CustomPrefix") or "Playing") + " " + title.name

        return dict(
            details=details,
            large_image=largeimagekey,
            large_text=largeimagetext,
            small_text=smallimagetext
        )

    def run(self):
        try:
            if not valid_ip(self.ip):
                self.log.emit(self.i18n.t("invalid_ip_status"))
                self.status.emit(self.i18n.t("invalid_ip_status"))
                return

            self.status.emit("...")
            self._fetch_overrides()

            self._ensure_rpc()

            self._sock = self._connect_socket()
            if not self._sock:
                return

            self.last_program_name = ""
            last_data_ts = time.time()

            while not self._stop.is_set():
                try:
                    data = self._sock.recv(PACKET_STRUCT.size)
                    if not data or len(data) < PACKET_STRUCT.size:
                        raise ConnectionResetError("Socket closed or incomplete packet")

                    last_data_ts = time.time()
                    title = TitlePacket.parse(data, self.quest_overrides, self.switch_overrides)

                    if self.ignore_home and title.name == "Home Menu":
                        self.nowPlaying.emit(self.i18n.t("home_dash"))
                        if self._rpc and self.connected_presence:
                            self._clear_rpc()
                        time.sleep(0.5)
                        continue

                    if title.name != self.last_program_name:
                        self.last_program_name = title.name
                        self.nowPlaying.emit(title.name or self.i18n.t("home_dash"))

                    self._ensure_rpc()

                    if self._rpc:
                        payload = self._presence_payload(title)
                        try:
                            self._rpc.update(**payload)
                            if not self.connected_presence:
                                self.connected_presence = True
                                self.connectedChanged.emit(True)
                            self.status.emit(self.i18n.t("presence_updated", details=payload.get('details','')))
                        except Exception as e:
                            self.log.emit(self.i18n.t("rpc_failed", err=e))
                            self._clear_rpc()
                    else:
                        self.status.emit(self.i18n.t("rpc_not_connected"))
                        time.sleep(1)

                except socket.timeout:
                    if time.time() - last_data_ts > 5:
                        self.log.emit(self.i18n.t("no_data"))
                        self._clear_rpc()
                        try:
                            self._sock.close()
                        except Exception:
                            pass
                        self._sock = self._connect_socket()
                        if not self._sock:
                            return
                        continue
                except Exception as e:
                    self.log.emit(f"Socket error: {e}. Reconnecting...")
                    self._clear_rpc()
                    try:
                        if self._sock:
                            self._sock.close()
                    except Exception:
                        pass
                    if self._stop.is_set():
                        break
                    self._sock = self._connect_socket()
                    if not self._sock:
                        return

                time.sleep(1)

        except Exception as e:
            self.log.emit(self.i18n.t("fatal", trace="".join(traceback.format_exception(e))))
        finally:
            self._close_all()
            self.status.emit(self.i18n.t("stopping_status"))
            self.nowPlaying.emit(self.i18n.t("home_dash"))



class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, i18n: I18N, theme: str):
        super().__init__()
        self.i18n = i18n
        self.theme = theme
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(780, 560)
        self.setWindowIcon(QtGui.QIcon.fromTheme("applications-games"))

        self.ipEdit = QtWidgets.QLineEdit()
        self.ipEdit.setPlaceholderText("192.168.1.50")

        self.clientEdit = QtWidgets.QLineEdit()
        self.clientEdit.setPlaceholderText("Application ID (Dev Portal)")

        self.ignoreHome = QtWidgets.QCheckBox()

        self.btnConnect = QtWidgets.QPushButton()
        self.btnStop = QtWidgets.QPushButton()
        self.btnStop.setEnabled(False)

        self.nowPlayingLbl = QtWidgets.QLabel(self.i18n.t("home_dash"))
        f = self.nowPlayingLbl.font()
        f.setPointSize(15)
        f.setBold(True)
        self.nowPlayingLbl.setFont(f)
        self.nowPlayingLbl.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)

        self.logView = QtWidgets.QPlainTextEdit()
        self.logView.setReadOnly(True)
        self.logView.setMaximumBlockCount(4000)
        mono = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        mono.setPointSize(11)
        self.logView.setFont(mono)

        self.statusLbl = QtWidgets.QLabel(self.i18n.t("ready"))
        self.statusBar().addPermanentWidget(self.statusLbl)

        form = QtWidgets.QFormLayout()
        self.lblDevice = QtWidgets.QLabel()
        self.lblClient = QtWidgets.QLabel()
        form.addRow(self.lblDevice, self.ipEdit)
        form.addRow(self.lblClient, self.clientEdit)
        form.addRow(self.ignoreHome)

        self.topBox = QtWidgets.QGroupBox()
        topLay = QtWidgets.QVBoxLayout(self.topBox)
        topLay.addLayout(form)

        btnRow = QtWidgets.QHBoxLayout()
        btnRow.addWidget(self.btnConnect)
        btnRow.addWidget(self.btnStop)
        btnRow.addStretch(1)

        self.nowBox = QtWidgets.QGroupBox()
        nowRow = QtWidgets.QHBoxLayout(self.nowBox)
        nowRow.addWidget(self.nowPlayingLbl)

        center = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(center)
        v.setSpacing(10)
        v.addWidget(self.topBox)
        v.addLayout(btnRow)
        v.addWidget(self.nowBox)
        self.lblLogs = QtWidgets.QLabel()
        v.addWidget(self.lblLogs)
        v.addWidget(self.logView, 1)
        self.setCentralWidget(center)

        self.menu = self.menuBar().addMenu(self.i18n.t("menu_settings"))
        self.langMenu = self.menu.addMenu(self.i18n.t("menu_language"))
        self.themeMenu = self.menu.addMenu(self.i18n.t("menu_theme"))

        self.actLangFR = self.langMenu.addAction(self.i18n.t("lang_fr"))
        self.actLangEN = self.langMenu.addAction(self.i18n.t("lang_en"))
        self.actThemeLight = self.themeMenu.addAction(self.i18n.t("theme_light"))
        self.actThemeDark = self.themeMenu.addAction(self.i18n.t("theme_dark"))
        self.actThemeAuto = self.themeMenu.addAction(self.i18n.t("theme_auto"))

        for a in (self.actLangFR, self.actLangEN, self.actThemeLight, self.actThemeDark, self.actThemeAuto):
            a.setCheckable(True)

        self.worker: Optional[RpcWorker] = None

        self.actLangFR.triggered.connect(lambda: self.changeLanguage(I18N.FR))
        self.actLangEN.triggered.connect(lambda: self.changeLanguage(I18N.EN))
        self.actThemeLight.triggered.connect(lambda: self.changeTheme(Theme.LIGHT))
        self.actThemeDark.triggered.connect(lambda: self.changeTheme(Theme.DARK))
        self.actThemeAuto.triggered.connect(lambda: self.changeTheme(Theme.AUTO))
        self.btnConnect.clicked.connect(self.startWorker)
        self.btnStop.clicked.connect(self.stopWorker)

        self.retranslate()
        self.syncThemeChecks()

    def changeEvent(self, e: QtCore.QEvent):
        super().changeEvent(e)
        if e.type() == QtCore.QEvent.Type.LanguageChange:
            self.setWindowTitle(APP_NAME)

    def retranslate(self):
        self.setWindowTitle(APP_NAME)
        self.lblDevice.setText(self.i18n.t("device_ip"))
        self.lblClient.setText(self.i18n.t("client_id"))
        self.ignoreHome.setText(self.i18n.t("ignore_home"))
        self.btnConnect.setText(self.i18n.t("connect"))
        self.btnStop.setText(self.i18n.t("stop"))
        self.topBox.setTitle(" ")
        self.nowBox.setTitle(self.i18n.t("now_playing"))
        self.lblLogs.setText(self.i18n.t("logs"))
        self.menu.setTitle(self.i18n.t("menu_settings"))
        self.langMenu.setTitle(self.i18n.t("menu_language"))
        self.themeMenu.setTitle(self.i18n.t("menu_theme"))
        self.actLangFR.setText(self.i18n.t("lang_fr"))
        self.actLangEN.setText(self.i18n.t("lang_en"))
        self.actThemeLight.setText(self.i18n.t("theme_light"))
        self.actThemeDark.setText(self.i18n.t("theme_dark"))
        self.actThemeAuto.setText(self.i18n.t("theme_auto"))
        self.statusLbl.setText(self.i18n.t("ready"))

    def changeTheme(self, theme: str):
        self.theme = theme
        app = QtWidgets.QApplication.instance()
        if theme == Theme.DARK:
            apply_dark_palette(app)
        elif theme == Theme.LIGHT:
            apply_light_palette(app)
        else:
            apply_auto_palette(app)
        apply_global_stylesheet(app)
        self.syncThemeChecks()
        QtCore.QSettings(APP_ORG, APP_NAME).setValue("theme", theme)

    def syncThemeChecks(self):
        self.actThemeLight.setChecked(self.theme == Theme.LIGHT)
        self.actThemeDark.setChecked(self.theme == Theme.DARK)
        self.actThemeAuto.setChecked(self.theme == Theme.AUTO)

    def changeLanguage(self, lang: str):
        self.i18n.lang = lang
        self.retranslate()
        QtCore.QSettings(APP_ORG, APP_NAME).setValue("lang", lang)

    def appendLog(self, text: str):
        self.logView.appendPlainText(text)

    def setStatus(self, text: str):
        self.statusLbl.setText(text)

    def setNowPlaying(self, text: str):
        self.nowPlayingLbl.setText(text)

    def onConnectedChanged(self, yes: bool):
        self.statusLbl.setStyleSheet("color: #4caf50;" if yes else "color: #ffb74d;")

    def startWorker(self):
        ip = self.ipEdit.text().strip()
        client_id = self.clientEdit.text().strip()
        if not ip or not valid_ip(ip):
            QtWidgets.QMessageBox.warning(self, self.i18n.t("invalid_ip_title"), self.i18n.t("invalid_ip_msg"))
            return
        if not client_id:
            QtWidgets.QMessageBox.warning(self, self.i18n.t("missing_client_title"), self.i18n.t("missing_client_msg"))
            return

        self.logView.clear()
        self.setStatus(self.i18n.t("starting"))
        self.setNowPlaying(self.i18n.t("home_dash"))

        self.worker = RpcWorker(ip, client_id, self.ignoreHome.isChecked(), self.i18n)
        self.worker.log.connect(self.appendLog)
        self.worker.status.connect(self.setStatus)
        self.worker.nowPlaying.connect(self.setNowPlaying)
        self.worker.connectedChanged.connect(self.onConnectedChanged)
        self.worker.finished.connect(self.onWorkerFinished)
        self.worker.start()

        self.btnConnect.setEnabled(False)
        self.btnStop.setEnabled(True)

    def stopWorker(self):
        if self.worker and self.worker.isRunning():
            self.setStatus(self.i18n.t("stopping"))
            self.worker.stop()
            self.worker.wait(3000)
        self.onWorkerFinished()

    def onWorkerFinished(self):
        self.btnConnect.setEnabled(True)
        self.btnStop.setEnabled(False)
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
        self.onConnectedChanged(False)
        self.setStatus(self.i18n.t("stopped"))

    def closeEvent(self, event: QtGui.QCloseEvent):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        event.accept()


# ----------------------------- main -----------------------------

def main():
    # Définir identifiants pour QSettings
    QtCore.QCoreApplication.setOrganizationName(APP_ORG)
    QtCore.QCoreApplication.setApplicationName(APP_NAME)

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    # Nom d'affichage (taskbar Windows / Dock macOS)
    app.setApplicationDisplayName(APP_NAME)

    # Load saved prefs
    settings = QtCore.QSettings(APP_ORG, APP_NAME)
    lang = settings.value("lang", I18N.FR)
    theme = settings.value("theme", Theme.AUTO)

    # Apply theme at startup
    if theme == Theme.DARK:
        apply_dark_palette(app)
    elif theme == Theme.LIGHT:
        apply_light_palette(app)
    else:
        apply_auto_palette(app)
    apply_global_stylesheet(app)

    i18n = I18N(lang=lang)
    w = MainWindow(i18n=i18n, theme=theme)
    # Reforce le titre encore une fois (au cas où)
    w.setWindowTitle(APP_NAME)
    # Et après l'event loop d'init :
    QtCore.QTimer.singleShot(0, lambda: w.setWindowTitle(APP_NAME))

    w.resize(880, 640)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
