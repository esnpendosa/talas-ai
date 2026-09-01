# PRD — TALAS AI
## Telaah Regulasi Pemerintah Daerah Berbasis Artificial Intelligence

**Versi:** 1.0  
**Tanggal:** 1 September 2026  
**Platform target:** Windows Desktop, Android, Web  
**Backend/engine:** Python  
**Database:** SQLite  
**Lisensi:** Ditentukan pemilik proyek  
**Status:** Product Requirements Document

---

# 1. Ringkasan Produk

TALAS AI (Telaah Regulasi Berbasis AI) adalah aplikasi untuk membantu ASN/analis hukum pemerintah daerah melakukan pencarian, pembacaan, perbandingan, pemeriksaan, dan telaah awal terhadap regulasi, khususnya Rancangan Peraturan Bupati (Raperbup).

Aplikasi menggunakan Python sebagai bahasa utama dan SQLite sebagai database lokal. Sistem harus dapat berjalan secara offline untuk fungsi dokumen dan database lokal, sementara fitur AI dapat menggunakan provider LLM melalui API atau model lokal.

Prinsip utama:

> AI adalah co-pilot ASN, bukan pengambil keputusan hukum.

Semua hasil AI harus diberi label "Telaah Awal AI" dan wajib diverifikasi manusia sebelum menjadi dokumen/keputusan resmi.

---

# 2. Tujuan Produk

## Tujuan utama

1. Mempercepat proses telaah awal Raperbup.
2. Memudahkan ASN menemukan dasar hukum.
3. Membantu menemukan potensi konflik/harmonisasi regulasi.
4. Membantu menemukan ketidakkonsistenan pasal, ayat, istilah, dan rujukan.
5. Menyediakan chatbot regulasi berbasis dokumen resmi.
6. Menghasilkan draft telaah yang dapat direview manusia.
7. Menyimpan histori analisis dan perubahan.
8. Menyediakan sistem yang dapat digunakan pada Windows, Android, dan browser.
9. Tetap berguna dalam kondisi offline untuk fitur non-AI.
10. Menjaga keamanan dokumen internal pemerintah.

---

# 3. Non-Goals

Versi pertama TIDAK boleh mengklaim bahwa:

- AI menentukan sah/tidak sah suatu Perbup.
- AI menggantikan analis hukum.
- AI memberikan keputusan hukum final.
- Hasil AI otomatis menjadi dokumen resmi.
- Semua jawaban AI pasti benar.

---

# 4. Target Pengguna

## 4.1 Admin

Hak:
- Mengelola pengguna.
- Mengelola role.
- Mengelola database regulasi.
- Mengelola konfigurasi AI.
- Backup/restore database.
- Melihat audit log.

## 4.2 Analis Hukum

Hak:
- Upload regulasi.
- Upload Raperbup.
- Menjalankan analisis.
- Chat dengan AI.
- Review hasil AI.
- Memberi koreksi.
- Generate telaah.
- Export dokumen.

## 4.3 OPD/Pengusul

Hak:
- Upload Raperbup.
- Mengajukan telaah.
- Melihat hasil yang diberikan kepadanya.
- Menanggapi catatan reviewer.

## 4.4 Reviewer/Pimpinan

Hak:
- Melihat hasil telaah.
- Menyetujui/menolak/meminta revisi.
- Melihat histori.
- Melihat ringkasan risiko.

---

# 5. Platform dan Arsitektur

## Rekomendasi arsitektur

Gunakan satu codebase Python sebanyak mungkin.

### Desktop Windows

Gunakan:
- Python
- PySide6
- SQLite
- FastAPI service lokal bila diperlukan

### Web

Gunakan:
- FastAPI
- HTML/CSS/JavaScript ringan atau Jinja2
- SQLite

### Android

Prioritas:
- Web/PWA responsive sebagai target utama Android.

Opsional:
- Packaging aplikasi Android dengan WebView/Python bridge setelah versi web stabil.

Jangan membuat tiga codebase bisnis yang berbeda. Business logic harus berada di service Python yang dapat digunakan bersama.

---

# 6. Tech Stack

## Core

- Python 3.12+
- SQLite
- SQLAlchemy
- Pydantic
- FastAPI
- Uvicorn

## Desktop

- PySide6

## Web

