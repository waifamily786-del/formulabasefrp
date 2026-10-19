@echo off
title FormulaBase Nexus - ERP + POS System
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║       FORMULABASE NEXUS - Multi-Brand ERP + POS             ║
echo  ║       Smart PDF Invoice Engine  ·  Auto-Accountant          ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

:: Change to the project directory
cd /d "%~dp0"

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

:: Check for pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip is not available.
    pause
    exit /b 1
)

:: Install backend dependencies if needed
echo [1/4] Checking backend dependencies...
pip install -r backend\requirements.txt --quiet --no-warn-script-location
if %errorlevel% neq 0 (
    echo [WARNING] Some dependencies may have failed to install.
)
echo       Done.

:: Create required directories
echo [2/4] Creating directories...
if not exist "backend\database" mkdir "backend\database"
if not exist "backend\modules\pdf_invoice_engine\templates" mkdir "backend\modules\pdf_invoice_engine\templates"
if not exist "backend\modules\pdf_invoice_engine\fonts" mkdir "backend\modules\pdf_invoice_engine\fonts"
if not exist "backend\data\invoices_output" mkdir "backend\data\invoices_output"
if not exist "backend\data\uploads" mkdir "backend\data\uploads"
echo       Done.

:: Generate PDF invoice templates if they don't exist
echo [3/4] Generating sample PDF invoice templates...
if not exist "backend\modules\pdf_invoice_engine\templates\SARA_Invoice_Template.pdf" (
    python generate_pdf_templates.py
) else (
    echo       Templates already exist - skipping generation.
)

:: Start FastAPI backend
echo [4/4] Starting FormulaBase Nexus API Server...
echo.
echo  API Server: http://127.0.0.1:8765
echo  API Docs:   http://127.0.0.1:8765/api/docs
echo  Health:     http://127.0.0.1:8765/api/health
echo.
echo  Default Login: admin / admin123
echo  Brand Profiles: SARA (Emerald Green) + LMN (Citrus Orange)
echo.
echo  Press Ctrl+C to stop the server.
echo  ─────────────────────────────────────────────────────────────
echo.

cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8765 --reload --log-level info

pause
