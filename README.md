# TALAS AI

**Telaah Regulasi Berbasis Artificial Intelligence**

> ⚠️ **TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA.**
> AI adalah co-pilot ASN, bukan pengambil keputusan hukum. Semua output AI wajib diverifikasi oleh analis hukum yang berwenang.

---

## Gambaran Umum

TALAS AI adalah aplikasi telaah regulasi berbasis AI untuk membantu ASN pemerintah daerah dalam:

- Memeriksa dasar hukum Raperbup
- Menemukan potensi konflik dengan regulasi yang lebih tinggi
- Memeriksa konsistensi internal dokumen
- Membandingkan dua regulasi pasal per pasal
- Menghasilkan laporan telaah dalam format DOCX, PDF, atau JSON
- Mendukung human review atas temuan AI

**Stack:** FastAPI + SQLite + SQLAlchemy (async) + Python 3.11+

**AI:** Local-first — Ollama, LM Studio, atau Mock (offline). Cloud AI opsional.

**Privacy:** Default `LOCAL ONLY` — tidak ada data dikirim ke cloud tanpa izin eksplisit.

---

## Fase yang Sudah Diimplementasi

| Fase | Deskripsi |
|------|-----------|
| 1 | Foundation (config, database, logging) |
| 2 | Authentication & RBAC |
| 3 | Regulatory Library |
| 4 | Document Processing (PDF, DOCX) |
| 5 | Search Engine (FTS5) |
| 6 | Multi-AI Provider (Ollama, LM Studio, OpenAI-compatible, Mock) |
| 7 | RAG Engine (Retrieval-Augmented Generation) |
| 8 | Chatbot API |
| 9 | Legal Basis Checker |
| 10 | Conflict Checker |
| 11 | Consistency Checker |
| 12 | Comparison Engine |
| 13 | Human Review |
| 14 | Report Generator |
| 15 | Dashboard |
| 16 | Security / Audit / Backup |
| 17 | PWA (Progressive Web App) |
| 18 | Windows Desktop Launcher |
| 19 | Test Suite Lengkap |
| 20 | Dokumentasi Final |

---

## Instalasi

### Prasyarat

- Python 3.11+
- (Opsional) Ollama dengan model LLM

### Setup

```bash
# Clone repo
git clone https://github.com/esnpendosa/talas-ai.git
cd "talas-ai"

# Buat virtual environment
python -m venv venv

# Aktifkan venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy dan konfigurasi environment
cp .env.example .env
# Edit .env sesuai kebutuhan (minimal: SECRET_KEY)
```

### Jalankan Server

```bash
# Development
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Akses: http://localhost:8000

API Docs (development only): http://localhost:8000/docs

### Desktop Launcher (Windows)

```bash
# Pure Python launcher (tanpa GUI)
python desktop/launcher.py

# Dengan GUI PySide6 (jika terinstall)
python desktop/main.py
```

---

## API Endpoints

### Auth
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Data user saat ini |
| POST | `/api/auth/change-password` | Ganti password |

### Regulasi
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/regulations` | Daftar regulasi |
| POST | `/api/regulations` | Tambah regulasi |
| GET | `/api/regulations/{id}` | Detail regulasi |
| PUT | `/api/regulations/{id}` | Update regulasi |
| DELETE | `/api/regulations/{id}` | Hapus regulasi |

### Dokumen
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/api/documents/upload` | Upload dokumen (PDF/DOCX) |
| GET | `/api/documents` | Daftar dokumen |
| DELETE | `/api/documents/{id}` | Hapus dokumen |

### Analisis (Phase 9-13)
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/api/analysis` | Mulai analisis (LEGAL_BASIS/CONFLICT/CONSISTENCY/FULL) |
| GET | `/api/analysis/{id}` | Status analisis |
| GET | `/api/analysis/{id}/findings` | Daftar temuan |
| POST | `/api/analysis/compare` | Bandingkan dua regulasi |
| POST | `/api/findings/{id}/review` | Human review (TERIMA/TOLAK/EDIT/KOMENTAR/VERIFIKASI) |

### Chat (Phase 8)
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/api/chat` | Tanya tentang regulasi |
| GET | `/api/chat/sessions` | Daftar sesi chat |
| GET | `/api/chat/sessions/{id}/messages` | Riwayat pesan |

### Laporan (Phase 14)
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/api/reports/generate` | Generate laporan (docx/pdf/json) |
| GET | `/api/reports/{id}/download` | Download laporan |
| GET | `/api/reports` | Daftar laporan |

### Dashboard (Phase 15)
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/dashboard/stats` | Statistik dashboard |

### Admin (Phase 16)
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/audit-logs` | Daftar audit log (admin) |
| POST | `/api/backup` | Buat backup database (admin) |
| GET | `/api/backup/list` | Daftar backup (admin) |
| POST | `/api/restore` | Restore database (admin) |

---

## Status Analisis

Sistem menggunakan status berikut (tidak ada LEGAL/ILLEGAL):

| Status | Keterangan |
|--------|-----------|
| `FOUND` | Dasar hukum ditemukan |
| `NOT_FOUND` | Dasar hukum tidak ditemukan |
| `NEEDS_REVIEW` | Perlu verifikasi lebih lanjut |
| `NO_ISSUE` | Tidak ada masalah |
| `DIFFERENCE` | Ada perbedaan yang perlu dicermati |
| `POTENTIAL_CONFLICT` | Berpotensi konflik (bukan "bertentangan" secara absolut) |

