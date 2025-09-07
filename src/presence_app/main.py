import sys
import os
import json
import socket
import struct
import time
import ipaddress
import threading
import traceback
import platform
import hashlib
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Tuple

import requests
from pypresence import Presence
from PyQt6 import QtCore, QtGui, QtWidgets

APP_ORG = "Hya"
APP_NAME = "Switch Discord Presence GUIPy"
APP_VERSION = "1.0.4"  

GITHUB_OWNER = "THZoria"
GITHUB_REPO = "Switch-Discord-Presence-GUIPy"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

TCP_PORT = 0xCAFE
PACKETMAGIC = 0xFFAADD23
PACKET_STRUCT = struct.Struct('2Q612s')

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

        "menu_help": {FR: "Aide", EN: "Help"},
        "check_updates": {FR: "Rechercher des mises à jour…", EN: "Check for updates…"},
        "about": {FR: "À propos", EN: "About"},
        "current_version": {FR: "Version actuelle: {v}", EN: "Current version: {v}"},
        "up_to_date": {FR: "Vous êtes à jour ✅", EN: "You are up to date ✅"},
        "update_title": {FR: "Mise à jour disponible", EN: "Update available"},
        "update_body": {
            FR: "Nouvelle version: {new}\nVersion actuelle: {cur}\n\nRelease: {url}\nSHA-256 attendu ({asset}):\n{sha}",
            EN: "New version: {new}\nCurrent version: {cur}\n\nRelease: {url}\nExpected SHA-256 ({asset}):\n{sha}"
        },
        "btn_open_release": {FR: "Ouvrir la release", EN: "Open release"},
        "btn_verify_file": {FR: "Vérifier un fichier…", EN: "Verify a file…"},
        "btn_ok": {FR: "OK", EN: "OK"},
        "verif_ok": {FR: "Le fichier correspond au SHA-256 publié ✅", EN: "File matches published SHA-256 ✅"},
        "verif_ko": {
            FR: "Le hash ne correspond pas.\nAttendu: {exp}\nObtenu:  {got}",
            EN: "Hash mismatch.\nExpected: {exp}\nGot:      {got}"
        },
        "verif_title": {FR: "Vérification du fichier", EN: "File verification"},
        "checking_updates": {FR: "Recherche de mise à jour…", EN: "Checking for updates…"},
        "check_failed": {FR: "Impossible de vérifier les mises à jour.\n{err}", EN: "Unable to check updates.\n{err}"},
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


def get_config_dir() -> Path:
    """Retourne le dossier de config par OS."""
    if sys.platform.startswith("win"):
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME  # ex: %APPDATA%/Switch Discord Presence GUIPy

CONFIG_DIR = get_config_dir()
CONFIG_FILE = CONFIG_DIR / "config.json"

class ConfigStore:
    """Lecture/écriture JSON atomique (sans dépendances)."""
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data: dict = {}
        self.load()

    def load(self) -> None:
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self.data = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value) -> None:
        self.data[key] = value


def valid_ip(ip: str) -> bool:
    try:
        ipaddress.IPv4Address(ip)
        return True
    except Exception:
        return False

def icon_from_pid(pid: int) -> str:
    return '0' + format(int(pid), 'x')

def cmp_versions(a: str, b: str) -> int:
    """Compare '1.2.10' vs '1.2.3'. Returns 1 if a>b, -1 if a<b, 0 if equal."""
    def parts(v): return [int(x) for x in v.strip().lstrip('v').split('.')]
    pa, pb = parts(a), parts(b)
    m = max(len(pa), len(pb))
    pa += [0]*(m-len(pa)); pb += [0]*(m-len(pb))
    return (pa > pb) - (pa < pb)

def detect_target_label() -> Tuple[str, str]:
    """Return (label, ext) for artifact naming by OS/arch, matching the workflow outputs."""
    if sys.platform.startswith("win"):
        return "windows-x64", ".zip"
    if sys.platform == "darwin":
        m = platform.machine().lower()
        if "arm" in m or "aarch64" in m:
            return "mac-arm64", ".zip"
        return "mac-intel", ".zip"
    return "linux-x64", ".tar.gz"

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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