- FastAPI
- Jinja2
- HTML5
- CSS3
- Vanilla JavaScript

## PDF

- PyMuPDF
- OCR opsional: Tesseract/PaddleOCR

## DOCX

- python-docx

## PDF report

- ReportLab

## AI

Buat provider abstraction:

- OpenAI-compatible API
- Google/Gemini-compatible provider melalui adapter
- Local LLM adapter
- Mock provider untuk development

Jangan mengunci seluruh aplikasi ke satu vendor.

## RAG

Buat abstraction:

- Embedding provider
- Vector store adapter

Default MVP:
- SQLite sebagai metadata store
- local vector index menggunakan FAISS atau Chroma jika diperlukan

Jika ingin instalasi sesederhana mungkin, sediakan fallback keyword/full-text search menggunakan SQLite FTS5.

---

# 7. Prinsip Offline-First

Aplikasi harus tetap dapat:

- membuka database,
- membaca dokumen yang sudah diindeks,
- mencari regulasi,
- melihat histori,
- melakukan pencarian lokal,
- membuat draft non-AI,
- backup/restore.

tanpa internet.

Fitur yang membutuhkan internet:
- LLM cloud
- embedding cloud
- sinkronisasi server
- update regulasi online

Jika AI cloud tidak tersedia, tampilkan:

"AI tidak tersedia. Anda tetap dapat menggunakan pencarian regulasi lokal."

---

# 8. Modul Utama

## MODUL 1 — Authentication

Fitur:
- Login
- Logout
- Session
- Role-based access
- Password hashing
- Change password

Jangan menyimpan password plaintext.

Gunakan Argon2 atau bcrypt.

---

# 9. MODUL 2 — Dashboard

Dashboard menampilkan:

- Total regulasi
- Total Raperbup
- Analisis berjalan
- Analisis selesai
- Potensi masalah
- Dokumen perlu review
- Aktivitas terakhir

Contoh:

```text
REGULASI                  1.284
RAPERBUP                     27
ANALISIS SELESAI             19
PERLU REVIEW                  8
POTENSI MASALAH              42
```

---

# 10. MODUL 3 — Regulatory Library

Pengguna dapat:

- tambah regulasi,
- upload PDF,
- edit metadata,
- melihat status,
- mencari regulasi,
- melihat hubungan antarregulasi.

Metadata:

- jenis
- nomor
- tahun
- judul
- tanggal penetapan
- tanggal berlaku
- status
- sumber
- URL sumber
- file
- hash file
- catatan

Status:

- Berlaku
- Dicabut
- Diubah
- Sebagian berlaku
- Tidak diketahui

---

# 11. MODUL 4 — Document Processing

Pipeline:

```text
UPLOAD PDF
    ↓
VALIDASI
    ↓
EXTRACT TEXT
    ↓
OCR JIKA PERLU
    ↓
CLEAN TEXT
    ↓
DETECT BAB
    ↓
DETECT PASAL
    ↓
DETECT AYAT
    ↓
CHUNK
    ↓
INDEX
```

Parser harus berusaha mengenali:

- BAB
- Bagian
- Paragraf
- Pasal
- Ayat
- Huruf
- angka

Setiap chunk harus memiliki metadata:

```json
{
  "regulation_id": 1,
  "chapter": "BAB III",
  "article": "Pasal 8",
  "paragraph": "Ayat (2)",
  "page": 12,
  "text": "..."
}
```

---

# 12. MODUL 5 — Search Engine

Buat dua jenis pencarian:

## Keyword Search

Gunakan SQLite FTS5.

Contoh:

"pengelolaan keuangan daerah"

## Semantic Search

Gunakan embedding + vector index.

Hasil harus menampilkan:

- nama regulasi
- pasal
- ayat
- halaman
- potongan teks
- skor relevansi

---

# 13. MODUL 6 — RAG

RAG wajib menggunakan sumber dokumen yang tersedia di database.

Pipeline:

```text
PERTANYAAN
    ↓
QUERY PROCESSING
    ↓
RETRIEVAL
    ↓
RANKING
    ↓
CONTEXT
    ↓
LLM
    ↓
VALIDATION
    ↓
ANSWER + CITATIONS
```

AI dilarang menjawab seolah-olah memiliki sumber jika sumber tidak ditemukan.

