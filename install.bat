@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   TALAS AI - Script Instalasi Windows
echo   Telaah Regulasi Berbasis Artificial Intelligence
echo ============================================================
echo.

REM Cek Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak ditemukan.
    echo.
    echo Silakan download dan install Python 3.12 atau lebih baru dari:
    echo https://python.org/downloads/windows
    echo.
    echo Pastikan centang "Add Python to PATH" saat instalasi.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% ditemukan.
echo.

REM Cek apakah venv sudah ada
if exist "venv\Scripts\python.exe" (
    echo [INFO] Virtual environment sudah ada. Melewati pembuatan venv.
) else (
    echo [INFO] Membuat virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Gagal membuat virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment berhasil dibuat.
)
echo.

REM Aktifkan venv dan install dependencies
echo [INFO] Menginstall dependencies...
call venv\Scripts\activate.bat

pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [ERROR] Gagal menginstall dependencies.
    echo Coba jalankan: pip install -r requirements.txt
    pause
    exit /b 1
)
echo [OK] Dependencies berhasil diinstall.
echo.

REM Buat .env dari .env.example jika belum ada
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [OK] File .env berhasil dibuat dari .env.example.
        echo.
        echo [PENTING] Edit file .env dan ganti SECRET_KEY dengan nilai acak yang panjang.
        echo Contoh cara generate SECRET_KEY:
        echo   python -c "import secrets; print(secrets.token_hex(32))"
    ) else (
        echo [PERINGATAN] File .env.example tidak ditemukan.
    )
) else (
    echo [INFO] File .env sudah ada. Melewati pembuatan .env.
)
echo.

REM Selesai
echo ============================================================
echo   Instalasi selesai.
echo ============================================================
echo.
echo Cara menjalankan aplikasi:
echo   1. Klik dua kali file jalankan.bat
echo   ATAU
echo   2. Buka Command Prompt, masuk ke folder ini, lalu ketik:
echo      venv\Scripts\activate.bat
echo      python run.py
echo.
echo Setelah server berjalan, buka browser dan akses:
echo   http://127.0.0.1:8000
echo.
echo Login dengan:
echo   Username : admin
echo   Password : TalasAI@2024!
echo.
echo PENTING: Ganti password segera setelah login pertama.
echo.
pause
