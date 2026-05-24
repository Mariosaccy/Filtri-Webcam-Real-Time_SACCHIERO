@echo off
REM run.bat — avvia l'applicazione su Windows (doppio click o da terminale)

cd /d "%~dp0"

REM controlla se il virtualenv esiste già
if not exist "venv\Scripts\activate.bat" (
    echo [setup] creo il virtualenv...
    python -m venv venv
    if errorlevel 1 (
        echo [errore] non riesco a creare il virtualenv, controlla che python sia installato
        pause
        exit /b 1
    )
)

REM attiva il virtualenv
call venv\Scripts\activate.bat

REM installa le dipendenze
echo [setup] installo le dipendenze...
pip install --quiet -r requirements.txt

REM crea le cartelle se non esistono
if not exist "assets" mkdir assets
if not exist "scatti" mkdir scatti
if not exist "registrazioni" mkdir registrazioni

echo.
echo ============================================
echo   filtri webcam ar — in avvio...
echo   premi Q nella finestra per uscire
echo ============================================
echo.

python main.py
pause
