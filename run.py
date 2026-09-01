"""
TALAS AI — Application Runner
Jalankan: python run.py
"""
import os
import sys
from pathlib import Path

# Tambahkan root directory ke Python path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))


def check_environment():
    """Periksa environment sebelum menjalankan aplikasi."""
    # Periksa .env file
    env_file = ROOT_DIR / ".env"
    if not env_file.exists():
        print("⚠️  File .env tidak ditemukan.")
        print("   Menyalin .env.example ke .env...")
        env_example = ROOT_DIR / ".env.example"
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print("   ✓ .env berhasil dibuat dari .env.example")
            print("   ⚠️  Harap ubah SECRET_KEY sebelum production!")
        else:
            print("   ✗ .env.example juga tidak ditemukan!")
            sys.exit(1)

    # Periksa Python version
    if sys.version_info < (3, 12):
        print(f"⚠️  Python 3.12+ diperlukan. Versi saat ini: {sys.version}")
        print("   Melanjutkan, namun mungkin ada masalah kompatibilitas.")


def main():
    """Entry point utama."""
    import argparse

    parser = argparse.ArgumentParser(
        description="TALAS AI — Telaah Regulasi Berbasis Artificial Intelligence"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host server (default dari .env: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port server (default dari .env: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Auto-reload saat file berubah (development only)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Jumlah worker processes",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Jalankan seed database sebelum start",
    )

    args = parser.parse_args()

    # Periksa environment
    check_environment()

    # Import setelah environment check
    import uvicorn
    from app.config import settings

    host = args.host or settings.HOST
    port = args.port or settings.PORT
    workers = args.workers or settings.WORKERS
    reload = args.reload or settings.DEBUG

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   TALAS AI v{settings.APP_VERSION:<51}║
║   {settings.APP_TAGLINE:<60}║
║                                                              ║
║   Environment : {settings.ENVIRONMENT:<45}║
║   AI Privacy  : {settings.DEFAULT_AI_MODE:<45}║
║   Server      : http://{host}:{port:<38}║
║   Docs        : http://{host}:{port}/docs{' ' * 32}║
║                                                              ║
║   ⚠️  TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    if args.seed:
        print("🌱 Menjalankan seed database...")
        import asyncio

        async def _seed():
            from app.database.connection import init_database, create_all_tables
            import app.models  # noqa: F401
            init_database(settings.DATABASE_URL, settings.DATABASE_ECHO)
            await create_all_tables()
            try:
                from scripts.seed import run_seed
                await run_seed()
                print("✓ Seed database selesai.")
            except Exception as e:
                print(f"✗ Seed gagal: {e}")

        asyncio.run(_seed())

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload and workers == 1,  # reload tidak kompatibel dengan multi-worker
        workers=workers if not reload else 1,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