Jika bukti tidak cukup:

"Dokumen yang tersedia belum cukup untuk memberikan kesimpulan. Silakan verifikasi regulasi terkait."

---

# 14. MODUL 7 — Chatbot Regulasi

Contoh:

User:
"Apakah Pasal 8 Raperbup ini mempunyai dasar hukum?"

AI:

```text
HASIL TELAAH AWAL

Pasal: 8
Status: PERLU REVIEW

Dasar hukum teridentifikasi:
1. UU XX/XXXX Pasal XX
2. PP XX/XXXX Pasal XX

Analisis:
...

Sumber:
[UU XX/XXXX - Pasal XX]
[PP XX/XXXX - Pasal XX]

Catatan:
Hasil AI bukan keputusan hukum final.
```

Chatbot harus mendukung:

- percakapan multi-turn,
- konteks dokumen,
- citation,
- membuka sumber,
- copy answer,
- feedback benar/salah,
- riwayat percakapan.

---

# 15. MODUL 8 — Legal Basis Checker

Tujuan:
Mengidentifikasi apakah ketentuan memiliki dasar hukum yang relevan.

Output:

- Pasal
- dasar hukum
- sumber
- status
- alasan
- confidence
- rekomendasi

Kategori:

- Ditemukan
- Tidak ditemukan
- Perlu verifikasi

Jangan menggunakan "Pasti benar" atau "Pasti salah".

---

# 16. MODUL 9 — Conflict Checker

Membandingkan Raperbup dengan:

- UU
- PP
- Perpres
- Permen
- Permendagri
- Perda
- Pergub
- Perbup lainnya

Output:

```text
POTENSI KONFLIK

Pasal 15 Ayat (2)

Raperbup:
...

Regulasi pembanding:
...

Temuan:
...

Rekomendasi:
...

Status:
PERLU REVIEW MANUSIA
```

AI harus membedakan:

- conflict
- difference
- possible conflict

Jangan menyebut "bertentangan" kecuali sistem memiliki bukti dan tetap memberi label perlu verifikasi.

---

# 17. MODUL 10 — Consistency Checker

Periksa:

- istilah,
- definisi,
- nomenklatur,
- nomor pasal,
- referensi antarpasal,
- nomor ayat,
- nama OPD,
- singkatan,
- struktur dokumen.

Contoh:

```text
Pasal 7:
"Perangkat Daerah"

Pasal 21:
"Organisasi Perangkat Daerah"

Temuan:
Istilah berbeda. Perlu pemeriksaan konsistensi.
```

---

# 18. MODUL 11 — Regulation Status Checker

Setiap sumber harus mempunyai:

- status berlaku,
- perubahan,
- pencabutan,
- penggantian,
- hubungan dengan regulasi lain.

Jika status tidak diketahui:

"Status regulasi tidak dapat diverifikasi secara otomatis."

---

# 19. MODUL 12 — Comparison

Dukungan:

- Regulasi lama vs baru
- Perbup vs Perda
- Raperbup vs regulasi lebih tinggi

Gunakan tampilan:

```text
HIJAU  = tidak berubah
KUNING = berubah
BIRU   = baru
MERAH  = perlu review
```

Warna hanya untuk UI; jangan menggunakan warna sebagai klaim legal.

---

# 20. MODUL 13 — AI Telaah Otomatis

Tombol:

"Mulai Telaah AI"

Tahapan:

1. Analisis metadata
2. Analisis struktur
3. Cari dasar hukum
4. Cari regulasi terkait
5. Conflict checking
6. Consistency checking
7. Identifikasi risiko
8. Buat rekomendasi
9. Buat ringkasan

Dashboard hasil:

```text
TOTAL PASAL              48
DASAR HUKUM TERIDENTIFIKASI 39
PERLU REVIEW               9
POTENSI KONFLIK             4
KETIDAKKONSISTENAN          7
```

---

# 21. MODUL 14 — Human Review

Setiap temuan AI harus dapat:

- Accept
- Reject
- Edit
- Add note
- Mark as verified

Contoh:

```text
AI FINDING
Pasal 15 berpotensi konflik.

Reviewer:
[Terima]
[Tolak]
[Edit]
[Catatan]
```

Status:

