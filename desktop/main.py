"""
TALAS AI — Desktop Launcher dengan PySide6 (Phase 18)
Desktop launcher dengan system tray / window sederhana.

Graceful fallback ke launcher.py jika PySide6 tidak tersedia.

PRINSIP:
- Ini hanya launcher — tidak menduplikasi business logic
- Semua logika ada di FastAPI server
- PySide6 opsional — jika tidak ada, gunakan pure Python launcher
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
HOST = "127.0.0.1"
PORT = 8000
APP_URL = f"http://{HOST}:{PORT}"
APP_NAME = "TALAS AI"
DISCLAIMER = "TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA."


def _find_python() -> str:
    """Cari Python executable di venv atau system."""
    venv_python = ROOT_DIR / "venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _start_server() -> subprocess.Popen:
    """Jalankan FastAPI server."""
    python = _find_python()
    cmd = [
        python, "-m", "uvicorn",
        "app.main:app",
        "--host", HOST,
        "--port", str(PORT),
    ]
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _wait_server(timeout: int = 30) -> bool:
    """Tunggu server siap."""
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((HOST, PORT), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False


try:
    from PySide6.QtWidgets import (  # type: ignore
        QApplication, QMainWindow, QWidget, QVBoxLayout,
        QPushButton, QLabel, QSystemTrayIcon, QMenu,
    )
    from PySide6.QtCore import Qt, QThread, Signal  # type: ignore
    from PySide6.QtGui import QIcon, QPixmap, QColor  # type: ignore

    PYSIDE6_AVAILABLE = True

    class ServerThread(QThread):
        """Thread terpisah untuk FastAPI server."""
        status_changed = Signal(str)

        def __init__(self):
            super().__init__()
            self._proc = None

        def run(self):
            self._proc = _start_server()
            self.status_changed.emit("STARTING")
            if _wait_server():
                self.status_changed.emit("RUNNING")
            else:
                self.status_changed.emit("TIMEOUT")

        def stop(self):
            if self._proc:
                self._proc.terminate()

    class TalasWindow(QMainWindow):
        """Window utama TALAS AI launcher."""

        def __init__(self):
            super().__init__()
            self.setWindowTitle(f"{APP_NAME} — Desktop Launcher")
            self.setMinimumSize(400, 300)
            self.server_thread = None
            self._setup_ui()
            self._setup_tray()
            self._start()

        def _setup_ui(self):
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setSpacing(12)
            layout.setContentsMargins(20, 20, 20, 20)

            # Title
            title = QLabel(f"<h2>{APP_NAME}</h2>")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

            # Disclaimer
            disclaimer = QLabel(f"<small><i>{DISCLAIMER}</i></small>")
            disclaimer.setAlignment(Qt.AlignCenter)
            disclaimer.setWordWrap(True)
            layout.addWidget(disclaimer)

            # Status
            self.status_label = QLabel("Status: Memulai...")
            self.status_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.status_label)

            # URL
            url_label = QLabel(f'URL: <a href="{APP_URL}">{APP_URL}</a>')
            url_label.setOpenExternalLinks(True)
            url_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(url_label)

            layout.addStretch()

            # Buttons
            self.btn_browser = QPushButton("🌐 Buka Browser")
            self.btn_browser.clicked.connect(self._open_browser)
            layout.addWidget(self.btn_browser)

            btn_backup = QPushButton("💾 Backup Database")
            btn_backup.clicked.connect(self._run_backup)
            layout.addWidget(btn_backup)

            btn_data = QPushButton("📁 Buka Folder Data")
            btn_data.clicked.connect(self._open_data)
            layout.addWidget(btn_data)

            btn_stop = QPushButton("⏹ Hentikan Server")
            btn_stop.clicked.connect(self._stop_server)
            layout.addWidget(btn_stop)

        def _setup_tray(self):
            """Setup system tray icon."""
            # Buat icon sederhana
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor("#1a4a7a"))
            icon = QIcon(pixmap)

            self.tray = QSystemTrayIcon(icon, self)
            tray_menu = QMenu()
            tray_menu.addAction("Buka Browser", self._open_browser)
            tray_menu.addAction("Status", self._show_status_tooltip)
            tray_menu.addSeparator()
            tray_menu.addAction("Keluar", self._quit)
            self.tray.setContextMenu(tray_menu)
            self.tray.setToolTip(APP_NAME)
            self.tray.show()

        def _start(self):
            self.server_thread = ServerThread()
            self.server_thread.status_changed.connect(self._on_status_changed)
            self.server_thread.start()

        def _on_status_changed(self, status: str):
            msgs = {
                "STARTING": "Status: Memulai server...",
                "RUNNING": f"Status: ✅ Berjalan di {APP_URL}",
                "TIMEOUT": "Status: ⚠️ Timeout — coba buka manual",
            }
            self.status_label.setText(msgs.get(status, f"Status: {status}"))
            if status == "RUNNING":
                self.tray.showMessage(APP_NAME, f"Server siap di {APP_URL}")

        def _open_browser(self):
            webbrowser.open(APP_URL)

        def _show_status_tooltip(self):
            self.tray.showMessage(APP_NAME, self.status_label.text())

        def _run_backup(self):
            """Jalankan backup via subprocess."""
            python = _find_python()
            subprocess.Popen([python, str(ROOT_DIR / "scripts" / "backup.py")],
                             cwd=str(ROOT_DIR))
            self.status_label.setText("Status: Backup dimulai...")

        def _open_data(self):
            data_dir = ROOT_DIR / "data"
            data_dir.mkdir(exist_ok=True)
            if sys.platform == "win32":
                os.startfile(str(data_dir))

        def _stop_server(self):
            if self.server_thread:
                self.server_thread.stop()
            self.status_label.setText("Status: Server dihentikan.")

        def _quit(self):
            self._stop_server()
            QApplication.quit()

        def closeEvent(self, event):
            # Minimize to tray instead of closing
            event.ignore()
            self.hide()
            self.tray.showMessage(APP_NAME, "TALAS AI berjalan di background.")

    def main():
        """Entry point PySide6."""
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setQuitOnLastWindowClosed(False)
        window = TalasWindow()
        window.show()
        sys.exit(app.exec())

except ImportError:
    PYSIDE6_AVAILABLE = False
    print(f"[{APP_NAME}] PySide6 tidak tersedia. Menggunakan pure Python launcher...")
    print(f"[{APP_NAME}] Install: pip install PySide6")
    print(f"[{APP_NAME}] {DISCLAIMER}")

    def main():
        """Fallback ke pure Python launcher."""
        from desktop.launcher import main as launcher_main
        launcher_main()


if __name__ == "__main__":
    main()
