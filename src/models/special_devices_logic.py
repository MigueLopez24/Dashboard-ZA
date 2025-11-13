# src/models/special_devices_logic.py
from requests.auth import HTTPDigestAuth
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import requests
import xml.etree.ElementTree as ET
import winrm
import time
from zk import ZK
from datetime import datetime
import urllib3
import atexit
from ..data.sql_connector import (
    obtener_checadores_db, obtener_dvr_db, registrar_cambio_estado_sitio,
    db_connection_manager, obtener_dispositivos 
)
from .monitoring_logic import ping_dispositivo
from ..utils.concurrency import get_shared_executor as get_executor

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Variables globales de estado ---
ultimo_estado_checadores = {}
ultimo_estado_dvrs = {}
ultimo_estado_sitios = {}
ultimo_estado_servicios = {}
ultimo_estado_conmutador = {'id_dispositivo': None, 'estado': 'Desconocido'}
lock = threading.Lock()

# --- Conmutador ---
def monitorear_conmutador():
    """Monitorea el conmutador y prepara los updates a BD y datos de layout."""
    global ultimo_estado_conmutador
    updates_to_db = []
    
    try:
        dispositivos = obtener_dispositivos('Conmutador')
        
        if not dispositivos: return {"error": "No se encontró el conmutador."}
        
        conmutador = dispositivos[0]
        ip = conmutador.get('ip')
        id_conmutador = conmutador.get('id_dispositivo')
        
        ping_exitoso = ping_dispositivo(ip)
        estado_conmutador_str = "Inactivo" if not ping_exitoso else "Activo"

        with lock:
            estado_anterior_str = ultimo_estado_conmutador['estado']
            
            updates_to_db.append({
                'id_dispositivo': id_conmutador, 'estado_final': estado_conmutador_str, 'estado_anterior': estado_anterior_str,
                'tipo': 'Conmutador', 'ip': ip, 'es_especial': False
            })

            ultimo_estado_conmutador['estado'] = estado_conmutador_str
            ultimo_estado_conmutador['id_dispositivo'] = id_conmutador

        # Devolvemos solo el estado para que la capa de layout construya el HTML
        return {"layout": {"estado": estado_conmutador_str}, "updates": updates_to_db}

    except Exception as e:
        logging.error(f"Ocurrió un error al monitorear el conmutador: {e}")
        return {"error": f"Ocurrió un error al monitorear el conmutador: {e}"}

# --- Sitios Web ---
def check_website_status(url: str) -> bool:
    """Verifica el estado HTTP de un sitio web."""
    if not url: return False
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    retries = 3
    delay = 2

    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10, allow_redirects=True, verify=False, headers=headers)
            if 200 <= response.status_code < 400: return True
        
            if 400 <= response.status_code < 600:
                url_with_index = f"{url.rstrip('/')}/index.html"
                response_index = requests.get(url_with_index, timeout=10, allow_redirects=True, verify=False, headers=headers)
                if 200 <= response_index.status_code < 400: return True
                else: return False
        
        except requests.exceptions.RequestException:
            pass
        
        if attempt < retries - 1:
            time.sleep(delay)
    
    return False