- AI Generated
- Under Review
- Verified
- Rejected
- Revised
- Final

---

# 22. MODUL 15 — Generate Telaah

Buat draft:

```text
TELAAH RANCANGAN PERATURAN BUPATI

I. IDENTITAS
II. LATAR BELAKANG
III. DASAR HUKUM
IV. MATERI MUATAN
V. HASIL ANALISIS
VI. POTENSI PERMASALAHAN
VII. REKOMENDASI
VIII. KESIMPULAN
```

Semua bagian yang dihasilkan AI harus diberi penanda internal bahwa konten berasal dari AI sampai reviewer memvalidasi.

Export:

- DOCX
- PDF

---

# 23. MODUL 16 — Workflow

Status dokumen:

```text
Draft
 ↓
Diajukan
 ↓
AI Analysis
 ↓
Review Analis
 ↓
Revisi
 ↓
Review Pimpinan
 ↓
Disetujui
 ↓
Final
```

Setiap perpindahan status dicatat dalam audit log.

---

# 24. MODUL 17 — Audit Trail

Catat:

- user
- waktu
- dokumen
- action
- IP/device jika tersedia
- AI provider
- model
- prompt version
- result
- perubahan reviewer

Contoh:

```text
01-09-2026 14:20
User: admin
Action: AI_ANALYSIS
Document: Raperbup-12-2026.pdf
Model: ...
Status: completed
```

---

# 25. MODUL 18 — Backup & Restore

SQLite harus dapat:

- backup manual,
- backup otomatis,
- restore,
- export database,
- integrity check.

Jangan menimpa backup lama.

Gunakan timestamp:

```text
backup_2026-09-01_1420.db
```

---

# 26. MODUL 19 — Settings

Pengaturan:

- nama pemerintah daerah
- logo
- tema
- lokasi database
- folder dokumen
- AI provider
- API key
- model
- temperature
- max tokens
- embedding provider
- backup schedule

API key jangan disimpan plaintext jika platform memungkinkan secure credential storage.

---

# 27. Database SQLite

Buat tabel minimal:

```sql
users
roles
permissions
user_roles

regulations
regulation_relationships
regulation_versions

documents
document_chunks
document_metadata

analyses
analysis_findings
analysis_sources

chat_sessions
chat_messages

reviews
review_comments

reports
report_versions

audit_logs
settings

ai_providers
ai_usage_logs
```

---

# 28. Contoh Schema Inti

## regulations

```sql
CREATE TABLE regulations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    number TEXT NOT NULL,
    year INTEGER NOT NULL,
    title TEXT NOT NULL,
    enactment_date TEXT,
    effective_date TEXT,
    status TEXT DEFAULT 'unknown',
    source_name TEXT,
    source_url TEXT,
    file_path TEXT,
    file_hash TEXT UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## documents

```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regulation_id INTEGER,
    document_type TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    processing_status TEXT DEFAULT 'pending',
    created_by INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(regulation_id) REFERENCES regulations(id),
    FOREIGN KEY(created_by) REFERENCES users(id)
);
```

## document_chunks

```sql
CREATE TABLE document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    chapter TEXT,
    section TEXT,
    article TEXT,
    paragraph TEXT,
    page_number INTEGER,
    chunk_index INTEGER,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(document_id) REFERENCES documents(id)
);
```

## analyses

```sql
CREATE TABLE analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    analysis_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    summary TEXT,
    ai_provider TEXT,
    ai_model TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(document_id) REFERENCES documents(id),
    FOREIGN KEY(created_by) REFERENCES users(id)
);
```

## analysis_findings

```sql
CREATE TABLE analysis_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    finding_type TEXT NOT NULL,
    article TEXT,
    severity TEXT,
    confidence REAL,
    finding TEXT NOT NULL,
    recommendation TEXT,
    status TEXT DEFAULT 'ai_generated',
    reviewer_note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(analysis_id) REFERENCES analyses(id)
);
```

---

# 29. AI Prompt Architecture

Jangan menyimpan prompt langsung di banyak file.

Buat:

```text
prompts/
    system.txt
    chatbot.txt
    legal_basis.txt
    conflict.txt
    consistency.txt
    report.txt
