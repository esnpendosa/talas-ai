"""
TALAS AI — Desktop Launcher (Phase 18)
Pure Python fallback launcher — tidak memerlukan PySide6.
Menjalankan server FastAPI dan membuka browser.

PRINSIP:
- Ini hanya launcher — tidak menduplikasi business logic
- Semua logika ada di FastAPI server
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# Konfigurasi
HOST = "127.0.0.1"
PORT = 8000
APP_URL = f"http://{HOST}:{PORT}"
APP_NAME = "TALAS AI"
DISCLAIMER = "TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA."

# Root project
ROOT_DIR = Path(__file__).parent.parent


def find_python() -> str:
    """Cari Python executable di venv atau system."""
    venv_python = ROOT_DIR / "venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def start_server() -> subprocess.Popen:
    """Jalankan FastAPI server sebagai subprocess."""
    python = find_python()
    cmd = [
        python, "-m", "uvicorn",
        "app.main:app",
        "--host", HOST,
        "--port", str(PORT),
        "--workers", "1",
    ]
    print(f"[{APP_NAME}] Menjalankan server: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc


def wait_for_server(timeout: int = 30) -> bool:
    """Tunggu hingga server siap menerima koneksi."""
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((HOST, PORT), timeout=1):
                return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.5)
    return False


def open_browser() -> None:
    """Buka browser ke URL aplikasi."""
    print(f"[{APP_NAME}] Membuka browser: {APP_URL}")
    webbrowser.open(APP_URL)


def open_data_folder() -> None:
    """Buka folder data di file explorer."""
    data_dir = ROOT_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    if sys.platform == "win32":
        os.startfile(str(data_dir))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(data_dir)])
    else:
        subprocess.run(["xdg-open", str(data_dir)])


def show_status(server_proc: subprocess.Popen) -> None:
    """Tampilkan status server."""
    running = server_proc.poll() is None
    status = "BERJALAN" if running else "BERHENTI"
    print(f"[{APP_NAME}] Status server: {status}")
    print(f"[{APP_NAME}] URL: {APP_URL}")
    print(f"[{APP_NAME}] {DISCLAIMER}")


def run_backup() -> None:
    """Jalankan backup database."""
    try:
        # Import path
        sys.path.insert(0, str(ROOT_DIR))
        from app.services.backup import create_backup
        result = create_backup()
        print(f"[{APP_NAME}] Backup berhasil: {result['filename']}")
    except Exception as e:
        print(f"[{APP_NAME}] Backup gagal: {e}")


def main() -> None:
    """Entry point launcher."""
    print(f"{'='*50}")
    print(f"  {APP_NAME}")
    print(f"  Telaah Regulasi Berbasis Artificial Intelligence")
    print(f"  {DISCLAIMER}")
    print(f"{'='*50}")
    print()

    # Mulai server
    server_proc = start_server()

    print(f"[{APP_NAME}] Menunggu server siap...")
    ready = wait_for_server(timeout=30)

    if ready:
        print(f"[{APP_NAME}] Server siap di {APP_URL}")
        open_browser()
    else:
        print(f"[{APP_NAME}] Server timeout. Coba buka manual: {APP_URL}")

    print(f"\n[{APP_NAME}] Tekan Ctrl+C untuk berhenti.")
    print(f"[{APP_NAME}] Atau akses: {APP_URL}")

    try:
        server_proc.wait()
    except KeyboardInterrupt:
        print(f"\n[{APP_NAME}] Menghentikan server...")
        server_proc.terminate()
        server_proc.wait(timeout=5)
        print(f"[{APP_NAME}] Server dihentikan. Sampai jumpa!")


if __name__ == "__main__":
    main()