def monitorear_sitios_web():
    """Orquesta el monitoreo de sitios web y prepara los updates a BD y datos de layout."""
    global ultimo_estado_sitios

    # 1. Obtener sitios desde la capa de datos
    with db_connection_manager() as conn:
        if not conn: return {"error": "No se pudo conectar a la base de datos."}
        sitios_db = []
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id_dispositivo, direccion FROM DISPOSITIVOS WHERE TIPOS_DISPOSITIVO_id_tipo = (SELECT id_tipo FROM TIPOS_DISPOSITIVO WHERE nombre_tipo = 'Sitio Web') ORDER BY direccion")
            sitios_db = cursor.fetchall()
        except Exception as e:
            return {"error": f"Error en consulta de sitios web: {e}"}

    if not sitios_db:
        return {"layout": {"resultados": [], "activos": 0, "total": 0}, "updates": []}

    # 2. Ejecutar chequeos concurrentemente
    max_workers_sites = min(12, max(2, len(sitios_db)))
    with ThreadPoolExecutor(max_workers=max_workers_sites) as executor:
        future_to_site = {executor.submit(check_website_status, site[1]): site for site in sitios_db}
    
    resultados_layout = []
    sitios_activos = 0
    updates_to_db = []
    
    with lock:
        for future in as_completed(future_to_site, timeout=120):
            id_dispositivo, direccion = future_to_site[future]
            is_up = False
            try:
                is_up = future.result()
            except Exception as exc:
                logging.error(f"Error al verificar {direccion}: {exc}")
            
            estado_final = "Error"

            if is_up:
                sitios_activos += 1
                estado_final = "Activo"
            
            resultados_layout.append({'direccion': direccion, 'estado': estado_final, 'id_dispositivo': id_dispositivo})

            estado_anterior = ultimo_estado_sitios.get(id_dispositivo, {}).get('estado', 'Desconocido')
            
            if estado_anterior != estado_final:
                registrar_cambio_estado_sitio(id_dispositivo, 1 if estado_final == "Activo" else 0)
                logging.info(f"Sitio {direccion} cambió de {estado_anterior} a {estado_final}. Registrando en la base de datos.")
            ultimo_estado_sitios[id_dispositivo] = {'estado': estado_final, 'direccion': direccion}

            updates_to_db.append({
                'id_dispositivo': id_dispositivo, 'estado_final': estado_final, 'estado_anterior': estado_anterior,
                'tipo': 'Sitio Web', 'es_especial': False
            })

    resultados_layout.sort(key=lambda x: x['direccion'])

    # 4. Devolver datos crudos para el layout
    layout_data = {
        "resultados": resultados_layout, "activos": sitios_activos, "total": len(sitios_db)
    }

    return {"layout": layout_data, "updates": updates_to_db}

# --- Checadores ---
def check_checador_status(device_info: dict) -> dict:
    """Verifica el estado de un checador ZKTeco y sincroniza la hora."""
    conn = None
    zk = ZK(device_info['direccion'], port=device_info['puerto'], timeout=10)
    
    try:
        conn = zk.connect()
        device_time = conn.get_time()
        
        server_time = datetime.now()
        desfase_segundos = abs((server_time - device_time).total_seconds())

        if desfase_segundos >= 5:
            conn.set_time(server_time)
            device_time = conn.get_time()
            desfase_segundos = abs((server_time - device_time).total_seconds())
        
        status = 'ok'
        if desfase_segundos > 60: status = 'warning'
        if desfase_segundos > 120: status = 'error'
        
        return {
            'id_reloj': device_info['id_reloj'], 'ip': device_info['direccion'], 
            'hora_reloj': device_time.strftime("%H:%M"), 'hora_servidor': server_time.strftime("%H:%M"),
            'desfase_minutos': round(desfase_segundos / 60, 2), 'status': status,
            'nombre_edificio': device_info.get('nombre_edificio', 'Desconocido'), 'estado_ping': 'Activo'
        }
    except Exception as e:
        return {
            'id_reloj': device_info['id_reloj'], 'ip': device_info['direccion'],
            'hora_reloj': 'N/A', 'hora_servidor': datetime.now().strftime("%H:%M"),
            'desfase_minutos': None, 'status': 'error',
            'nombre_edificio': device_info.get('nombre_edificio', 'Desconocido'), 'estado_ping': 'Inactivo'
        }
    finally:
        if conn and conn.is_connect:
            conn.disconnect()

def monitorear_checadores():
    """Orquesta el monitoreo de los relojes checadores y prepara los updates a BD y datos de layout."""
    global ultimo_estado_checadores

    checadores = obtener_checadores_db() # Llama a la capa de datos
    if "error" in checadores:
        return {"error": checadores["error"]}

    datos_checadores = []
    updates_to_db = []
    total_checadores = len(checadores.get('dispositivos', []))

    if total_checadores == 0:
        return {"layout": {"datos": [], "ok": 0, "total": 0}, "updates": []}

    try:
        with lock:
            for checador in checadores['dispositivos']:
                resultado = check_checador_status(checador)
                datos_checadores.append(resultado)
                
                id_reloj = resultado['id_reloj']
                
                estado_final_str = 'Activo'
                if resultado['status'] == 'warning': estado_final_str = 'Advertencia'
                elif resultado['status'] == 'error' or resultado['estado_ping'] == 'Inactivo': estado_final_str = 'Error'
                
                estado_anterior_str = ultimo_estado_checadores.get(id_reloj, 'Desconocido')
                ultimo_estado_checadores[id_reloj] = estado_final_str

                updates_to_db.append({
                    'id_dispositivo': id_reloj, 'estado_final': estado_final_str, 'estado_anterior': estado_anterior_str,
                    'tipo': 'Checador', 'es_especial': True
                })
        
    except Exception as e:
        logging.error(f"ERROR: Ocurrió un error mayor en monitorear_checadores: {e}")
        return {"error": "Error procesando checadores"}

    checadores_ok = sum(1 for d in datos_checadores if d['status'] == 'ok' and d['estado_ping'] == 'Activo')
    
    # Devolver datos crudos para el layout
    layout = {"datos": datos_checadores, "ok": checadores_ok, "total": total_checadores}
    return {"layout": layout, "updates": updates_to_db}

