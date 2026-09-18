@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_tools\build_windows_v1_0_0.ps1" -ProjectRoot "%~dp0.."
pause
