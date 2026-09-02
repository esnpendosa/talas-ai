"""
TALAS AI — Standalone Backup Script
Jalankan sebagai script mandiri untuk backup database.

Usage:
    python scripts/backup.py
    python scripts/backup.py --list
    python scripts/backup.py --restore /path/to/backup.db
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Tambahkan root project ke path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


def main():
    parser = argparse.ArgumentParser(
        description="TALAS AI — Database Backup & Restore",
        epilog="TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA.",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Tampilkan daftar backup yang tersedia"
    )
    parser.add_argument(
        "--restore",
        metavar="BACKUP_PATH",
        help="Restore dari file backup (memerlukan --confirm)",
    )
    parser.add_argument(
        "--confirm", action="store_true",
        help="Konfirmasi restore (wajib untuk --restore)",
    )
    args = parser.parse_args()

    from app.services.backup import create_backup, list_backups, restore_backup

    if args.list:
        backups = list_backups()
        if not backups:
            print("Tidak ada backup yang tersedia.")
            return
        print(f"\nDaftar Backup ({len(backups)} file):")
        print("-" * 60)
        for b in backups:
            size_kb = b["size_bytes"] / 1024
            print(f"  {b['filename']}")
            print(f"    Path: {b['path']}")
            print(f"    Ukuran: {size_kb:.1f} KB")
            print(f"    Dibuat: {b['created_at']}")
            print()
        return

    if args.restore:
        if not args.confirm:
            print("PERINGATAN: Restore akan menggantikan database saat ini.")
            print("Gunakan --confirm untuk melanjutkan:")
            print(f"  python scripts/backup.py --restore {args.restore} --confirm")
            sys.exit(1)

        print(f"Merestore database dari: {args.restore}")
        result = restore_backup(args.restore, confirmed=True)
        print(f"✅ Restore berhasil!")
        print(f"   Database: {result['database_path']}")
        if result.get("pre_restore_backup"):
            print(f"   Pre-restore backup: {result['pre_restore_backup']}")
        print(f"\n⚠️  Restart aplikasi untuk menggunakan database yang direstored.")
        return

    # Default: buat backup
    print("TALAS AI — Membuat backup database...")
    try:
        result = create_backup()
        print(f"✅ Backup berhasil!")
        print(f"   File: {result['filename']}")
        print(f"   Path: {result['path']}")
        print(f"   Ukuran: {result['size_bytes'] / 1024:.1f} KB")
        print(f"   Waktu: {result['created_at']}")
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Backup gagal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
