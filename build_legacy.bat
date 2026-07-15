@echo off
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%..\.venv-win7\Scripts\python.exe"
if not exist "%PY%" (
    echo Missing build environment: %PY%
    exit /b 1
)
cd /d "%ROOT%"
"%PY%" -m PyInstaller --noconfirm --clean jzd_extract_win7_legacy.spec
if errorlevel 1 exit /b 1
echo Built: %ROOT%dist\jzd_extract_win7_legacy.exe
endlocal