```

Setiap prompt mempunyai version:

```text
legal_basis_v1
legal_basis_v2
```

AI output harus JSON terstruktur jika memungkinkan.

Contoh:

```json
{
  "status": "perlu_review",
  "confidence": 0.84,
  "finding": "...",
  "sources": [
    {
      "regulation": "...",
      "article": "...",
      "page": 12
    }
  ],
  "recommendation": "..."
}
```

---

# 30. System Prompt AI

Gunakan prinsip berikut:

```text
Anda adalah AI Regulatory Assistant untuk membantu ASN melakukan telaah awal regulasi.

Anda bukan pejabat pembentuk peraturan dan bukan pengambil keputusan hukum.

Gunakan hanya sumber regulasi yang diberikan melalui retrieval system.

Jangan mengarang nomor peraturan, pasal, ayat, kutipan, atau sumber.

Jika sumber tidak ditemukan, nyatakan bahwa bukti tidak cukup.

Bedakan:
1. fakta dari dokumen,
2. hasil retrieval,
3. analisis AI,
4. rekomendasi,
5. hal yang membutuhkan verifikasi manusia.

Selalu tampilkan sumber yang mendukung analisis.

Jangan menyatakan suatu ketentuan pasti sah, pasti batal, atau pasti bertentangan tanpa dasar yang dapat diverifikasi.

Gunakan bahasa Indonesia formal, jelas, dan administratif.

Setiap output analisis harus diberi label:
"TELAAH AWAL AI — WAJIB VERIFIKASI MANUSIA."
```

---

# 31. UI/UX

UI harus sederhana untuk ASN dan pengguna non-teknis.

Menu:

```text
Dashboard
Regulasi
Raperbup
Telaah AI
Chatbot
Perbandingan
Review
Laporan
Pengguna
Audit Log
Pengaturan
```

Gunakan layout desktop dan mobile responsive.

---

# 32. Halaman Utama

```text
┌──────────────────────────────────────────────┐
│ TALAS AI                         👤 Admin    │
├──────────────────────────────────────────────┤
│                                              │
│  Dashboard                                   │
│                                              │
│  Regulasi     Raperbup     Telaah     Review │
│    1.284         27          19          8   │
│                                              │
│  [+ Upload Raperbup]  [💬 Tanya Regulasi]    │
│                                              │
│  Aktivitas Terbaru                           │
│  ------------------------------------------  │
│  Raperbup 12/2026 - AI Analysis selesai      │
│                                              │
└──────────────────────────────────────────────┘
```

---

# 33. Halaman Telaah

```text
Raperbup Nomor 12 Tahun 2026

[Mulai Analisis AI]

Ringkasan
---------------------------------
48 Pasal
9 Perlu Review
4 Potensi Konflik
7 Konsistensi

Temuan
---------------------------------
Pasal 8
⚠ Perlu Review

Dasar:
PP XX/XXXX Pasal XX

Analisis:
...

[Sumber]
[Terima] [Tolak] [Edit]
```

---

# 34. API Design

FastAPI endpoints:

```text
POST   /api/auth/login
POST   /api/auth/logout

GET    /api/regulations
POST   /api/regulations
GET    /api/regulations/{id}
PUT    /api/regulations/{id}
DELETE /api/regulations/{id}

POST   /api/documents/upload
GET    /api/documents/{id}
POST   /api/documents/{id}/process

POST   /api/analysis
GET    /api/analysis/{id}
GET    /api/analysis/{id}/findings

POST   /api/findings/{id}/review

POST   /api/chat
GET    /api/chat/sessions

POST   /api/reports/generate
GET    /api/reports/{id}/download

