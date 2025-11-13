# src/models/monitoring_logic.py

import platform
import subprocess
import logging
import shutil

CONTADOR_ADVERTENCIA = 2
CONTADOR_ERROR = 3

def ping_dispositivo(ip: str) -> bool:
    
    if shutil.which('ping') is None:
        logging.warning("El comando 'ping' no está disponible en el sistema.")
        return False

    system = platform.system().lower()
    if system == 'windows':
        command = ['ping', '-n', '1', '-w', '1000', ip]
    else:
        command = ['ping', '-c', '1', '-W', '1', ip]
    
    creation_flags = 0
    if system == 'windows':
        # evadir ventana en Windows
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW
        except AttributeError:
            creation_flags = 0
        
    try:
        resultado = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=2,
            creationflags=creation_flags
        )
        return resultado.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception as e:
        logging.error(f"Error al ejecutar ping: {e}")
        return False

def ip_to_int_tuple(ip: str) -> tuple:
    
    try:
        return tuple(int(part) for part in ip.split('.'))
    except (ValueError, AttributeError):
        return (0, 0, 0, 0)