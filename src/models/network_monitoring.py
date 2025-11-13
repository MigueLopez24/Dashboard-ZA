# src/models/network_monitoring.py

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..data.sql_connector import obtener_dispositivos
from .monitoring_logic import ping_dispositivo, CONTADOR_ADVERTENCIA, CONTADOR_ERROR
import logging
import atexit
from ..utils.concurrency import get_shared_executor as get_executor

ultimo_estado_dispositivos = {}
lock = threading.Lock()

def _ping_and_process_device_state(dispositivo: dict) -> dict:
    """
    Realiza un ping y determina el nuevo estado con contadores.
    """
    id_dispositivo = dispositivo.get('id_dispositivo')
    ip = dispositivo.get('ip')
    nombre = dispositivo.get('nombre')
    ping_exitoso = ping_dispositivo(ip) # Usa la función del mismo paquete
    
    with lock:
        if id_dispositivo not in ultimo_estado_dispositivos:
            ultimo_estado_dispositivos[id_dispositivo] = {'contador_inactividad': 0, 'estado_final': 'Desconocido'}
        estado_anterior = ultimo_estado_dispositivos[id_dispositivo]['estado_final']
        if ping_exitoso:
            ultimo_estado_dispositivos[id_dispositivo]['contador_inactividad'] = 0
            estado_final_str = 'Activo'
        else:
            contador = ultimo_estado_dispositivos[id_dispositivo]['contador_inactividad'] + 1
            ultimo_estado_dispositivos[id_dispositivo]['contador_inactividad'] = contador
            
            if contador >= CONTADOR_ERROR:
                estado_final_str = 'Error'
            elif contador >= CONTADOR_ADVERTENCIA:
                estado_final_str = 'Advertencia'
            else:
                estado_final_str = 'Inactivo'

        ultimo_estado_dispositivos[id_dispositivo]['estado_final'] = estado_final_str
    
    # Devuelve el resultado para el procesamiento posterior (layout o update a BD)
    return {
        'id_dispositivo': id_dispositivo,
        'ip': ip,
        'nombre': nombre,
        'estado_final': estado_final_str,
        'estado_anterior': estado_anterior,
        'tipo': dispositivo.get('tipo_dispositivo'),
        'nombre_edificio': dispositivo.get('nombre_edificio'),
        'es_especial': False
    }

def monitorear_dispositivos_ping(tipo_dispositivo: str = None, agrupar_por_edificio: bool = False) -> dict:
    """
    Orquesta el monitoreo genérico y devuelve los datos procesados.
    """
    dispositivos = obtener_dispositivos(tipo_dispositivo, agrupar_por_edificio)
    return monitorear_dispositivos_ping_from_list(dispositivos)

def monitorear_dispositivos_ping_from_list(dispositivos: list) -> dict:
    """Función auxiliar que realiza el monitoreo a partir de una lista de dispositivos ya cargada."""
    if not dispositivos:
        return {"error": "No se proporcionaron dispositivos para monitorear."}
    try:
        future_to_device = {get_executor().submit(_ping_and_process_device_state, d): d for d in dispositivos}
        # Espera a que todos los pings terminen
        resultados_ping = [future.result() for future in as_completed(future_to_device)]

        # Consolidar los resultados para el layout y los updates a BD
        resultados_dashboard = {}
        updates_to_db = []
        total_activos = 0
        total_dispositivos = len(dispositivos)

        for data in resultados_ping:
            resultados_dashboard[data['ip']] = {
                'estado': data['estado_final'], 
                'tipo': data['tipo'], 
                'nombre_edificio': data['nombre_edificio'],
                'nombre': data['nombre'],
                'identifier': data.get('identifier', data['nombre']) # Asegurar que el identifier esté presente
            }
            if data['estado_final'] == 'Activo':
                total_activos += 1
            
            updates_to_db.append(data)

        resultados_finales = {
            'total_dispositivos': total_dispositivos,
            'total_activos': total_activos,
            'items': resultados_dashboard,
            'updates': updates_to_db
        }
        
        # Contrato uniforme: envolver los datos de presentación en "layout" y exponer "updates" separadamente.
        # Mantener compatibilidad: además de 'layout' y 'updates', exponer las claves esperadas
        # en el nivel superior para evitar KeyError en layouts que aún leen 'items' directamente.
        return {
            "layout": resultados_finales,
            "updates": updates_to_db,
            "items": resultados_finales['items'],
            "total_activos": resultados_finales['total_activos'],
            "total_dispositivos": resultados_finales['total_dispositivos']
        }
 
    except Exception as e:
        logging.error(f"Error en el monitoreo genérico de dispositivos: {e}")
        return {"error": f"Ocurrió un error en el monitoreo genérico: {e}"}