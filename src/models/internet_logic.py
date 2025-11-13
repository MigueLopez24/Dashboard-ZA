import speedtest
import logging
import time
import requests
import ipaddress
import socket
from datetime import datetime, timedelta, timezone
import urllib3
from concurrent.futures import ThreadPoolExecutor
from ..data.sql_connector import db_connection_manager, obtener_historial_sitios_web

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Configuración FortiGate ---
FORTIGATE_IP = '192.168.0.1'
API_KEY = '8w77bGkj5fHq0xpmrpgtbNr6mbs5jj'
VDOM = 'root'
API_ENDPOINT_VPN_USERS = f'https://{FORTIGATE_IP}/api/v2/monitor/vpn/ssl?vdom={VDOM}'

def monitorear_velocidad_internet(retries: int = 2, delay: int = 5) -> dict:
    # Mide la velocidad de internet usando Speedtest
    for attempt in range(retries):
        try:
            st = speedtest.Speedtest(secure=True)
            st.get_best_server()
            st.download()
            st.upload()
            
            velocidad_descarga_mbps = round(st.results.download / 1_000_000, 2)
            velocidad_carga_mbps = round(st.results.upload / 1_000_000, 2)
            ping_ms = round(st.results.ping, 2)
            
            return {
                "velocidad_descarga": velocidad_descarga_mbps,
                "velocidad_carga": velocidad_carga_mbps,
                "ping": ping_ms
            }
        except Exception as e:
            logging.warning(f"Intento {attempt + 1} de speedtest falló: {e}")
            if attempt < retries - 1:
                time.sleep(delay)

    logging.error(f"La prueba de velocidad de internet falló después de {retries} intentos.")
    return {"error": "Fallo al medir la velocidad de internet."}

def local_users() -> int:
    # Cuenta el número de PCs activas
    try:
        with db_connection_manager() as conn:
            if not conn: return 0
            cursor = conn.cursor()
            query = """
            SELECT COUNT(D.id_dispositivo)
            FROM DISPOSITIVOS AS D
            JOIN TIPOS_DISPOSITIVO AS TD ON D.TIPOS_DISPOSITIVO_id_tipo = TD.id_tipo
            JOIN ESTADOS AS E ON D.ESTADOS_id_estado = E.id_estado
            WHERE TD.nombre_tipo = 'PC' AND E.nombre_estado = 'Activo';
            """
            count = cursor.execute(query).fetchval()
            return count if count is not None else 0
    except Exception as e:
        logging.error(f"Error al contar PCs activas desde la BD: {e}")
        return 0

def vpn_users() -> dict:
    # Obtiene el número y detalles de usuarios VPN (API FortiGate).
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
    }
    vpn_data = {'count': 0, 'details': []}
    try:
        response = requests.get(API_ENDPOINT_VPN_USERS, headers=headers, verify=False, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if 'results' in data and data['results']:
            vpn_data['count'] = len(data['results'])
            vpn_data['details'] = data['results']
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al conectar con FortiGate (VPN): {e}")
    
    return vpn_data

def all_users() -> dict:
    # Consolida usuarios locales y VPN.
    vpn_data = vpn_users()
    users = {
        'remotos': vpn_data['count'],
        'empresariales': local_users(),
        'vpn_details': vpn_data['details']
    }
    return users

def get_primary_ip(hostname: str) -> str:
    try:
        _, _, ip_addresses = socket.gethostbyname_ex(hostname)
        if not ip_addresses: return hostname
        
        corporate_subnet = ipaddress.ip_network('192.168.0.0/23')

        for ip_str in ip_addresses:
            try:
                if ipaddress.ip_address(ip_str) in corporate_subnet:
                    return ip_str
            except ValueError:
                continue 

        return ip_addresses[0]
    except socket.gaierror:
        return hostname

def process_sitios_web_history(interval_seconds: int = 60, hours: int = 1) -> dict:
    """
    Construye un timeline regular (por defecto cada `interval_seconds`) para la última `hours` horas.
    Rellena en cada punto temporal el último estado conocido de cada sitio.
    Retorna {'fechas': [...], 'sitios': {direccion: [0/1, ...]}}
    """
    raw_data_result = obtener_historial_sitios_web() 
    
    if "error" in raw_data_result:
        return raw_data_result
        
    rows = raw_data_result.get('data', [])
    if not rows:
        return {'fechas': [], 'sitios': {}}

    # Normalizar filas (soporta row.attr o tupla)
    sitios_map = {}
    events_by_site = {}
    for row in rows:
        try:
            fecha = row.fecha_hora
            estado = int(row.estado)
            direccion = row.direccion
            id_sitio = row.id_dispositivo
        except Exception:
            fecha, estado, direccion, id_sitio = row
            estado = int(estado)
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        sitios_map[id_sitio] = direccion
        events_by_site.setdefault(id_sitio, []).append((fecha, estado))

    # Ordenar eventos por tiempo por sitio
    for ev_list in events_by_site.values():
        ev_list.sort(key=lambda x: x[0])

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)

    # Generar los puntos de tiempo regulares
    fechas = []
    t = start
    while t <= now:
        fechas.append(t)
        t = t + timedelta(seconds=interval_seconds)

    # Construir series por sitio rellenando con último estado conocido
    sitios_final = {}
    for id_sitio, direccion in sitios_map.items():
        events = events_by_site.get(id_sitio, [])
        idx = 0
        last_state = 1  # fallback si no hay histórico; se mantiene el comportamiento previo
        # Buscar estado inicial válido (último <= start)
        while idx < len(events) and events[idx][0] <= start:
            last_state = events[idx][1]
            idx += 1

        series = []
        for fecha_point in fechas:
            # Avanzar por eventos que ocurren <= fecha_point
            while idx < len(events) and events[idx][0] <= fecha_point:
                last_state = events[idx][1]
                idx += 1
            series.append(last_state)
        sitios_final[direccion] = series

    return {'fechas': fechas, 'sitios': sitios_final}