# --- DVR ---
def get_camera_status_from_dvr(dvr_info: dict) -> dict:
    """Obtiene el estado de las cámaras desde un DVR."""
    
    ip = dvr_info.get('direccion')
    puerto = dvr_info.get('puerto_web') 
    usuario = dvr_info.get('usuario')
    contrasena = dvr_info.get('contrasena')

    attempts = [('http', puerto)]
    
    endpoint = '/ISAPI/System/Video/inputs/channels'
    
    headers = {
        'Accept': 'application/xml',
        'User-Agent': 'Monitoring-Dashboard/1.0',
        'Connection': 'close' 
    }
    
    for protocol, current_port in attempts:
        url = f"{protocol}://{ip}:{current_port}{endpoint}"
        
        try:
            logging.info(f"Intentando {protocol.upper()} en DVR {ip} puerto {current_port} con endpoint: {endpoint}")
            
            response = requests.get(
                url,
                auth=HTTPDigestAuth(usuario, contrasena),
                headers=headers,
                timeout=20, 
                verify=False
            )
            response.raise_for_status()

            root = ET.fromstring(response.content)
            cameras = []
            
            list_container = root.find('.//{*}VideoInputChannelList') or root
            
            for channel in list_container.findall('.//{*}VideoInputChannel'):
                id_tag = channel.find('{*}id')
                enabled_tag = channel.find('{*}videoInputEnabled')
                name_tag = channel.find('{*}name')
                res_desc_tag = channel.find('{*}resDesc') # Etiqueta para detectar NO VIDEO
                
                if id_tag is not None and enabled_tag is not None:
                    
                    # Usamos el ID del canal del XML como identificador
                    channel_id = id_tag.text 
                    camera_name = name_tag.text if name_tag is not None and name_tag.text else f"Canal {channel_id}"
                    res_desc_value = res_desc_tag.text.strip().upper() if res_desc_tag is not None else "ERROR"
                    
                    current_status = 'Inactivo'

                    # Si el DVR reporta una resolución (no "NO VIDEO"), está Activo.
                    if res_desc_value != 'NO VIDEO' and res_desc_value != 'ERROR':
                        current_status = 'Activo'
                    
                    cameras.append({
                        'name': camera_name, 
                        'status': current_status, 
                        'identifier': channel_id # Usamos el ID del canal (ej. "1", "2")
                    })

            if cameras:
                return {"status": "Activo", "cameras": cameras}

        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code
            logging.warning(f"DVR {ip}: Falló (HTTP {status_code}). Error: {http_err.response.text}")
            return {"status": "Error", "cameras": [], "error_detail": f"HTTP Error: {status_code}"}

        except Exception as e:
            logging.critical(f"Error CRÍTICO al procesar: {e}")
            return {"status": "Error", "cameras": [], "error_detail": "Fallo de procesamiento interno."}

    # Si la conexión no se pudo establecer en el único intento (HTTP/80)
    return {"status": "Error", "cameras": [], "error_detail": "Fallo de conexión total."}

