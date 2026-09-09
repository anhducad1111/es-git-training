@echo off
setlocal
set PATH=%~dp0venv\Lib\site-packages\torch\lib;%PATH%
"%~dp0venv\Scripts\python.exe" "%~dp0annotate_data.py"
