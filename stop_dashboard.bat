@echo off
REM =====================================
REM  Detener proceso del dashboard
REM =====================================
echo Deteniendo dashboard...
taskkill /IM python.exe /F
echo Dashboard detenido correctamente.
pause