def monitorear_dvr():
    """Orquesta el monitoreo de los DVRs y prepara los updates a BD y datos de layout."""
    global ultimo_estado_dvrs
    
    dvr_monitoreo = obtener_dvr_db()
    if "error" in dvr_monitoreo:
        return {"error": dvr_monitoreo["error"]}

    datos_por_edificio = {}
    total_activos = 0
    total_dispositivos = 0 
    updates_to_db = []

    if not dvr_monitoreo.get('dispositivos'):
        return {"layout": {"datos_por_edificio": {}, "total_activos": 0, "total_dispositivos": 0}, "updates": []}

    try:
        max_workers_dvrs = min(8, max(2, len(dvr_monitoreo['dispositivos'])))
        with ThreadPoolExecutor(max_workers=max_workers_dvrs) as executor:
            future_to_dvr = {executor.submit(get_camera_status_from_dvr, dvr): dvr for dvr in dvr_monitoreo['dispositivos']}
            for future in as_completed(future_to_dvr, timeout=120):
                dvr = future_to_dvr[future]
                try:
                    status_dvr = future.result()
                    id_dvr = dvr['id_dvr']
                    nombre_edificio = dvr.get('nombre_edificio', 'Sin Edificio')
                    
                    datos_por_edificio.setdefault(nombre_edificio, [])

                    # Mostrar el identificador del canal SIEMPRE que haya cámaras, y solo el id del DVR si no hay cámaras
                    if status_dvr['status'] == 'Activo' and status_dvr['cameras']:
                        for cam in status_dvr['cameras']:
                            if cam['status'] == 'Activo':
                                total_activos += 1
                            datos_por_edificio[nombre_edificio].append({
                                'ip': dvr['direccion'],
                                'estado': cam['status'],
                                'name': cam.get('name'),
                                'identifier': cam.get('identifier') or cam.get('name') or '',
                                'nombre_edificio': nombre_edificio
                            })
                        total_dispositivos += len(status_dvr['cameras'])
                    else:
                        datos_por_edificio[nombre_edificio].append({
                            'ip': dvr['direccion'],
                            'estado': status_dvr['status'],
                            'identifier': '', 
                            'nombre_edificio': nombre_edificio
                        })
                        total_dispositivos += 1

                    with lock:
                        estado_final_str = status_dvr['status']
                        estado_anterior_str = ultimo_estado_dvrs.get(id_dvr, 'Desconocido')
                        ultimo_estado_dvrs[id_dvr] = estado_final_str
                        
                        updates_to_db.append({
                            'id_dispositivo': id_dvr, 'estado_final': estado_final_str, 'estado_anterior': estado_anterior_str,
                            'tipo': 'Camara DVR', 'es_especial': True # Corregido para coincidir con la BD
                        })
                except Exception as exc:
                    logging.error(f"Error al procesar el resultado del DVR {dvr.get('direccion')}: {exc}")

    except (Exception, TimeoutError) as e:
        logging.error(f"ERROR: Fallo en el proceso de monitoreo de DVRs: {e}")
        return {"error": f"Fallo en el proceso de monitoreo de DVRs: {e}"}

    layout = {
        "titulo": "CÁMARAS", "icono": '/assets/icons/camara.png', "datos_por_edificio": datos_por_edificio,
        "total_activos": total_activos, "total_dispositivos": total_dispositivos
    }
    return {"layout": layout, "updates": updates_to_db}

# --- Contpaqi ---
def check_contpaqi_service_status(service_info: dict) -> dict:
    """Verifica el estado de un servicio de Windows de forma remota."""
    hostname = service_info.get('ip')
    username = service_info.get('usuario')
    password = service_info.get('contrasena')
    service_name = service_info.get('nombre_servicio_windows')
    
    if not hostname or not username or not password or not service_name:
        return {"id_servicio": service_info.get('id_servicio'), "estado": "Error", "detalle": "Faltan datos de conexión."}
    
    auth_user = f"{hostname}\\{username}"
    session = winrm.Session(hostname, auth=(auth_user, password), transport='ntlm', operation_timeout_sec=15)
    
    try:
        command = f'powershell -command "Get-Service -Name \'{service_name}\' | Select-Object -ExpandProperty Status"'
        result = session.run_ps(command)
        
        if result.std_err:
            error_message = result.std_err.decode('utf-8', errors='ignore').strip()
            return {"id_servicio": service_info.get('id_servicio'), "estado": "Error", "detalle": f"Error en el comando remoto: {error_message}"}

        service_status = result.std_out.decode('utf-8').strip().lower()

        if not service_status:
            return {"id_servicio": service_info.get('id_servicio'), "estado": "Inactivo", "detalle": "Salida vacía, el servicio podría no existir."}

        if service_status == 'running':
            return {"id_servicio": service_info.get('id_servicio'), "estado": "Activo"}
        else:
            return {"id_servicio": service_info.get('id_servicio'), "estado": "Inactivo", "detalle": f"Estado reportado: {service_status}"}
    
    except Exception as e:
        return {"id_servicio": service_info.get('id_servicio'), "estado": "Error", "detalle": str(e)}

