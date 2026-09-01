# TALAS AI
## Telaah Regulasi Berbasis Artificial Intelligence

> **"AI sebagai Co-Pilot ASN untuk Telaah Regulasi"**

---

### ⚠️ DISCLAIMER PENTING

**TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA.**

TALAS AI adalah alat bantu telaah awal untuk ASN pemerintah daerah. AI bukan pengambil keputusan hukum dan bukan pengganti analis hukum. Semua output AI wajib diverifikasi oleh analis hukum yang berwenang.

---

## Daftar Isi

1. [Apa itu TALAS AI](#apa-itu-talas-ai)
2. [Requirements](#requirements)
3. [Instalasi](#instalasi)
4. [Konfigurasi](#konfigurasi)
5. [Konfigurasi AI](#konfigurasi-ai)
6. [Menjalankan Aplikasi](#menjalankan-aplikasi)
7. [Akses Web](#akses-web)
8. [Akses dari Android](#akses-dari-android)
9. [Backup & Restore](#backup--restore)
10. [Testing](#testing)
11. [Keamanan](#keamanan)
12. [Keterbatasan](#keterbatasan)

---

## Apa itu TALAS AI

TALAS AI (Telaah Regulasi Berbasis Artificial Intelligence) adalah aplikasi yang membantu ASN pemerintah daerah melakukan telaah awal terhadap rancangan Peraturan Bupati dan regulasi lainnya.

### Fitur Utama

- **Perpustakaan Regulasi** — Kelola UU, PP, Perpres, Permen, Permendagri, Perda, Pergub, Perbup
- **Telaah AI** — Analisis dasar hukum, konflik, dan konsistensi regulasi
- **Chatbot Regulasi** — Tanya jawab tentang regulasi dengan sumber yang terverifikasi
- **Perbandingan Dokumen** — Bandingkan Raperbup dengan regulasi yang berlaku
- **Human Review** — Review dan verifikasi temuan AI oleh analis hukum
- **Laporan Otomatis** — Generate laporan DOCX/PDF telaah regulasi
- **Multi AI Provider** — Ollama, LM Studio, llama.cpp, Cloud (opsional)
- **Privacy First** — Default LOCAL ONLY, dokumen tidak dikirim ke cloud

---

## Requirements

### Minimum
- **OS**: Windows 10/11 (64-bit)
- **Python**: 3.12 atau lebih baru
- **RAM**: 8 GB (16 GB direkomendasikan untuk local AI)
- **Storage**: 2 GB untuk aplikasi + ruang untuk dokumen

### Untuk Local AI (Direkomendasikan)
- **Ollama** atau **LM Studio** — untuk inferensi AI lokal
- **RAM**: 16 GB+ untuk model menengah
- **VRAM**: opsional, mempercepat inferensi

---

## Instalasi

### 1. Clone atau Download Project

```bash
# Clone repository
git clone https://github.com/pemda/talas-ai.git
cd talas-ai
```

Atau extract ZIP ke folder pilihan Anda.

### 2. Install Python

Download Python 3.12+ dari https://python.org

Pastikan centang **"Add Python to PATH"** saat instalasi.

Verifikasi:
```bash
python --version
```

### 3. Buat Virtual Environment

```bash
python -m venv venv
```

### 4. Aktifkan Virtual Environment

**Windows CMD:**
```bash
venv\Scripts\activate.bat
```

**Windows PowerShell:**
```bash
venv\Scripts\Activate.ps1
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Konfigurasi .env

```bash
copy .env.example .env
```

Edit `.env` sesuai kebutuhan. Minimal ganti `SECRET_KEY`:

```
SECRET_KEY=your-very-long-random-secret-key-here
```

### 7. Inisialisasi Database

Database akan dibuat otomatis saat pertama kali menjalankan aplikasi.

Atau jalankan seed manual:

```bash
python scripts/seed.py
```

---

## Konfigurasi AI

### Menggunakan Ollama (Direkomendasikan)

1. Download Ollama dari https://ollama.ai
2. Install dan jalankan Ollama
3. Pull model pilihan:

```bash
# Model ringan (4-8 GB RAM)
ollama pull llama3.2:3b
ollama pull qwen2.5:3b

# Model menengah (8-16 GB RAM)
ollama pull llama3.2:8b
ollama pull qwen2.5:7b

# Model besar (16+ GB RAM)
ollama pull llama3.1:70b
```

4. Pastikan `.env` memiliki:
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_ENABLED=true
```

### Menggunakan LM Studio

1. Download LM Studio dari https://lmstudio.ai
2. Download model dari UI LM Studio
3. Aktifkan Local Server di LM Studio
4. Edit `.env`:
```
LMSTUDIO_BASE_URL=http://localhost:1234
LMSTUDIO_ENABLED=true
```

### Mode Privacy

```
# Hanya AI lokal (default — direkomendasikan)
DEFAULT_AI_MODE=local_only

# Izinkan cloud AI (akan minta konfirmasi setiap kali)
DEFAULT_AI_MODE=ask_before_sending

# Izinkan cloud AI tanpa konfirmasi (tidak direkomendasikan)
DEFAULT_AI_MODE=cloud_allowed
```

---

## Menjalankan Aplikasi

### Development

```bash
python run.py
```

Atau dengan opsi:

```bash
python run.py --host 127.0.0.1 --port 8000 --reload
```

### Production

```bash
python run.py --workers 4 --host 0.0.0.0 --port 8000
```

---

## Akses Web

Setelah aplikasi berjalan:

- **Aplikasi**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (development only)
- **Health Check**: http://localhost:8000/api/health

### Login Default

```
Username: admin
Password: TalasAI@2024!
```

**⚠️ WAJIB ganti password segera setelah login pertama!**

---

## Akses dari Android

TALAS AI mendukung PWA (Progressive Web App) yang dapat diakses dari browser Android.

1. Buka browser Chrome/Edge di perangkat Android
2. Akses: `http://[IP-SERVER]:8000`
3. Tap **"Add to Home Screen"** untuk install sebagai app

Pastikan server dapat diakses dari jaringan yang sama (WiFi/LAN).

---

## Backup & Restore

### Buat Backup

```bash
# Via API
POST /api/backup

# Atau via script
python scripts/backup.py
```

File backup tersimpan di: `data/backups/backup_YYYY-MM-DD_HH-MM-SS.db`

### Restore

```bash
# Via API
POST /api/restore

# Atau via script
python scripts/restore.py --file data/backups/backup_2026-01-01_12-00-00.db
```

---

## Testing

### Jalankan Semua Test

```bash
pytest
```

### Dengan Coverage Report

```bash
pytest --cov=app --cov-report=html
```

### Test Spesifik

```bash
pytest tests/test_database.py
pytest tests/test_health.py
pytest tests/test_config.py
```

---

## Keamanan

### Password Policy
- Password di-hash menggunakan Argon2
- Minimum 8 karakter
- Admin wajib ganti password saat first login

### RBAC (Role-Based Access Control)
- ADMIN — akses penuh
- ANALIS_HUKUM — analisis dan review
- OPD — upload dan lihat
- REVIEWER — review finding
- PIMPINAN — lihat laporan

### Proteksi Dokumen
- Upload divalidasi (tipe file, ukuran)
- File hash untuk deteksi duplikasi
- Path traversal protection
- Dokumen diperlakukan sebagai DATA, bukan instruksi AI

### Prompt Injection Protection
- Dokumen regulasi tidak dapat mengoverride system prompt AI
- Semua isi dokumen diperlakukan sebagai UNTRUSTED DATA

---

## Keterbatasan

1. **TALAS AI bukan sistem hukum resmi** — Output wajib diverifikasi analis hukum.
2. **AI dapat salah** — Konfidensialitas tinggi bukan jaminan kebenaran.
3. **Database regulasi harus diupdate secara manual** — AI hanya dapat menganalisis regulasi yang ada di database.
4. **OCR terbatas** — Dokumen scan dengan kualitas rendah mungkin tidak dapat diproses.
5. **Local AI membutuhkan resource** — Model besar memerlukan RAM/VRAM yang signifikan.
6. **Bukan pengganti Biro Hukum** — Gunakan TALAS AI sebagai alat bantu awal, bukan keputusan final.

---

## Struktur Project

```
talas-ai/
├── app/                    # Kode aplikasi utama
│   ├── api/               # API endpoints
│   ├── database/          # Koneksi dan konfigurasi database
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   ├── prompts/           # AI system prompts
│   ├── templates/         # HTML templates
│   ├── static/            # CSS, JS, images
│   └── utils/             # Utilities
├── data/                  # Data aplikasi (database, dokumen, dll.)
├── logs/                  # Log files
├── tests/                 # Test suite
├── scripts/               # Utility scripts
├── desktop/               # PySide6 desktop launcher
├── requirements.txt
├── .env.example
├── run.py
└── README.md
```

---

## Development Roadmap

- ✅ Phase 1: Foundation
- 🔄 Phase 2: Authentication/RBAC
- 📋 Phase 3: Regulatory Library
- 📋 Phase 4: Document Processing
- 📋 Phase 5: Search Engine
- 📋 Phase 6: Multi-AI Provider
- 📋 Phase 7: RAG
- 📋 Phase 8: Chatbot
- 📋 Phase 9-11: Legal/Conflict/Consistency Analysis
- 📋 Phase 12-14: Comparison/Review/Reports
- 📋 Phase 15-20: Dashboard/Security/PWA/Packaging

---

*TALAS AI — Membantu ASN lebih efisien, keputusan tetap di tangan manusia.*
