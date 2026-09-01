"""
TALAS AI — Database Seed Script
Membuat data awal: roles, permissions, admin user, sample regulation metadata.
PENTING: Jangan masukkan password production hardcoded di sini.
"""
import asyncio
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

logger = logging.getLogger("talas_ai.seed")


# ------------------------------------------------------------------ #
# Role & Permission Definitions
# ------------------------------------------------------------------ #

PERMISSIONS = [
    # Format: (resource, action, description)
    ("regulations", "read", "Lihat regulasi"),
    ("regulations", "write", "Tambah/edit regulasi"),
    ("regulations", "delete", "Hapus regulasi"),
    ("documents", "read", "Lihat dokumen"),
    ("documents", "upload", "Upload dokumen"),
    ("documents", "delete", "Hapus dokumen"),
    ("analysis", "read", "Lihat hasil analisis"),
    ("analysis", "run", "Jalankan analisis AI"),
    ("analysis", "delete", "Hapus analisis"),
    ("review", "read", "Lihat review"),
    ("review", "write", "Buat/edit review"),
    ("reports", "read", "Lihat laporan"),
    ("reports", "generate", "Generate laporan"),
    ("reports", "download", "Download laporan"),
    ("chat", "use", "Gunakan chatbot"),
    ("users", "read", "Lihat pengguna"),
    ("users", "write", "Tambah/edit pengguna"),
    ("users", "delete", "Hapus pengguna"),
    ("audit_logs", "read", "Lihat audit log"),
    ("settings", "read", "Lihat pengaturan"),
    ("settings", "write", "Ubah pengaturan"),
    ("ai_config", "read", "Lihat konfigurasi AI"),
    ("ai_config", "write", "Ubah konfigurasi AI"),
    ("backup", "create", "Buat backup"),
    ("backup", "restore", "Restore backup"),
]

ROLES = [
    {
        "name": "admin",
        "display_name": "Administrator",
        "description": "Akses penuh ke semua fitur sistem.",
        "permissions": "all",  # semua permission
    },
    {
        "name": "analis_hukum",
        "display_name": "Analis Hukum",
        "description": "Dapat menjalankan analisis, review, dan generate laporan.",
        "permissions": [
            "regulations:read", "regulations:write",
            "documents:read", "documents:upload",
            "analysis:read", "analysis:run",
            "review:read", "review:write",
            "reports:read", "reports:generate", "reports:download",
            "chat:use",
            "ai_config:read",
        ],
    },
    {
        "name": "opd",
        "display_name": "OPD (Perangkat Daerah)",
        "description": "Dapat upload dokumen dan melihat hasil analisis.",
        "permissions": [
            "regulations:read",
            "documents:read", "documents:upload",
            "analysis:read",
            "reports:read", "reports:download",
            "chat:use",
        ],
    },
    {
        "name": "reviewer",
        "display_name": "Reviewer",
        "description": "Dapat mereview dan memverifikasi temuan AI.",
        "permissions": [
            "regulations:read",
            "documents:read",
            "analysis:read",
            "review:read", "review:write",
            "reports:read", "reports:download",
            "chat:use",
        ],
    },
    {
        "name": "pimpinan",
        "display_name": "Pimpinan",
        "description": "Dapat melihat dashboard dan laporan.",
        "permissions": [
            "regulations:read",
            "analysis:read",
            "reports:read", "reports:download",
        ],
    },
]

DEFAULT_SETTINGS = [
    ("app.name", "TALAS AI", "string", "Nama aplikasi", True),
    ("app.tagline", "AI sebagai Co-Pilot ASN untuk Telaah Regulasi", "string", "Tagline", True),
    ("app.first_run_completed", "false", "boolean", "Apakah first run sudah selesai", False),
    ("ai.default_mode", "local_only", "string", "Mode privasi AI default", True),
    ("ai.disclaimer", "TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA.", "string", "Disclaimer AI", True),
    ("system.max_upload_mb", "50", "integer", "Ukuran maksimal upload (MB)", True),
]

SAMPLE_REGULATIONS = [
    {
        "jenis": "UU",
        "nomor": "23",
        "tahun": 2014,
        "judul": "Pemerintahan Daerah",
        "status": "BERLAKU",
        "level": 1,
        "catatan": "Sample data untuk demonstrasi — bukan teks asli regulasi",
    },
    {
        "jenis": "PP",
        "nomor": "12",
        "tahun": 2019,
        "judul": "Pengelolaan Keuangan Daerah",
        "status": "BERLAKU",
        "level": 2,
        "catatan": "Sample data untuk demonstrasi — bukan teks asli regulasi",
    },
    {
        "jenis": "Permendagri",
        "nomor": "77",
        "tahun": 2020,
        "judul": "Pedoman Teknis Pengelolaan Keuangan Daerah",
        "status": "BERLAKU",
        "level": 5,
        "catatan": "Sample data untuk demonstrasi — bukan teks asli regulasi",
    },
    {
        "jenis": "Raperbup",
        "nomor": "DRAFT-001",
        "tahun": 2026,
        "judul": "Pengelolaan Aset Daerah Kabupaten (Contoh Draft)",
        "status": "TIDAK_DIKETAHUI",
        "level": 9,
        "is_draft": True,
        "catatan": "Sample Raperbup untuk demonstrasi — bukan dokumen resmi",
    },
]


