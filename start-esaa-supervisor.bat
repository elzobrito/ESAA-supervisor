@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"
set "BACKEND_PY=python"

if exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
  set "BACKEND_PY=%BACKEND_DIR%\venv\Scripts\python.exe"
)

if not exist "%BACKEND_DIR%\.env" if exist "%BACKEND_DIR%\.env.example" (
  copy /Y "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
)

if not exist "%FRONTEND_DIR%\.env" if exist "%FRONTEND_DIR%\.env.example" (
  copy /Y "%FRONTEND_DIR%\.env.example" "%FRONTEND_DIR%\.env" >nul
)

echo Iniciando ESAA Supervisor...
echo Backend: http://localhost:8000
echo Frontend: execute em outra janela; a URL final sera mostrada pelo Vite.

start "ESAA Backend" cmd /k "cd /d ""%BACKEND_DIR%"" && ""%BACKEND_PY%"" -m uvicorn app.main:app --reload"
start "ESAA Frontend" cmd /k "cd /d ""%FRONTEND_DIR%"" && npm run dev"

endlocal
