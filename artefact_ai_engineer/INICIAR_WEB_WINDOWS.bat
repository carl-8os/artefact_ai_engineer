@echo off
setlocal
cd /d "%~dp0"
set "LLM_PROVIDER=ollama"
if not defined OLLAMA_MODEL set "OLLAMA_MODEL=qwen2.5:1.5b"
if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=py"
)
echo Local model: %OLLAMA_MODEL%
echo Ensure Ollama is installed and the model is downloaded.
echo Open http://127.0.0.1:8765 after the server starts.
"%PYTHON%" run.py --web
pause
