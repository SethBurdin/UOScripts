@echo off
start powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0PullChanges.ps1"
pause