async def run_seed(force: bool = False) -> None:
    """
    Jalankan seed database.
    Jika force=False, skip jika data sudah ada.
    """
    from sqlalchemy import select, text
    from app.database.connection import get_session_maker
    from app.models.user import User, Role, Permission, UserRole, RolePermission
    from app.models.regulation import Regulation
    from app.models.settings import AppSettings

    session_factory = get_session_maker()

    async with session_factory() as session:
        # Cek apakah sudah di-seed
        result = await session.execute(select(Role).limit(1))
        if result.scalar_one_or_none() is not None and not force:
            logger.info("Database sudah di-seed sebelumnya. Skip.")
            return

        logger.info("Menjalankan seed database...")

        # ---- 1. Permissions ----
        permission_map = {}
        for resource, action, description in PERMISSIONS:
            name = f"{resource}:{action}"
            perm = Permission(
                name=name,
                resource=resource,
                action=action,
                description=description,
            )
            session.add(perm)
            await session.flush()
            permission_map[name] = perm
            logger.debug(f"  + Permission: {name}")

        # ---- 2. Roles ----
        role_map = {}
        for role_data in ROLES:
            role = Role(
                name=role_data["name"],
                display_name=role_data["display_name"],
                description=role_data["description"],
            )
            session.add(role)
            await session.flush()
            role_map[role_data["name"]] = role

            # Assign permissions
            perms_to_assign = []
            if role_data["permissions"] == "all":
                perms_to_assign = list(permission_map.values())
            else:
                for pname in role_data["permissions"]:
                    if pname in permission_map:
                        perms_to_assign.append(permission_map[pname])

            for perm in perms_to_assign:
                rp = RolePermission(role_id=role.id, permission_id=perm.id)
                session.add(rp)

            logger.debug(f"  + Role: {role.name} ({len(perms_to_assign)} permissions)")

        # ---- 3. Admin User ----
        # Cek apakah admin sudah ada
        admin_result = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin_user = admin_result.scalar_one_or_none()

        if admin_user is None:
            # Hash password menggunakan argon2
            try:
                from argon2 import PasswordHasher
                ph = PasswordHasher()
                hashed_pw = ph.hash("TalasAI@2024!")
            except ImportError:
                # Fallback ke passlib bcrypt
                from passlib.context import CryptContext
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                hashed_pw = pwd_context.hash("TalasAI@2024!")

            admin_user = User(
                username="admin",
                email="admin@talas.local",
                full_name="Administrator TALAS AI",
                position="Administrator Sistem",
                department="Tim IT",
                hashed_password=hashed_pw,
                is_active=True,
                is_superuser=True,
                must_change_password=True,  # Wajib ganti password saat first login
                ai_privacy_mode="local_only",
            )
            session.add(admin_user)
            await session.flush()

            # Assign admin role
            user_role = UserRole(
                user_id=admin_user.id,
                role_id=role_map["admin"].id,
            )
            session.add(user_role)
            logger.info(f"  + Admin user dibuat: admin@talas.local")
            logger.info(f"  ⚠️  Password default: TalasAI@2024! — WAJIB DIGANTI!")

        # ---- 4. Sample Regulations ----
        for reg_data in SAMPLE_REGULATIONS:
            existing = await session.execute(
                select(Regulation).where(
                    Regulation.jenis == reg_data["jenis"],
                    Regulation.nomor == reg_data.get("nomor"),
                    Regulation.tahun == reg_data.get("tahun"),
                )
            )
            if existing.scalar_one_or_none() is None:
                reg = Regulation(**reg_data)
                session.add(reg)
                logger.debug(f"  + Sample regulation: {reg_data['jenis']} {reg_data.get('nomor')} Tahun {reg_data.get('tahun')}")

        # ---- 5. Default Settings ----
        for key, value, value_type, description, is_public in DEFAULT_SETTINGS:
            existing_setting = await session.execute(
                select(AppSettings).where(AppSettings.key == key)
            )
            if existing_setting.scalar_one_or_none() is None:
                setting = AppSettings(
                    key=key,
                    value=value,
                    value_type=value_type,
                    description=description,
                    is_public=is_public,
                )
                session.add(setting)

        await session.commit()
        logger.info("✓ Seed database selesai.")
        logger.info(f"  Roles: {len(ROLES)}")
        logger.info(f"  Permissions: {len(PERMISSIONS)}")
        logger.info(f"  Sample regulations: {len(SAMPLE_REGULATIONS)}")


if __name__ == "__main__":
    import sys
    from pathlib import Path

    ROOT_DIR = Path(__file__).parent.parent
    sys.path.insert(0, str(ROOT_DIR))

    from app.config import settings
    from app.database.connection import init_database, create_all_tables
    import app.models  # noqa: F401

    from app.utils.logging import setup_logging
    setup_logging(log_dir=settings.LOG_DIR, log_level="INFO")

    async def main():
        init_database(settings.DATABASE_URL, settings.DATABASE_ECHO)
        await create_all_tables()
        await run_seed(force="--force" in sys.argv)
        print("✓ Seed selesai.")

    asyncio.run(main())
