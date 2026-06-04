@echo off
cd /d %~dp0
call .venv\Scripts\python src\main.py
pause
