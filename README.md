# TALAS AI
## Telaah Regulasi Berbasis Artificial Intelligence

**Tagline:** AI sebagai Co-Pilot ASN untuk Telaah Regulasi

---

## DISCLAIMER PENTING

**TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA.**

TALAS AI adalah alat bantu telaah awal regulasi untuk ASN pemerintah daerah. AI bukan pengambil keputusan hukum dan bukan pengganti analis hukum. Semua output AI wajib diverifikasi oleh analis hukum yang berwenang sebelum digunakan dalam produk hukum resmi.

---

## Daftar Isi

1. [Tentang TALAS AI](#tentang-talas-ai)
2. [Fitur Utama](#fitur-utama)
3. [Cara Menjalankan di Windows](#cara-menjalankan-di-windows)
4. [Download dan Instalasi](#download-dan-instalasi)
5. [Konfigurasi AI](#konfigurasi-ai)
6. [Mengakses Aplikasi](#mengakses-aplikasi)
7. [Akses dari Android](#akses-dari-android)
8. [Akun Default](#akun-default)
9. [Backup dan Restore](#backup-dan-restore)
10. [Panduan Penggunaan](#panduan-penggunaan)
11. [Daftar API](#daftar-api)
12. [Menjalankan Test](#menjalankan-test)
13. [Pemecahan Masalah](#pemecahan-masalah)
14. [Keterbatasan Sistem](#keterbatasan-sistem)

---

## Tentang TALAS AI

TALAS AI (Telaah Regulasi Berbasis Artificial Intelligence) membantu ASN pemerintah daerah melakukan telaah awal terhadap rancangan Peraturan Bupati dan regulasi lainnya.

Sistem ini menggunakan teknologi RAG (Retrieval-Augmented Generation) yang hanya menjawab berdasarkan dokumen yang tersedia di database. AI tidak mengarang regulasi, tidak mengarang nomor Pasal, dan tidak membuat citation palsu. Jika bukti tidak tersedia, sistem akan menyatakan bahwa bukti tidak cukup.

Prinsip utama: AI adalah co-pilot ASN. Keputusan hukum tetap di tangan manusia.

---

## Fitur Utama

- Perpustakaan regulasi: UU, PP, Perpres, Permen, Permendagri, Perda, Pergub, Perbup, Raperbup
- Upload dan ekstraksi teks PDF
- Pencarian keyword menggunakan SQLite FTS5
- Chatbot "Tanya Regulasi" dengan sumber yang dapat dilacak
- Legal Basis Checker: cek dasar hukum setiap Pasal
- Conflict Checker: deteksi potensi konflik dengan regulasi lain
- Consistency Checker: periksa konsistensi internal dokumen
- Comparison Engine: bandingkan dua regulasi pasal per pasal
- Human Review: verifikasi temuan AI oleh analis hukum
- Generate laporan DOCX/PDF/JSON
- Multi AI Provider: Ollama, LM Studio, llama.cpp, Cloud (opsional)
- Mode privasi LOCAL ONLY secara default
- PWA (Progressive Web App): dapat diinstall di Android
- Dashboard statistik
- Audit log lengkap
- Backup dan restore database

---

## Cara Menjalankan di Windows

### Persyaratan Sistem

- Windows 10 atau Windows 11 (64-bit)
- Python 3.12 atau lebih baru (Python 3.14 sudah diuji)
- RAM minimal 8 GB (16 GB direkomendasikan jika menggunakan AI lokal)
- Ruang penyimpanan minimal 2 GB

### Langkah 1: Download Source Code

**Opsi A — Menggunakan Git:**

```
git clone https://github.com/esnpendosa/talas-ai.git
cd talas-ai
```

**Opsi B — Download ZIP:**

1. Buka https://github.com/esnpendosa/talas-ai
2. Klik tombol "Code" lalu pilih "Download ZIP"
3. Ekstrak ZIP ke folder pilihan, misalnya `C:\talas-ai`
4. Buka Command Prompt, masuk ke folder tersebut:

```
cd C:\talas-ai
```

### Langkah 2: Install Python

Download Python dari https://python.org/downloads

Saat instalasi, centang opsi "Add Python to PATH".

Verifikasi instalasi:

```
python --version
```

Output yang diharapkan: `Python 3.12.x` atau lebih baru.

### Langkah 3: Buat Virtual Environment

```
python -m venv venv
```

### Langkah 4: Aktifkan Virtual Environment

**Command Prompt (CMD):**

```
venv\Scripts\activate.bat
```

**PowerShell:**

```
venv\Scripts\Activate.ps1
```

Jika PowerShell menolak karena execution policy:

```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Kemudian aktifkan ulang.

### Langkah 5: Install Dependencies

```
pip install -r requirements.txt
```

Proses ini membutuhkan koneksi internet dan mungkin memakan waktu beberapa menit.

### Langkah 6: Konfigurasi Environment

```
copy .env.example .env
```

Edit file `.env` menggunakan Notepad atau editor teks lainnya. Minimal ganti nilai `SECRET_KEY`:

```
SECRET_KEY=ganti-dengan-kunci-rahasia-panjang-dan-acak
```

Untuk generate SECRET_KEY yang aman, jalankan:

```
python -c "import secrets; print(secrets.token_hex(32))"
```

Salin hasilnya ke file `.env`.

### Langkah 7: Jalankan Aplikasi

```
python run.py
```

Aplikasi akan berjalan dan database akan dibuat secara otomatis pada startup pertama.

Output yang diharapkan:

```
TALAS AI v1.0.0
AI sebagai Co-Pilot ASN untuk Telaah Regulasi

Environment : development
AI Privacy  : local_only
Server      : http://127.0.0.1:8000
Docs        : http://127.0.0.1:8000/docs

TINJAUAN AWAL AI - WAJIB VERIFIKASI MANUSIA
```

Buka browser dan akses: `http://127.0.0.1:8000`

---

## Download dan Instalasi

### Persyaratan Sebelum Install

Sebelum menjalankan TALAS AI, pastikan hal berikut sudah tersedia:

**Python 3.12 atau lebih baru**

Download dari: https://python.org/downloads/windows

Pilih versi "Windows installer (64-bit)". Saat instalasi, centang "Add Python to PATH".

**Git (opsional, untuk update mudah)**

Download dari: https://git-scm.com/download/win

**Ollama (untuk AI lokal — direkomendasikan)**

Download dari: https://ollama.com/download/windows

Setelah install Ollama, download model AI:

```
ollama pull llama3.2:3b
```

Model ini membutuhkan sekitar 2 GB ruang penyimpanan dan RAM minimal 8 GB.

### Instalasi Otomatis dengan Script

Buat file `install.bat` dengan isi berikut, lalu jalankan dengan klik dua kali:

```batch
@echo off
echo TALAS AI - Instalasi
echo ====================

python --version
if %errorlevel% neq 0 (
    echo Python tidak ditemukan. Silakan install Python 3.12+ dari python.org
    pause
    exit
)

python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt

if not exist .env (
    copy .env.example .env
    echo File .env berhasil dibuat dari .env.example
    echo PENTING: Edit file .env dan ganti SECRET_KEY
)

echo.
echo Instalasi selesai.
echo Jalankan aplikasi dengan: python run.py
echo.
pause
```

### Menjalankan Tanpa Membuka Terminal

Buat file `jalankan.bat` di folder TALAS AI:

```batch
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python run.py
pause
```

Klik dua kali file `jalankan.bat` untuk menjalankan aplikasi tanpa perlu membuka terminal secara manual.

### Membuat Shortcut di Desktop

1. Klik kanan di desktop, pilih "New" > "Shortcut"
2. Isi lokasi: `C:\talas-ai\jalankan.bat` (sesuaikan dengan lokasi folder)
3. Beri nama shortcut: "TALAS AI"
4. Klik Finish

---

## Konfigurasi AI

### Menggunakan Ollama (Direkomendasikan untuk Penggunaan Lokal)

Ollama menjalankan model AI sepenuhnya di komputer lokal. Data tidak dikirim ke internet.

1. Install Ollama dari https://ollama.com/download/windows
2. Setelah install, Ollama berjalan otomatis di background
3. Download model (pilih salah satu sesuai kapasitas RAM):

**RAM 8 GB:**
```
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
```

**RAM 16 GB:**
```
ollama pull llama3.2:8b
ollama pull qwen2.5:7b
```

**RAM 32 GB ke atas:**
```
ollama pull llama3.1:70b
```

4. Pastikan konfigurasi di `.env`:

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_ENABLED=true
DEFAULT_AI_MODE=local_only
```

### Menggunakan LM Studio

1. Download LM Studio dari https://lmstudio.ai
2. Download model yang diinginkan melalui antarmuka LM Studio
3. Aktifkan "Local Server" di menu LM Studio
4. Edit `.env`:

```
LMSTUDIO_BASE_URL=http://localhost:1234
LMSTUDIO_ENABLED=true
```

### Mode Privasi AI

Terdapat tiga pilihan mode privasi yang dapat diatur di `.env`:

```
DEFAULT_AI_MODE=local_only
```

Pilihan:
- `local_only` — Hanya AI lokal yang digunakan. Data tidak dikirim ke internet. **Default dan direkomendasikan.**
- `ask_before_sending` — Sistem akan meminta konfirmasi sebelum mengirim data ke cloud.
- `cloud_allowed` — Mengizinkan penggunaan cloud AI tanpa konfirmasi per-request.

Untuk mengaktifkan cloud AI (misalnya OpenAI):

```
CLOUD_AI_ENABLED=true
OPENAI_API_KEY=masukkan-api-key-anda
DEFAULT_AI_MODE=ask_before_sending
```

---

## Mengakses Aplikasi

Setelah `python run.py` berhasil dijalankan:

| Halaman | URL |
|---------|-----|
| Dashboard utama | http://127.0.0.1:8000 |
| API Documentation | http://127.0.0.1:8000/docs |
| Health Check | http://127.0.0.1:8000/api/health |

Agar dapat diakses dari perangkat lain di jaringan yang sama (misalnya dari Android), ubah HOST di `.env`:

```
HOST=0.0.0.0
```

Kemudian akses menggunakan IP komputer, misalnya `http://192.168.1.100:8000`.

Untuk mengetahui IP komputer Anda, jalankan di CMD:

```
ipconfig
```

Cari baris "IPv4 Address".

---

## Akses dari Android

TALAS AI mendukung PWA (Progressive Web App) yang dapat diinstall di Android seperti aplikasi biasa.

**Langkah-langkah:**

1. Pastikan komputer dan perangkat Android terhubung ke jaringan WiFi yang sama
2. Ubah `HOST=0.0.0.0` di file `.env` dan restart server
3. Di perangkat Android, buka browser Chrome atau Edge
4. Akses URL server, misalnya `http://192.168.1.100:8000`
5. Tap menu tiga titik di browser (pojok kanan atas)
6. Pilih "Add to Home Screen" atau "Install App"
7. Konfirmasi instalasi

Aplikasi akan muncul di layar utama Android dan dapat dibuka seperti aplikasi biasa.

Fitur yang dapat digunakan dari Android:
- Dashboard statistik
- Chatbot Tanya Regulasi
- Lihat daftar regulasi
- Lihat hasil analisis
- Download laporan

---

## Akun Default

Pada startup pertama, sistem membuat akun administrator secara otomatis:

```
Username : admin
Password : TalasAI@2024!
```

**PENTING: Ganti password segera setelah login pertama.**

Cara ganti password melalui API:

```
POST /api/auth/change-password
{
  "current_password": "TalasAI@2024!",
  "new_password": "password-baru-yang-kuat"
}
```

Atau melalui antarmuka web di menu Pengaturan setelah fitur manajemen pengguna tersedia.

### Daftar Role

| Role | Akses |
|------|-------|
| admin | Akses penuh ke semua fitur |
| analis_hukum | Analisis, review, generate laporan |
| opd | Upload dokumen, lihat hasil analisis |
| reviewer | Review dan verifikasi temuan AI |
| pimpinan | Dashboard dan laporan saja |

Untuk membuat pengguna baru (memerlukan akses admin):

```
POST /api/admin/users
Authorization: Bearer {token}
{
  "username": "analis01",
  "email": "analis@pemda.go.id",
  "full_name": "Nama Lengkap",
  "password": "password-kuat",
  "role": "analis_hukum"
}
```

---

## Backup dan Restore

### Membuat Backup

Melalui API (memerlukan login admin):

```
POST /api/backup
Authorization: Bearer {token}
```

File backup tersimpan di folder `data/backups/` dengan format nama `backup_YYYY-MM-DD_HH-MM-SS.db`.

Melalui script:

```
python scripts/backup.py
```

### Melihat Daftar Backup

```
GET /api/backup/list
Authorization: Bearer {token}
```

### Restore Database

**Perhatian: Operasi ini menggantikan database yang sedang digunakan secara permanen.**

```
POST /api/restore
Authorization: Bearer {token}
{
  "backup_path": "data/backups/backup_2026-01-01_12-00-00.db",
  "confirmed": true,
  "confirmation_text": "SAYA KONFIRMASI RESTORE DATABASE"
}
```

Teks konfirmasi harus persis: `SAYA KONFIRMASI RESTORE DATABASE`

Setelah restore berhasil, restart aplikasi:

```
Ctrl+C  (hentikan server)
python run.py  (jalankan ulang)
```

---

## Panduan Penggunaan

### Alur Kerja Dasar

**1. Tambah Regulasi Referensi**

Tambahkan regulasi yang menjadi acuan (UU, PP, Perda, dll.) melalui API atau antarmuka web:

```
POST /api/regulations
Authorization: Bearer {token}
{
  "jenis": "UU",
  "nomor": "23",
  "tahun": 2014,
  "judul": "Pemerintahan Daerah",
  "status": "BERLAKU"
}
```

**2. Upload dan Proses Dokumen**

Upload file PDF regulasi:

```
POST /api/documents/upload
Authorization: Bearer {token}
Form Data:
  file: [file PDF]
  regulation_id: [ID regulasi yang dibuat di langkah 1]
```

Proses ekstraksi teks:

```
POST /api/documents/{id}/process
Authorization: Bearer {token}
```

**3. Upload Raperbup yang Akan Ditelaah**

Buat entri regulasi untuk Raperbup:

```
POST /api/regulations
{
  "jenis": "Raperbup",
  "nomor": "DRAFT-001",
  "tahun": 2026,
  "judul": "Judul Raperbup",
  "is_draft": true,
  "status": "TIDAK_DIKETAHUI"
}
```

Upload dan proses dokumen Raperbup seperti langkah 2.

**4. Jalankan Analisis AI**

```
POST /api/analysis
Authorization: Bearer {token}
{
  "regulation_id": [ID Raperbup],
  "analysis_type": "FULL"
}
```

Tipe analisis yang tersedia:
- `LEGAL_BASIS` — Cek dasar hukum setiap Pasal
- `CONFLICT` — Deteksi potensi konflik dengan regulasi lain
- `CONSISTENCY` — Periksa konsistensi internal
- `FULL` — Semua analisis sekaligus

**5. Review Temuan AI**

Lihat daftar temuan:

```
GET /api/analysis/{id}/findings
Authorization: Bearer {token}
```

Submit review untuk setiap temuan:

```
POST /api/findings/{id}/review
Authorization: Bearer {token}
{
  "action": "TERIMA",
  "notes": "Catatan reviewer"
}
```

Aksi review yang tersedia: `TERIMA`, `TOLAK`, `EDIT`, `KOMENTAR`, `VERIFIKASI`

**6. Generate Laporan**

```
POST /api/reports/generate
Authorization: Bearer {token}
{
  "analysis_id": [ID analisis],
  "format": "docx"
}
```

Format yang tersedia: `docx`, `pdf`, `json`

### Chatbot Tanya Regulasi

Kirim pertanyaan tentang regulasi:

```
POST /api/chat
Authorization: Bearer {token}
{
  "message": "Apa dasar hukum Pasal 8 terkait pengelolaan keuangan?"
}
```

Response akan menyertakan:
- Jawaban berdasarkan dokumen yang tersedia
- Sumber/citation yang dapat dilacak
- Confidence level
- Disclaimer wajib

### Perbandingan Dua Regulasi

```
POST /api/analysis/compare
Authorization: Bearer {token}
{
  "regulation_id_a": 1,
  "regulation_id_b": 2
}
```

---

## Daftar API

Dokumentasi API lengkap tersedia di: `http://127.0.0.1:8000/docs`

Ringkasan endpoint utama:

| Method | Endpoint | Keterangan |
|--------|----------|------------|
| POST | /api/auth/login | Login |
| POST | /api/auth/logout | Logout |
| GET | /api/auth/me | Profil pengguna |
| POST | /api/auth/change-password | Ganti password |
| GET | /api/regulations | Daftar regulasi |
| POST | /api/regulations | Tambah regulasi |
| GET | /api/regulations/{id} | Detail regulasi |
| PUT | /api/regulations/{id} | Update regulasi |
| DELETE | /api/regulations/{id} | Hapus regulasi |
| GET | /api/regulations/search/keyword | Cari regulasi |
| POST | /api/documents/upload | Upload PDF |
| POST | /api/documents/{id}/process | Proses ekstraksi |
| GET | /api/documents/{id} | Detail dokumen |
| GET | /api/documents/{id}/chunks | Chunk teks |
| POST | /api/analysis | Mulai analisis |
| GET | /api/analysis/{id} | Status analisis |
| GET | /api/analysis/{id}/findings | Daftar temuan |
| POST | /api/findings/{id}/review | Submit review |
| POST | /api/analysis/compare | Bandingkan regulasi |
| POST | /api/chat | Kirim pertanyaan |
| GET | /api/chat/sessions | Daftar sesi chat |
| POST | /api/reports/generate | Generate laporan |
| GET | /api/dashboard/stats | Statistik dashboard |
| GET | /api/ai/providers | Status AI provider |
| POST | /api/ai/providers/{name}/test | Test koneksi provider |
| GET | /api/ai/providers/{name}/models | Daftar model |
| POST | /api/ai/models/refresh | Refresh model list |
| GET | /api/ai/settings | Konfigurasi AI |
| POST | /api/backup | Buat backup |
| POST | /api/restore | Restore backup |
| GET | /api/audit-logs | Audit log (admin) |
| GET | /api/health | Health check |

---

## Menjalankan Test

```
venv\Scripts\pytest tests\ -q
```

Output yang diharapkan:

```
147 passed in xx.xxs
```

Test dengan laporan coverage:

```
venv\Scripts\pytest tests\ --cov=app --cov-report=html
```

Laporan coverage tersedia di folder `htmlcov/`.

---

## Pemecahan Masalah

### Aplikasi tidak bisa dijalankan (port sudah digunakan)

Jika muncul error `[WinError 10048] only one usage of each socket address`:

1. Buka Task Manager (Ctrl+Shift+Esc)
2. Tab "Details"
3. Cari proses "python.exe"
4. Klik kanan, pilih "End Task"
5. Jalankan ulang `python run.py`

Atau melalui Command Prompt (jalankan sebagai Administrator):

```
for /f "tokens=5" %a in ('netstat -aon ^| findstr :8000') do taskkill /f /pid %a
```

### Ollama tidak terdeteksi

Pastikan Ollama sudah berjalan. Buka Task Manager dan cari "ollama". Jika tidak ada, buka Ollama dari menu Start.

Cek status Ollama:

```
http://localhost:11434/api/tags
```

Jika tidak bisa diakses, jalankan ulang Ollama.

### Database bermasalah

Jika muncul error database saat startup:

```
python -c "import asyncio; from app.database.connection import init_database, create_all_tables; import app.models; asyncio.run(create_all_tables())"
```

Jika tetap bermasalah, rename file `data/talas.db` dan jalankan ulang server. Database akan dibuat ulang dari awal, namun semua data akan hilang. Pastikan sudah backup terlebih dahulu.

### Error: `TypeError: descriptor '__getitem__'` (Python 3.14)

Error ini adalah bug kompatibilitas SQLAlchemy dengan Python 3.14. Patch sudah diterapkan secara otomatis di file `venv/Lib/site-packages/sqlalchemy/util/typing.py`. Jika muncul setelah update pip, jalankan:

```
python -c "
import sqlalchemy.util.typing as sat
import sys, typing
def patched(*types):
    if sys.version_info >= (3, 14):
        if not types: return type(None)
        if len(types) == 1: return types[0]
        r = typing.Union[types[0], types[1]]
        for t in types[2:]: r = typing.Union[r, t]
        return r
    return typing.Union[types]
sat.make_union_type = patched
print('Patch berhasil')
"
```

### PDF tidak bisa diproses

Pastikan PyMuPDF terinstall:

```
pip install PyMuPDF
```

Jika PDF berupa scan (gambar), sistem akan memberikan peringatan bahwa OCR diperlukan. Fitur OCR penuh akan tersedia di versi berikutnya.

### Port berbeda

Untuk menjalankan di port selain 8000:

```
python run.py --port 9000
```

Atau ubah di `.env`:

```
PORT=9000
```

---

## Keterbatasan Sistem

1. **Output AI adalah tinjauan awal.** Semua temuan wajib diverifikasi oleh analis hukum berwenang sebelum digunakan dalam produk hukum resmi.

2. **AI tidak menggantikan Biro Hukum.** TALAS AI adalah alat bantu, bukan pengganti konsultasi hukum resmi.

3. **Akurasi bergantung pada database regulasi.** AI hanya dapat menganalisis regulasi yang sudah diupload ke sistem. Jika regulasi referensi tidak ada di database, analisis tidak akan akurat.

4. **PDF scan memerlukan OCR.** Dokumen berupa foto/scan mungkin tidak dapat diekstrak dengan baik. Gunakan PDF teks jika tersedia.

5. **Performa AI bergantung pada hardware.** Model AI yang lebih besar memberikan hasil lebih baik tetapi memerlukan RAM dan waktu lebih banyak.

6. **Tidak ada koneksi cloud secara default.** Semua pemrosesan berjalan di komputer lokal. Koneksi internet hanya diperlukan jika cloud AI dikonfigurasi secara eksplisit.

7. **Belum ada fitur autentikasi dua faktor.** Gunakan password yang kuat dan jangan bagikan akses ke pihak yang tidak berwenang.

---

## Struktur Folder

```
talas-ai/
    app/
        api/           - Endpoint API
        database/      - Koneksi dan konfigurasi database
        models/        - Model SQLAlchemy
        schemas/       - Pydantic schemas
        services/      - Business logic
        prompts/       - System prompt AI
        templates/     - Template HTML
        static/        - Aset statis (CSS, JS, ikon)
        utils/         - Utilitas
    data/
        talas.db       - Database SQLite
        documents/     - Dokumen yang diupload
        backups/       - File backup database
        exports/       - Laporan yang digenerate
        indexes/       - Indeks pencarian
    desktop/           - Launcher desktop
    logs/              - Log aplikasi
    scripts/           - Script utilitas
    tests/             - Test suite
    requirements.txt
    run.py
    .env.example
```

---

## Informasi Versi

- Versi: 1.0.0
- Status: MVP (Minimum Viable Product)
- Python: 3.12+ (diuji di Python 3.14)
- Database: SQLite dengan WAL mode
- Framework: FastAPI, SQLAlchemy, Pydantic

---

## Lisensi

MIT License. Lihat file LICENSE untuk detail.

Disclaimer tambahan: Output TALAS AI bukan merupakan pendapat hukum resmi pemerintah daerah dan wajib diverifikasi oleh pejabat yang berwenang.