GET    /api/audit-logs
POST   /api/backup
POST   /api/restore
```

---

# 35. Security Requirements

Wajib:

- password hashing
- role-based authorization
- input validation
- file type validation
- file size limit
- path traversal protection
- SQL injection protection
- XSS protection
- CSRF protection untuk form web
- secure API key storage
- audit trail
- session timeout
- backup

PDF yang diupload tidak boleh dipercaya begitu saja.

Jangan menjalankan executable yang berasal dari upload.

---

# 36. AI Security

Implementasikan:

- prompt injection defense,
- document instruction isolation,
- source-only retrieval,
- maximum context size,
- output schema validation,
- hallucination detection,
- citation validation.

Jika PDF berisi teks seperti:

"Ignore previous instructions..."

AI harus memperlakukannya sebagai DATA/DOKUMEN, bukan instruksi sistem.

---

# 37. Testing

## Unit Test

Test:

- PDF parser
- parser Pasal
- chunker
- database
- authentication
- FTS
- RAG retrieval
- report generation

## AI Evaluation

Buat dataset pertanyaan dan jawaban terverifikasi.

Minimal:

- 50 pertanyaan mudah
- 50 pertanyaan menengah
- 50 pertanyaan kompleks

Evaluasi:

- citation accuracy
- retrieval accuracy
- hallucination rate
- answer relevance
- false positive
- false negative

---

# 38. Acceptance Criteria MVP

MVP dinyatakan selesai jika:

1. Aplikasi dapat diinstall di Windows.
2. Aplikasi dapat menjalankan SQLite tanpa server database.
3. User dapat login.
4. User dapat upload PDF.
5. Sistem dapat mengekstrak teks.
6. Sistem dapat mengenali Pasal/Ayat secara reasonable.
7. Sistem dapat melakukan pencarian.
8. Chatbot dapat menjawab berdasarkan dokumen.
9. Jawaban mempunyai citation.
10. Sistem dapat menjalankan legal basis check.
11. Sistem dapat menjalankan consistency check.
12. Sistem dapat menghasilkan finding.
13. ASN dapat review finding.
14. Sistem dapat membuat draft telaah.
15. Sistem dapat export DOCX/PDF.
16. Audit log berjalan.
17. Database dapat backup/restore.
18. UI responsive di Android melalui browser.
19. AI failure tidak membuat aplikasi crash.
20. Aplikasi memberi peringatan bahwa hasil AI wajib diverifikasi.

---

# 39. Tahapan Development

## Sprint 1 — Foundation

- Setup repository
- Python environment
- SQLite
- SQLAlchemy
- project structure
- logging
- config
- migrations

## Sprint 2 — Authentication

- User
- Role
- Login
- Permission

## Sprint 3 — Regulatory Library

- Regulation CRUD
- PDF upload
- Metadata
- Document management

## Sprint 4 — PDF Engine

- Extraction
- OCR
- Parser
- Chunking
- FTS5

## Sprint 5 — RAG

- Embedding
- Vector store
- Retriever
- Citation
- Context builder

## Sprint 6 — Chatbot

- Chat API
- Session
- Conversation
- Source citation
- Error handling

## Sprint 7 — AI Telaah

- Legal basis
- Conflict checker
- Consistency checker
- Status checker

## Sprint 8 — Review

- Findings
- Reviewer
- Comments
- Approval
- Revision

## Sprint 9 — Reporting

- Telaah generator
- DOCX
- PDF
- Report history

## Sprint 10 — Security

- Audit
- authorization
- file security
- API key security
- backup

## Sprint 11 — UI/UX

- Desktop
- responsive web
- mobile optimization

## Sprint 12 — Deployment

- Windows installer
- portable mode
- PWA
- documentation
- testing

---

# 40. Folder Structure

```text
talas-ai/
│
├── app/
│   ├── main.py
│   ├── config.py
│   │
│   ├── api/
│   ├── auth/
│   ├── database/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   │   ├── pdf/
│   │   ├── rag/
│   │   ├── ai/
│   │   ├── analysis/
│   │   └── reports/
│   │
│   ├── prompts/
│   ├── templates/
│   ├── static/
│   └── utils/
│
├── desktop/
│   └── main.py
│
├── data/
│   ├── talas.db
│   ├── documents/
│   ├── indexes/
│   └── backups/
│
├── tests/
├── scripts/
├── requirements.txt
├── .env.example
├── README.md
└── LICENSE
```

---

# 41. requirements.txt awal

```text
fastapi
uvicorn
sqlalchemy
pydantic
pydantic-settings
python-multipart
passlib
argon2-cffi
PyMuPDF
python-docx
reportlab
jinja2
python-dotenv
httpx
numpy
faiss-cpu
pytest
pytest-asyncio
PySide6
```

Jika menggunakan provider/SDK AI tertentu, tambahkan adapter sesuai provider tersebut. Jangan memasukkan API key ke source code.

---

# 42. Windows Packaging

Target:

```text
TALAS AI Setup.exe
```

Installer harus:

1. Install aplikasi.
2. Membuat folder data.
3. Membuat database SQLite.
4. Membuat shortcut.
5. Membuka aplikasi.
6. Tidak membutuhkan user memahami Python.

Gunakan PyInstaller untuk packaging dan installer Windows yang sesuai.

Sediakan dua mode:

### Standard

Aplikasi terinstall.

### Portable

Aplikasi dapat dijalankan dari folder/USB tanpa instalasi penuh, dengan catatan konfigurasi dan hak akses Windows.

---

# 43. Android

Prioritas Android adalah:

```text
PWA / Responsive Web
```

User membuka:

```text
https://server-pemda/talas
```

atau aplikasi lokal melalui jaringan internal.

UI harus mendukung:

- touchscreen
- upload PDF
- chat
- review
- dashboard
- download report

Fitur berat seperti processing PDF dan AI sebaiknya dilakukan server, bukan smartphone.

---

# 44. Deployment Modes

## Mode A — Standalone Windows

```text
Windows PC
 ├── TALAS
 ├── SQLite
 ├── Documents
 └── AI API