---

## Human Review

Reviewer dapat melakukan aksi berikut terhadap temuan AI:

| Aksi | Efek |
|------|------|
| `TERIMA` | Set review_status = VERIFIED |
| `TOLAK` | Set review_status = REJECTED |
| `EDIT` | Update teks finding, set REVISED |
| `KOMENTAR` | Tambah catatan, set UNDER_REVIEW |
| `VERIFIKASI` | Set review_status = VERIFIED (aksi formal) |

Temuan yang sudah VERIFIED tidak dapat diubah oleh non-superuser.

---

## Struktur Laporan

Setiap laporan telaah mengikuti struktur:

```
I. IDENTITAS
II. LATAR BELAKANG
III. DASAR HUKUM
IV. MATERI MUATAN
V. HASIL ANALISIS
VI. POTENSI PERMASALAHAN
VII. REKOMENDASI
VIII. KESIMPULAN
```

Disclaimer wajib: **"TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA."**

---

## Konfigurasi AI

Edit `.env` untuk mengkonfigurasi AI:

```ini
# Privacy mode
DEFAULT_AI_MODE=local_only  # local_only | cloud_allowed | ask_before_sending

# Ollama (local)
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434

# LM Studio (local)
LMSTUDIO_ENABLED=false
LMSTUDIO_BASE_URL=http://localhost:1234

# Cloud AI (opsional, hanya jika mode != local_only)
CLOUD_AI_ENABLED=false
OPENAI_API_KEY=
```

---

## Backup & Restore

```bash
# Buat backup via script
python scripts/backup.py

# Daftar backup
python scripts/backup.py --list

# Restore (memerlukan konfirmasi)
python scripts/backup.py --restore data/backups/backup_2025-01-01_00-00-00.db --confirm
```

Atau via API (admin only):
```bash
# Buat backup
POST /api/backup

# Daftar backup
GET /api/backup/list

# Restore
POST /api/restore
{
  "backup_path": "data/backups/backup_2025-01-01_00-00-00.db",
  "confirmed": true,
  "confirmation_text": "SAYA KONFIRMASI RESTORE DATABASE"
}
```

---

## Testing

```bash
# Jalankan semua test
venv\Scripts\pytest tests/ -q

# Test spesifik
venv\Scripts\pytest tests/test_analysis.py -v
venv\Scripts\pytest tests/test_review.py -v
venv\Scripts\pytest tests/test_reports.py -v
venv\Scripts\pytest tests/test_backup.py -v
venv\Scripts\pytest tests/test_dashboard.py -v
venv\Scripts\pytest tests/test_security.py -v
```

---

## Prinsip Keamanan

1. **Privacy by default** — LOCAL ONLY mode, tidak ada data ke cloud tanpa izin
2. **Prompt injection protection** — context regulasi di-wrap dengan marker eksplisit
3. **FTS injection sanitization** — query search dibersihkan dari karakter berbahaya
4. **Security headers** — X-Content-Type-Options, X-Frame-Options, CSP, dll.
5. **Audit log** — semua aksi penting dicatat tanpa data sensitif
6. **Human in the loop** — AI tidak bisa mengubah temuan VERIFIED
7. **No LEGAL/ILLEGAL** — hanya status yang tidak bersifat final

---

## Struktur Proyek

```
talas-ai/
├── app/
│   ├── api/
│   │   ├── admin/          # Admin endpoints (users, audit, backup)
│   │   ├── ai/             # AI provider endpoints
│   │   ├── analysis/       # Analysis endpoints (Phase 9-13)
│   │   ├── auth/           # Authentication
│   │   ├── chat/           # Chatbot
│   │   ├── dashboard/      # Dashboard stats
│   │   ├── documents/      # Document management
│   │   ├── regulations/    # Regulation library
│   │   └── reports/        # Report generation
│   ├── models/             # SQLAlchemy models
│   ├── prompts/            # System prompts dan templates
│   ├── services/
│   │   ├── ai/             # AI Router dan providers
│   │   ├── analysis/       # Analysis services
│   │   ├── rag/            # RAG engine
│   │   ├── reports/        # Report generator
│   │   └── security/       # Auth, hashing, audit
│   ├── static/             # Static files (PWA)
│   ├── templates/          # HTML templates
│   ├── config.py
│   ├── dependencies.py
│   └── main.py
├── data/
│   ├── backups/
│   ├── documents/
│   ├── exports/
│   └── indexes/
├── desktop/
│   ├── launcher.py         # Pure Python launcher
│   └── main.py             # PySide6 launcher (opsional)
├── scripts/
│   ├── backup.py           # Standalone backup script
│   └── seed.py
├── tests/
│   ├── test_analysis.py
│   ├── test_auth.py
│   ├── test_backup.py
│   ├── test_dashboard.py
│   ├── test_documents.py
│   ├── test_health.py
│   ├── test_rag.py
│   ├── test_regulations.py
│   ├── test_reports.py
│   ├── test_review.py
│   └── test_security.py
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

---

## Lisensi & Disclaimer

TALAS AI adalah alat bantu telaah regulasi. Semua output adalah **TINJAUAN AWAL** yang wajib diverifikasi oleh analis hukum yang berwenang sebelum digunakan dalam pengambilan keputusan resmi.

**AI adalah co-pilot ASN, bukan pengambil keputusan hukum.**
