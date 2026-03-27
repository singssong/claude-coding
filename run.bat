@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing packages...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo Starting TrendLens at http://localhost:8000
uvicorn app.main:app --reload