```

Cocok untuk prototype/internal.

## Mode B — Local Server

```text
PC/Server Pemda
      │
      ├── FastAPI
      ├── SQLite
      └── Documents
             ↑
     Windows / Android
```

## Mode C — Production Server

```text
Reverse Proxy
      ↓
FastAPI
      ↓
SQLite
      ↓
Document Storage
      ↓
RAG
      ↓
LLM Provider
```

Untuk penggunaan multi-user serius, arsitektur database dapat ditingkatkan ke PostgreSQL pada fase berikutnya, tetapi versi awal WAJIB menggunakan SQLite sesuai requirement.

---

# 45. Logging

Buat log:

```text
logs/
    application.log
    ai.log
    security.log
    audit.log
```

Jangan menulis API key, password, atau dokumen sensitif penuh ke log.

---

# 46. Error Handling

Jika AI gagal:

```text
AI SERVICE UNAVAILABLE

Analisis AI tidak dapat dilakukan saat ini.

Anda masih dapat:
✓ mencari regulasi
✓ membaca dokumen
✓ melakukan review manual
```

Jika PDF gagal:

```text
Dokumen tidak dapat diproses.

Kemungkinan:
- PDF hasil scan
- file rusak
- format tidak didukung

Silakan aktifkan OCR atau upload dokumen lain.
```

---

# 47. Prompt untuk AI Coding Agent

Gunakan prompt berikut sebagai master prompt saat meminta AI coding agent membangun aplikasi:

```text
Anda adalah Senior Python Software Architect, AI Engineer, RAG Engineer, dan UI/UX Engineer.

Bangun aplikasi bernama TALAS AI (Telaah Regulasi Berbasis Artificial Intelligence) sesuai PRD ini.

PRINSIP:
1. Gunakan Python sebagai bahasa utama.
2. Gunakan SQLite sebagai database.
3. Target utama Windows.
4. Sediakan responsive web/PWA agar dapat digunakan Android.
5. Gunakan FastAPI untuk backend.
6. Gunakan PySide6 untuk desktop Windows.
7. Gunakan SQLAlchemy.
8. Gunakan clean architecture/service layer.
9. Jangan menaruh seluruh logic dalam satu file.
10. Jangan membuat mock feature yang terlihat selesai tetapi tidak bekerja.
11. Setiap fitur harus memiliki error handling.
12. Semua AI result harus memiliki sumber/citation.
13. AI tidak boleh menjadi pengambil keputusan hukum.
14. Selalu tampilkan "Telaah Awal AI — Wajib Verifikasi Manusia."
15. Jangan mengarang regulasi, pasal, ayat, atau sumber.
16. Jika informasi tidak tersedia, nyatakan tidak tersedia.
17. Implementasikan RAG.
18. Gunakan SQLite FTS5 sebagai fallback pencarian.
19. Buat abstraction untuk LLM provider dan embedding provider.
20. Jangan mengunci kode ke satu provider AI.
21. API key tidak boleh ditulis di source code.
22. Buat .env.example.
23. Password wajib di-hash.
24. Terapkan RBAC.
25. Semua aktivitas penting masuk audit log.
26. PDF upload harus divalidasi.
27. Lindungi dari path traversal dan prompt injection.
28. Jangan mengeksekusi konten dari dokumen upload.
29. Buat unit test.
30. Buat README instalasi Windows.

