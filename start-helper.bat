@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
set PIP_NO_CACHE_DIR=1
if not exist ".local-data\tmp" mkdir ".local-data\tmp"
if not exist ".local-data\tmp" goto failed
set "TEMP=%CD%\.local-data\tmp"
set "TMP=%TEMP%"
title Mongol - local helper
echo =============================================
echo  МОНГОЛ ХЭЛ: локальный помощник
echo =============================================
echo.
if not exist "local-helper\helper.py" goto missingfiles
if exist ".venv\Scripts\python.exe" goto dependencies

echo Подготавливаем программу. Это делается только при первом запуске.
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 goto usepy
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 goto usepython
echo Не найден Python версии 3.10 или новее.
echo Установите Python и включите Add Python to PATH, затем запустите файл снова.
goto failed

:usepy
py -3 -m venv ".venv"
if errorlevel 1 goto failed
goto dependencies

:usepython
python -m venv ".venv"
if errorlevel 1 goto failed

:dependencies
".venv\Scripts\python.exe" -c "import pypdf; from importlib.metadata import version; import sys; sys.exit(0 if 5 <= int(version('pypdf').split('.')[0]) < 7 else 1)" >nul 2>&1
if not errorlevel 1 goto run
echo Устанавливаем необходимый модуль. Нужно подключение к интернету.
".venv\Scripts\python.exe" -m pip install -r "local-helper\requirements.txt"
if errorlevel 1 goto failed

:run
echo.
echo Помощник запущен для сайта https://mongol-b2s.pages.dev
echo Скопируйте токен ниже в админку. Не отправляйте его другим людям.
echo Оставьте это окно открытым во время работы.
echo.
".venv\Scripts\python.exe" "local-helper\helper.py" --origin https://mongol-b2s.pages.dev
if errorlevel 1 goto failed
echo Помощник остановлен.
pause
goto end

:missingfiles
echo Не найдены файлы помощника. Распакуйте весь архив, а не только этот файл.
:failed
echo.
echo Не удалось запустить помощник. Проверьте сообщение выше.
echo Если нужна помощь, сделайте скриншот, предварительно скрыв токен.
pause
:end
endlocal
