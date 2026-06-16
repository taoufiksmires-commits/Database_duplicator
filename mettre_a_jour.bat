@echo off
cd /d "%~dp0"
echo Mise a jour de MySQLSync...
git pull origin master
echo.
echo Mise a jour terminee ! Relancez python main.py
pause