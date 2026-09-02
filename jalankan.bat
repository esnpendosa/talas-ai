@echo off
setlocal

echo ============================================================
echo   TALAS AI v1.0.0
echo   Telaah Regulasi Berbasis Artificial Intelligence
echo ============================================================
echo.

REM Masuk ke folder script ini berada
cd /d "%~dp0"

REM Cek venv
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment tidak ditemukan.
    echo Jalankan install.bat terlebih dahulu.
    echo.
    pause
    exit /b 1
)

REM Cek .env
if not exist ".env" (
    echo [PERINGATAN] File .env tidak ditemukan.
    echo Menyalin dari .env.example...
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo File .env berhasil dibuat. Disarankan untuk mengedit SECRET_KEY.
    )
)

echo Menjalankan server...
echo Setelah server siap, buka browser dan akses: http://127.0.0.1:8000
echo Tekan Ctrl+C untuk menghentikan server.
echo.

call venv\Scripts\activate.bat
python run.py

echo.
echo Server dihentikan.
pause