KERJAKAN SECARA BERTAHAP:

PHASE 1:
Buat project structure, configuration, logging, SQLite, SQLAlchemy, migration, model dasar, dan health check.

PHASE 2:
Buat authentication dan RBAC.

PHASE 3:
Buat regulatory library dan document upload.

PHASE 4:
Buat PDF extraction, OCR fallback, regulatory parser, Pasal/Ayat detection, chunking, dan SQLite FTS5.

PHASE 5:
Buat RAG engine dan citation engine.

PHASE 6:
Buat chatbot.

PHASE 7:
Buat Legal Basis Checker.

PHASE 8:
Buat Conflict Checker.

PHASE 9:
Buat Consistency Checker.

PHASE 10:
Buat Human Review.

PHASE 11:
Buat report generator DOCX/PDF.

PHASE 12:
Buat dashboard dan responsive UI.

PHASE 13:
Buat audit log, backup/restore, security hardening.

PHASE 14:
Buat Windows packaging.

PHASE 15:
Buat PWA/mobile responsive.

SETIAP PHASE:
- Tampilkan file yang dibuat/diubah.
- Tampilkan alasan desain.
- Tulis kode lengkap.
- Jangan meninggalkan TODO kosong untuk fungsi inti.
- Jalankan test.
- Perbaiki error.
- Pastikan aplikasi tetap dapat dijalankan.
- Jangan merusak fitur fase sebelumnya.

DATABASE:
Gunakan SQLite.
Gunakan foreign key.
Gunakan index.
Gunakan migration.
Gunakan transaction.
Gunakan WAL mode jika sesuai.
Pastikan backup aman.

RAG:
Pipeline wajib:
query → retrieval → ranking → context → LLM → structured output → citation validation.

CITATION:
Setiap klaim regulasi harus dapat ditelusuri ke:
nama regulasi, nomor, tahun, pasal/ayat, dan halaman jika tersedia.

AI:
Jika evidence tidak cukup, jawab:
"Bukti regulasi yang tersedia belum cukup untuk memberikan kesimpulan."

UI:
Gunakan bahasa Indonesia.
UI sederhana, profesional, dan cocok untuk ASN.
Responsive desktop/mobile.
Jangan membuat UI berlebihan.

FINAL:
Setelah seluruh MVP selesai, berikan:
1. struktur project final,
2. instruksi instalasi Windows,
3. instruksi menjalankan web,
4. instruksi menjalankan desktop,
5. instruksi konfigurasi AI,
6. instruksi backup database,
7. test report,
8. security checklist,
9. known limitations,
10. roadmap versi 2.
```

---

# 48. Definition of Done

Fitur dianggap selesai hanya jika:

- kode berjalan,
- tidak ada error utama,
- memiliki validasi,
- memiliki error handling,
- memiliki test,
- terintegrasi dengan database,
- memiliki UI jika diperlukan,
- memiliki audit log jika menyangkut data/keputusan,
- tidak membocorkan data sensitif,
- terdokumentasi.

---

# 49. Roadmap V2

Setelah MVP stabil:

- integrasi sumber regulasi resmi,
- regulatory update engine,
- semantic regulatory graph,
- multi-daerah,
- cloud synchronization,
- PostgreSQL,
- object storage,
- local LLM,
- advanced OCR,
- analytics,
- AI feedback learning,
- SSO pemerintah,
- digital signature integration,
- notification,
- WhatsApp/Telegram notification,
- API integration dengan sistem pemerintahan yang sudah ada.

---

# 50. Prinsip Kesimpulan Produk

TALAS AI harus diposisikan sebagai:

> "Asisten digital yang membantu ASN menemukan, membandingkan, menganalisis, dan mendokumentasikan telaah regulasi dengan cepat, terstruktur, dapat ditelusuri, dan tetap berada di bawah verifikasi manusia."

Bukan:

> "AI yang menentukan apakah Perbup legal atau ilegal."

Nilai utama produk:

**Cepat + Terstruktur + Traceable + Human-in-the-loop + Secure + Offline-capable.**