class UpdateChecker(QtCore.QThread):
    finishedWithResult = QtCore.pyqtSignal(object, object)  # (result: dict, error: Exception|None)

    def __init__(self, i18n: I18N, parent=None):
        super().__init__(parent)
        self.i18n = i18n

    def run(self):
        try:
            headers = {"Accept": "application/vnd.github+json", "User-Agent": APP_NAME}
            r = requests.get(GITHUB_API_LATEST, headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()

            latest = (data.get("tag_name") or "").lstrip("v")
            rel_url = data.get("html_url") or f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
            assets = data.get("assets") or []

            label, ext = detect_target_label()
            base = f"SwitchDiscordPresenceGUIPy-{label}{ext}"
            want_sha = f"{base}.sha256"

            sha_remote = None
            asset_name = None
            for a in assets:
                if a.get("name") == want_sha:
                    u = a.get("browser_download_url")
                    rr = requests.get(u, headers=headers, timeout=15)
                    rr.raise_for_status()
                    sha_remote = (rr.text or "").strip().split()[0]
                    asset_name = base
                    break

            result = {
                "latest": latest,
                "current": APP_VERSION,
                "release_url": rel_url,
                "asset_name": asset_name,
                "sha256": sha_remote,
                "has_update": (latest and cmp_versions(latest, APP_VERSION) > 0),
                "sha_ok": (sha_remote is not None and len(sha_remote) == 64 and all(c in "0123456789abcdef" for c in sha_remote.lower()))
            }
            self.finishedWithResult.emit(result, None)
        except Exception as e:
            self.finishedWithResult.emit({}, e)



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

        # --- TID indexes + regex ---
        self.tid_to_name: Dict[str, str] = {}
        self.name_to_tid: Dict[str, str] = {}
        self._tid_re = re.compile(r"^[0-9A-Fa-f]{16}$")

    def stop(self):
        self._stop.set()

    def _fetch_overrides(self):
        def fetch_one(url: str, name: str) -> Dict[str, dict]:
            for attempt in range(3):
                try:
                    self.log.emit(self.i18n.t("overrides_dl_try", name=name, a=attempt + 1, b=3))
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

        # Build TID indexes after loading
        self._build_tid_indexes()

    # -------------------- TID helpers --------------------
    def _is_tid(self, s: str) -> bool:
        return bool(s and self._tid_re.match(s.strip()))

    def _build_tid_indexes(self) -> None:
        """Build maps: tid_to_name (both cases) and name_to_tid from switch_overrides."""
        self.tid_to_name.clear()
        self.name_to_tid.clear()

        sw = self.switch_overrides or {}
        if isinstance(sw, dict):
            for name, info in sw.items():
                if not isinstance(info, dict):
                    continue
                tids = []
                for k in ("TitleIds", "TitleIDs", "TIDs", "Tids", "Tid", "TitleId", "TitleID"):
                    v = info.get(k)
                    if isinstance(v, str):
                        tids.append(v)
                    elif isinstance(v, (list, tuple)):
                        tids.extend([x for x in v if isinstance(x, str)])

                norm = []
                for t in tids:
                    t = t.strip()
                    if self._is_tid(t):
                        norm.append(t)

                if not norm:
                    continue

                display = info.get("CustomName") or name
                self.name_to_tid[display] = norm[0]
                for t in norm:
                    self.tid_to_name[t.upper()] = display
                    self.tid_to_name[t.lower()] = display

    def _resolve_name_from_tid(self, tid: str) -> Optional[str]:
        if not self._is_tid(tid):
            return None
        return (self.tid_to_name.get(tid)
                or self.tid_to_name.get(tid.upper())
                or self.tid_to_name.get(tid.lower()))

    def _resolve_tid_from_name(self, name: str) -> Optional[str]:
        return (self.name_to_tid or {}).get(name)

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
        # TID-aware payload builder
        smallimagetext = ""
        largeimagekey = ""
        details = ""

        # Start from provided name but resolve if it's a TID
        display_name = title.name or ""
        preferred_tid: Optional[str] = None

        # If incoming "name" is a TID -> resolve human-readable
        if self._is_tid(display_name):
            resolved = self._resolve_name_from_tid(display_name)
            if resolved:
                display_name = resolved
            preferred_tid = title.name  # use asset named like this TID if uploaded
        else:
            # Try to find a TID for this name
            preferred_tid = self._resolve_tid_from_name(display_name)

        largeimagetext = display_name or ""

        # Home Menu
        if display_name == "Home Menu":
            largeimagekey = "switch"
            details = "Navigating the Home Menu"
            largeimagetext = "Home Menu"
            smallimagetext = "On the Switch"
            return dict(
                details=details,
                large_image=largeimagekey,
                large_text=largeimagetext,
                small_text=smallimagetext
            )

        # Switch vs Quest
        if int(title.pid) != PACKETMAGIC:
            # SWITCH
            smallimagetext = "SwitchPresence-Rewritten"
            orinfo = self.switch_overrides.get(display_name)

            if not orinfo:
                # Prefer TID asset if present, else fallback to pid->hex
                largeimagekey = preferred_tid or icon_from_pid(title.pid)
                details = display_name
            else:
                # CustomKey > TID > pid->hex
                largeimagekey = (orinfo.get("CustomKey")
                                 or preferred_tid
                                 or icon_from_pid(title.pid))
                prefix = (orinfo.get("CustomPrefix") or "Playing")
                details = f"{prefix} {display_name}"

            return dict(
                details=details,
                large_image=largeimagekey,
                large_text=largeimagetext,
                small_text=smallimagetext
            )

        else:
            # QUEST (unchanged baseline)
            smallimagetext = "QuestPresence"
            if display_name not in self.quest_overrides:
                largeimagekey = display_name.lower().replace(" ", "")
                details = "Playing " + display_name
            else:
                orinfo = self.quest_overrides[display_name]
                largeimagekey = orinfo.get("CustomKey") or display_name.lower().replace(" ", "")
                details = (orinfo.get("CustomPrefix") or "Playing") + " " + display_name

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
                            self.status.emit(self.i18n.t("presence_updated", details=payload.get('details', '')))
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
    def __init__(self, i18n: I18N, theme: str, config: ConfigStore):
        super().__init__()
        self.i18n = i18n
        self.theme = theme
        self.config = config

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

        self.helpMenu = self.menuBar().addMenu(self.i18n.t("menu_help"))
        self.actCheckUpdate = self.helpMenu.addAction(self.i18n.t("check_updates"))
        self.actAbout = self.helpMenu.addAction(self.i18n.t("about"))

        self.worker: Optional[RpcWorker] = None
        self._upd: Optional[UpdateChecker] = None

        self.actLangFR.triggered.connect(lambda: self.changeLanguage(I18N.FR))
        self.actLangEN.triggered.connect(lambda: self.changeLanguage(I18N.EN))
        self.actThemeLight.triggered.connect(lambda: self.changeTheme(Theme.LIGHT))
        self.actThemeDark.triggered.connect(lambda: self.changeTheme(Theme.DARK))
        self.actThemeAuto.triggered.connect(lambda: self.changeTheme(Theme.AUTO))
        self.btnConnect.clicked.connect(self.startWorker)
        self.btnStop.clicked.connect(self.stopWorker)

        self.actCheckUpdate.triggered.connect(lambda: self.checkUpdates(manual=True))
        self.actAbout.triggered.connect(self.showAbout)

        self.ipEdit.setText(self.config.get("device_ip", "") or "")
        self.clientEdit.setText(self.config.get("client_id", "") or "")
        self.ignoreHome.setChecked(bool(self.config.get("ignore_home", False)))

        size = self.config.get("win_size")
        pos = self.config.get("win_pos")
        try:
            if isinstance(size, (list, tuple)) and len(size) == 2:
                self.resize(int(size[0]), int(size[1]))
            if isinstance(pos, (list, tuple)) and len(pos) == 2:
                self.move(int(pos[0]), int(pos[1]))
        except Exception:
            pass

        self.ipEdit.textEdited.connect(lambda _t: self.saveConfigField("device_ip", self.ipEdit.text().strip()))
        self.clientEdit.textEdited.connect(lambda _t: self.saveConfigField("client_id", self.clientEdit.text().strip()))
        self.ignoreHome.toggled.connect(lambda v: self.saveConfigField("ignore_home", bool(v)))

        self.retranslate()
        self.syncThemeChecks()

        QtCore.QTimer.singleShot(2000, lambda: self.checkUpdates(manual=False))

    def changeEvent(self, e: QtCore.QEvent):
        super().changeEvent(e)
        if e.type() == QtCore.QEvent.Type.LanguageChange:
            self.setWindowTitle(APP_NAME)

    def saveConfigField(self, key: str, value):
        self.config.set(key, value)
        self.config.save()

    def saveWindowStateToConfig(self):
        self.config.set("win_size", [self.width(), self.height()])
        self.config.set("win_pos", [self.x(), self.y()])
        self.config.save()

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
        self.helpMenu.setTitle(self.i18n.t("menu_help"))
        self.actCheckUpdate.setText(self.i18n.t("check_updates"))
        self.actAbout.setText(self.i18n.t("about"))
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
        self.saveConfigField("theme", theme)

    def syncThemeChecks(self):
        self.actThemeLight.setChecked(self.theme == Theme.LIGHT)
        self.actThemeDark.setChecked(self.theme == Theme.DARK)
        self.actThemeAuto.setChecked(self.theme == Theme.AUTO)

    def changeLanguage(self, lang: str):
        self.i18n.lang = lang
        self.retranslate()
        QtCore.QSettings(APP_ORG, APP_NAME).setValue("lang", lang)
        self.saveConfigField("lang", lang)

    def showAbout(self):
        QtWidgets.QMessageBox.information(
            self, f"About — {APP_NAME}",
            f"{APP_NAME}\n{self.i18n.t('current_version', v=APP_VERSION)}"
        )

    def checkUpdates(self, manual: bool = False):
        self.statusLbl.setText(self.i18n.t("checking_updates"))
        self._upd = UpdateChecker(self.i18n, self)
        self._upd.finishedWithResult.connect(lambda res, err: self.onUpdateResult(res, err, manual))
        self._upd.start()

    def onUpdateResult(self, res: dict, err: Optional[Exception], manual: bool):
        if err:
            if manual:
                QtWidgets.QMessageBox.warning(self, APP_NAME, self.i18n.t("check_failed", err=str(err)))
            self.statusLbl.setText(self.i18n.t("ready"))
            return

        latest = res.get("latest") or "?"
        cur = res.get("current") or "?"
        url = res.get("release_url") or ""
        sha = res.get("sha256") or "—"
        asset = res.get("asset_name") or "?"

        if res.get("has_update"):
            mb = QtWidgets.QMessageBox(self)
            mb.setWindowTitle(self.i18n.t("update_title"))
            mb.setIcon(QtWidgets.QMessageBox.Icon.Information)
            mb.setText(self.i18n.t("update_body", new=latest, cur=cur, url=url, sha=sha, asset=asset))
            openBtn = mb.addButton(self.i18n.t("btn_open_release"), QtWidgets.QMessageBox.ButtonRole.AcceptRole)
            verifyBtn = mb.addButton(self.i18n.t("btn_verify_file"), QtWidgets.QMessageBox.ButtonRole.ActionRole)
            mb.addButton(self.i18n.t("btn_ok"), QtWidgets.QMessageBox.ButtonRole.RejectRole)
            mb.exec()

            if mb.clickedButton() == openBtn:
                QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
            elif mb.clickedButton() == verifyBtn:
                self.verifyDownloadedFile(sha_expected=sha)
        else:
            if manual:
                QtWidgets.QMessageBox.information(self, APP_NAME, self.i18n.t("up_to_date"))
        self.statusLbl.setText(self.i18n.t("ready"))

    def verifyDownloadedFile(self, sha_expected: str):
        if not sha_expected or len(sha_expected) != 64:
            QtWidgets.QMessageBox.warning(self, APP_NAME, "No SHA-256 available for this release/asset.")
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, self.i18n.t("verif_title"), "", "All files (*)")
        if not path:
            return
        try:
            got = sha256_file(path)
            if got.lower() == sha_expected.lower():
                QtWidgets.QMessageBox.information(self, self.i18n.t("verif_title"), self.i18n.t("verif_ok"))
            else:
                QtWidgets.QMessageBox.warning(self, self.i18n.t("verif_title"),
                                              self.i18n.t("verif_ko", exp=sha_expected, got=got))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, self.i18n.t("verif_title"), str(e))

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

        self.saveConfigField("device_ip", ip)
        self.saveConfigField("client_id", client_id)
        self.saveConfigField("ignore_home", bool(self.ignoreHome.isChecked()))

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
        # Sauvegarde position/tailles
        self.saveWindowStateToConfig()
        event.accept()



def main():
    QtCore.QCoreApplication.setOrganizationName(APP_ORG)
    QtCore.QCoreApplication.setApplicationName(APP_NAME)

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationDisplayName(APP_NAME) 

    settings = QtCore.QSettings(APP_ORG, APP_NAME)
    config = ConfigStore(CONFIG_FILE)

    lang = config.get("lang", settings.value("lang", I18N.FR))
    theme = config.get("theme", settings.value("theme", Theme.AUTO))

    if theme == Theme.DARK:
        apply_dark_palette(app)
    elif theme == Theme.LIGHT:
        apply_light_palette(app)
    else:
        apply_auto_palette(app)
    apply_global_stylesheet(app)

    i18n = I18N(lang=lang)
    w = MainWindow(i18n=i18n, theme=theme, config=config)
    w.setWindowTitle(APP_NAME)
    QtCore.QTimer.singleShot(0, lambda: w.setWindowTitle(APP_NAME))

    if config.get("win_size") is None:
        w.resize(880, 640)

    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
