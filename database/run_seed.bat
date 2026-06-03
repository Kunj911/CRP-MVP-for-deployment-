@echo off
title Live-Trace Database Seeder
echo ============================================================
echo   LIVE-TRACE DATABASE SEEDER
echo   Seeding live_trace_dashboard with production-ready data
echo ============================================================
echo.

:: The backend venv has pymysql and bcrypt installed
set PYTHON=..\backend\venv\Scripts\python.exe

:: Fallback to root venv if backend venv doesn't exist
if not exist "%PYTHON%" (
    set PYTHON=..\venv\Scripts\python.exe
)

:: Check that python exists
if not exist "%PYTHON%" (
    echo ERROR: No virtual environment found.
    echo Checked: ..\backend\venv\Scripts\python.exe
    echo Checked: ..\venv\Scripts\python.exe
    echo.
    echo Please install dependencies first:
    echo   cd ..\backend
    echo   pip install pymysql bcrypt
    pause
    exit /b 1
)

:: Check that seed script exists
if not exist "seed_real_data.py" (
    echo ERROR: seed_real_data.py not found in current directory.
    echo Please run this from the database\ directory.
    pause
    exit /b 1
)

echo Using Python: %PYTHON%
echo.
echo [1/2] Running seed script...
echo.
%PYTHON% -u seed_real_data.py
set SEED_EXIT=%errorlevel%
echo.

if %SEED_EXIT% EQU 0 (
    echo ============================================================
    echo   SUCCESS! Database seeded successfully.
    echo ============================================================
    echo.
    echo   You can now test login with:
    echo     Client:  kunj.fittree@gmail.com / Kunj@1234
    echo     Admin:   kunjalpesh@gmail.com / Iamtheadmin@1234
    echo.
) else (
    echo ============================================================
    echo   FAILED! Seed script exited with code: %SEED_EXIT%
    echo   Check the error output above for details.
    echo ============================================================
)

pause
