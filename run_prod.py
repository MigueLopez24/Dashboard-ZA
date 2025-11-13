import sys
import os
from waitress import serve
import logging
    
# Añade el directorio actual al path para asegurar que las importaciones de 'src' funcionen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
application = app.server 
    
# Log de Waitress
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
# ----------------------------------------------------
#  Arrancar los hilos de monitoreo (¡CRÍTICO!)
# ----------------------------------------------------

from app import start_monitoring_threads 
logging.info("Arrancando hilos de monitoreo...")
start_monitoring_threads()
logging.info("Hilos de monitoreo iniciados. El servidor Waitress está listo para servir.")
    
# Servir la aplicación con Waitress
serve(application, host='0.0.0.0', port='8050', threads=16, channel_timeout=120)