def monitorear_servicios_contpaqi():
    """Orquesta el monitoreo de servicios ContpaQi y prepara los updates a BD y datos de layout."""
    global ultimo_estado_servicios

    with db_connection_manager() as conn:
        if not conn: return {"error": "No se pudo conectar a la base de datos."}

        servicios_a_monitorear = []
        try:
            # Obtener datos desde la BD (consulta SQL de contpaqi.py)
            cursor = conn.cursor()
            query = """
            SELECT sc.id_servicio, sc.nombre_servicio, sc.nombre_instancia_sql, 
                d.direccion AS ip, d.usuario, d.contrasena, td.descripcion
            FROM SERVICIOS_CONTPAQI AS sc
            JOIN DISPOSITIVOS AS d ON sc.DISPOSITIVOS_id_dispositivo = d.id_dispositivo
            JOIN TIPOS_DISPOSITIVO AS td ON d.TIPOS_DISPOSITIVO_id_tipo = td.id_tipo;
            """
            cursor.execute(query)
            servicios_db = cursor.fetchall()
            
            for row in servicios_db:
                # Lógica para determinar el nombre del servicio de Windows
                service_name = None
                if 'Contabilidad' in row.nombre_servicio or 'Nóminas' in row.nombre_servicio: service_name = 'Saci_CONTPAQi'
                elif 'SQL Server' in row.nombre_servicio and row.nombre_instancia_sql: service_name = f'MSSQL${row.nombre_instancia_sql}'
                elif 'Sincronización' in row.nombre_servicio: service_name = 'SSCi_CONTPAQi'
                elif 'SQL Server Agent' in row.nombre_servicio and row.nombre_instancia_sql: service_name = f'SQLAgent${row.nombre_instancia_sql}'
                else: continue

                servicios_a_monitorear.append({
                    'id_servicio': row.id_servicio,
                    'nombre_servicio': row.nombre_servicio,
                    'ip': row.ip,
                    'usuario': row.usuario,
                    'contrasena': row.contrasena,
                    'nombre_servicio_windows': service_name
                })
        except Exception as e:
            return {"error": f"Error al obtener los servicios de ContpaQi: {e}"}

    if not servicios_a_monitorear:
        return {"error": "No hay servicios de ContpaQi configurados para monitorear."}
    
    max_workers_contpaqi = min(10, max(2, len(servicios_a_monitorear)))
    with ThreadPoolExecutor(max_workers=max_workers_contpaqi) as executor:
        future_to_service = {executor.submit(check_contpaqi_service_status, s): s for s in servicios_a_monitorear}
    
    resultados_layout = []
    total_activos = 0
    updates_to_db = []
    
    try:
        for future in as_completed(future_to_service, timeout=120):
            service_info = future_to_service[future]
            try:
                result = future.result()
                estado_final = result.get('estado')
                
                with lock:
                    estado_anterior = ultimo_estado_servicios.get(result.get('id_servicio'), {}).get('estado_final', 'Desconocido')
                    ultimo_estado_servicios[result.get('id_servicio')] = {'estado_final': estado_final}

                updates_to_db.append({
                    'id_dispositivo': result.get('id_servicio'), 'estado_final': estado_final, 'estado_anterior': estado_anterior,
                    'tipo': 'Servicio ContpaQi', 'es_especial': False, 'es_servicio_contpaqi': True
                })

                if estado_final == "Activo": total_activos += 1

                # --- INCLUYE id_servicio en el dict de resultados ---
                resultados_layout.append({
                    'id_servicio': service_info['id_servicio'],
                    'nombre': service_info['nombre_servicio'],
                    'estado': estado_final
                })

            except Exception as exc:
                with lock:
                    estado_anterior = ultimo_estado_servicios.get(service_info.get('id_servicio'), {}).get('estado_final', 'Desconocido')
                    ultimo_estado_servicios[service_info.get('id_servicio')] = {'estado_final': 'Error'}
                    updates_to_db.append({
                        'id_dispositivo': service_info.get('id_servicio'), 'estado_final': 'Error', 'estado_anterior': estado_anterior,
                        'tipo': 'Servicio ContpaQi', 'es_especial': False, 'es_servicio_contpaqi': True
                    })
                resultados_layout.append({
                    'id_servicio': service_info.get('id_servicio'),
                    'nombre': service_info.get('nombre_servicio'),
                    'estado': 'Error'
                })
                
    except TimeoutError:
        return {"error": "Timeout al monitorear servicios de ContpaQi."}

    # Devolver datos crudos para el layout
    layout_data = {
        "resultados": resultados_layout, "activos": total_activos, "total": len(servicios_a_monitorear)
    }
    return {"layout": layout_data, "updates": updates_to_db}