@echo off
ECHO Iniciando el Dashboard de Monitoreo en modo Produccion...

:: 1. Define la ruta al entorno virtual
SET VENV_PATH=.\venv\Scripts\activate.bat
SET VENV_NAME=.venv

:: Intenta activar el entorno virtual
IF EXIST %VENV_PATH% (
    CALL %VENV_PATH%
    ECHO Entorno virtual %VENV_NAME% activado.
) ELSE (
    ECHO No se encontro el entorno virtual en %VENV_PATH%. Usando Python del sistema.
)

:: 2. Navega al directorio del script para asegurar que las rutas relativas funcionen
CD /D "%~dp0"
ECHO Directorio actual: %CD%

:: 3. Ejecuta la aplicación de producción usando Waitress
python run_prod.py

:: Si el proceso termina inesperadamente, espera un momento y muestra un mensaje
ECHO.
ECHO ******************************************************
ECHO * EL DASHBOARD SE HA DETENIDO O HA OCURRIDO UN ERROR. *
ECHO ******************************************************
PAUSE