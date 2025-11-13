# src/data/sql_connector.py
import pyodbc
import logging
from contextlib import contextmanager
from datetime import datetime
import os

# --- 1. CONFIGURACIÓN Y CONEXIÓN (ahora desde ENV) ---
DB_DRIVER = os.getenv('DB_DRIVER', '{ODBC Driver 17 for SQL Server}')
DB_SERVER = os.getenv('DB_SERVER', 'localhost\\SQLEXPRESS')
DB_DATABASE = os.getenv('DB_DATABASE', 'DashboardDB')
DB_TRUSTED = os.getenv('DB_TRUSTED', 'true').lower() in ('1', 'true', 'yes')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

def _build_connection_string():
    # Construye la cadena de conexión según si se usan credenciales o trusted connection
    if DB_TRUSTED:
        return f"DRIVER={DB_DRIVER};SERVER={DB_SERVER};DATABASE={DB_DATABASE};Trusted_Connection=yes;"
    else:
        if not DB_USER or not DB_PASSWORD:
            logging.error("DB_USER/DB_PASSWORD no proporcionados y DB_TRUSTED=False. No se puede conectar.")
            return None
        return f"DRIVER={DB_DRIVER};SERVER={DB_SERVER};DATABASE={DB_DATABASE};UID={DB_USER};PWD={DB_PASSWORD};"

DB_CONNECTION_STRING = _build_connection_string()

def get_db_connection():
    """Establece y retorna una conexión a la base de datos."""
    try:
        if not DB_CONNECTION_STRING:
            logging.error("Cadena de conexión inválida. Revisa variables de entorno.")
            return None
        conn = pyodbc.connect(DB_CONNECTION_STRING, autocommit=True)
        return conn
    except pyodbc.Error as ex:
        # Mejora: loguear más información si está disponible
        try:
            err_msg = ex.args[1] if len(ex.args) > 1 else ex.args[0]
        except Exception:
            err_msg = str(ex)
        logging.error(f"Fallo al conectar a la base de datos. Error: {err_msg}")
        return None

@contextmanager
def db_connection_manager():
    """Context manager para manejar conexiones a la base de datos."""
    conn = None
    try:
        conn = get_db_connection()
        yield conn
    finally:
        if conn:
            conn.close()

# --- 2. FUNCIONES DE LECTURA (GETTERS) ---

def get_estados_map() -> dict:
    """Obtiene el mapeo de nombres de estado a IDs de la base de datos."""
    with db_connection_manager() as conn:
        if not conn:
            logging.error("No se pudo conectar a la BD para obtener el mapa de estados.")
            return {}
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT nombre_estado, id_estado FROM ESTADOS")
            return {row.nombre_estado: row.id_estado for row in cursor.fetchall()}
        except Exception as e:
            logging.error(f"Error al obtener el mapa de estados: {e}")
            return {}

def obtener_dispositivos(nombre_tipo_dispositivo, agrupar_por_edificio=False) -> list:
    """Obtiene la lista de dispositivos de la base de datos por tipo."""
    with db_connection_manager() as conn:
        if not conn: return []
        dispositivos_db = []
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT id_tipo FROM TIPOS_DISPOSITIVO WHERE nombre_tipo = ?", nombre_tipo_dispositivo)
            id_tipo_row = cursor.fetchone()
            if not id_tipo_row: return []
            id_tipo = id_tipo_row[0]

            query = "SELECT d.id_dispositivo, d.nombre, d.direccion, d.ESTADOS_id_estado"
            if agrupar_por_edificio:
                query += ", e.nombre AS nombre_edificio FROM DISPOSITIVOS d JOIN EDIFICIOS e ON d.EDIFICIOS_id_edificio = e.id_edificio"
            else:
                query += " FROM DISPOSITIVOS d"
            query += " WHERE d.TIPOS_DISPOSITIVO_id_tipo = ? ORDER BY d.direccion"
            
            cursor.execute(query, id_tipo)
            dispositivos_db = cursor.fetchall()
            
        except Exception as e:
            logging.error(f"Error al obtener dispositivos para '{nombre_tipo_dispositivo}': {e}")
            return []

    dispositivos_list = []
    for row in dispositivos_db:
        device_dict = {
            'id_dispositivo': row.id_dispositivo,
            'nombre': row.nombre,
            'ip': row.direccion,
            'tipo_dispositivo': nombre_tipo_dispositivo,
            'id_estado_actual': row.ESTADOS_id_estado
        }
        if agrupar_por_edificio and hasattr(row, 'nombre_edificio'):
            device_dict['nombre_edificio'] = row.nombre_edificio
        dispositivos_list.append(device_dict)

    return dispositivos_list

def obtener_detalles_dispositivo(id_dispositivo) -> dict:
    """Obtiene los detalles de un dispositivo, incluyendo credenciales."""
    with db_connection_manager() as conn:
        if not conn: return {"error": "No se pudo conectar a la base de datos."}
        try:
            cursor = conn.cursor()
            query = """
            SELECT id_dispositivo, nombre, direccion, usuario, contrasena
            FROM DISPOSITIVOS
            WHERE id_dispositivo = ?
            """
            cursor.execute(query, id_dispositivo)
            row = cursor.fetchone()
            if row:
                return {
                    'id_dispositivo': row.id_dispositivo, 'nombre': row.nombre, 
                    'ip': row.direccion, 'usuario': row.usuario, 'contrasena': row.contrasena
                }
            return {"error": "Dispositivo no encontrado."}
        except Exception as e:
            logging.error(f"Error al obtener detalles del dispositivo {id_dispositivo}: {e}")
            return {"error": str(e)}

def obtener_checadores_db() -> dict:
    """Obtiene la lista de relojes checadores."""
    with db_connection_manager() as conn:
        if not conn: return {"error": "No se pudo conectar a la base de datos."}
        dispositivos_db = []
        try:
            cursor = conn.cursor()
            query = """
            SELECT de.id_especial, de.nombre, de.direccion, de.puerto_checador, e.nombre AS nombre_edificio
            FROM DISPOSITIVOS_ESPECIALES AS de
            LEFT JOIN EDIFICIOS AS e ON de.EDIFICIOS_id_edificio = e.id_edificio
            WHERE de.puerto_checador IS NOT NULL
            ORDER BY e.nombre, de.nombre;
            """
            cursor.execute(query)
            dispositivos_db = cursor.fetchall()
        except Exception as e:
            logging.error(f"Error al obtener relojes checadores: {e}")
            return {"error": str(e)}

    checadores_list = [
        {
            'id_reloj': row.id_especial, 'nombre': row.nombre, 'direccion': row.direccion, 
            'puerto': row.puerto_checador, 'nombre_edificio': row.nombre_edificio
        }
        for row in dispositivos_db
    ]

    return {"dispositivos": checadores_list}

def obtener_dvr_db() -> dict:
    """Obtiene la lista de DVRs."""
    with db_connection_manager() as conn:
        if not conn: return {"error": "No se pudo conectar a la base de datos."}
        dvr_list = []
        try:
            cursor = conn.cursor()
            query = """
            SELECT de.id_especial, de.nombre, de.direccion, de.puerto_web, de.usuario, de.contrasena, e.nombre AS nombre_edificio
            FROM DISPOSITIVOS_ESPECIALES AS de
            LEFT JOIN EDIFICIOS AS e ON de.EDIFICIOS_id_edificio = e.id_edificio
            WHERE de.TIPOS_DISPOSITIVO_id_tipo = 4
            ORDER BY e.nombre, de.nombre;
            """
            cursor.execute(query)
            dvr_list = cursor.fetchall()
        except Exception as e:
            logging.error(f"Error al obtener DVRs: {e}")
            return {"error": str(e)}

    dvr_info = [
        {
            'id_dvr': row.id_especial, 'nombre': row.nombre, 'direccion': row.direccion, 
            'puerto_web': row.puerto_web, 'usuario': row.usuario, 'contrasena': row.contrasena,
            'nombre_edificio': row.nombre_edificio
        }
        for row in dvr_list
    ]
    return {"dispositivos": dvr_info}

def obtener_conteo_fallas() -> dict:
    """Obtiene el conteo de todas las fallas ocurridas en el último mes agrupadas por tipo de dispositivo."""
    with db_connection_manager() as conn:
        if not conn: return {"error": "No se pudo conectar a la base de datos."}
        try:
            cursor = conn.cursor()
            # Consulta que une ambos tipos de dispositivos y agrupa por tipo, considerando el último mes
            query = """
            SELECT tipo, COUNT(*) AS total_fallas FROM (
                SELECT td.nombre_tipo AS tipo
                FROM HISTORIAL_FALLAS hf
                JOIN DISPOSITIVOS d ON hf.DISPOSITIVOS_id_dispositivo = d.id_dispositivo
                JOIN TIPOS_DISPOSITIVO td ON d.TIPOS_DISPOSITIVO_id_tipo = td.id_tipo
                WHERE hf.fecha_hora_inicio >= DATEADD(month, -1, GETDATE())
                UNION ALL
                SELECT tde.nombre_tipo AS tipo
                FROM HISTORIAL_FALLAS hf
                JOIN DISPOSITIVOS_ESPECIALES de ON hf.DISPOSITIVOS_ESPECIALES_id_especial = de.id_especial
                JOIN TIPOS_DISPOSITIVO tde ON de.TIPOS_DISPOSITIVO_id_tipo = tde.id_tipo
                WHERE hf.fecha_hora_inicio >= DATEADD(month, -1, GETDATE())
                UNION ALL
                SELECT 'Servicios Contpaqi' AS tipo
                FROM HISTORIAL_FALLAS hf
                JOIN SERVICIOS_CONTPAQI sc ON hf.SERVICIOS_CONTPAQI_id_servicio = sc.id_servicio
                WHERE hf.fecha_hora_inicio >= DATEADD(month, -1, GETDATE())
            ) AS fallas
            GROUP BY tipo
            ORDER BY total_fallas DESC;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            
            if not resultados:
                return {"fallas": [], "labels": []}
            labels = [row[0] for row in resultados]
            values = [row[1] for row in resultados]
            return {"fallas": values, "labels": labels}
        except Exception as e:
            logging.error(f"Error al procesar el conteo de fallas: {e}", exc_info=True)
            return {"error": f"Error al obtener el conteo de fallas: {e}"}

def obtener_historial_internet() -> dict:
    """Obtiene el historial de internet de la última hora."""
    with db_connection_manager() as conn:
        if not conn: return {"error": "No se pudo conectar a la base de datos."}
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                fecha_hora, velocidad_descarga, velocidad_carga, ping, 
                dispositivos_remotos, dispositivos_empresariales
            FROM HISTORIAL_INTERNET
            WHERE fecha_hora >= DATEADD(hour, -1, GETUTCDATE())
            ORDER BY fecha_hora ASC;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            
            fechas = [row.fecha_hora for row in resultados]
            descarga = [row.velocidad_descarga if row.velocidad_descarga is not None else 0 for row in resultados]
            carga = [row.velocidad_carga if row.velocidad_carga is not None else 0 for row in resultados]
            pings = [row.ping if row.ping is not None else 0 for row in resultados]
            remotos = [row.dispositivos_remotos if row.dispositivos_remotos is not None else 0 for row in resultados]
            empresariales = [row.dispositivos_empresariales if row.dispositivos_empresariales is not None else 0 for row in resultados]
            
            return {
                "fechas": fechas, "descarga": descarga, "carga": carga, "pings": pings, 
                "remotos": remotos, "empresariales": empresariales
            }
            
        except Exception as e:
            logging.error(f"Error al obtener el historial de internet: {e}")
            return {"error": f"Error al obtener el historial de internet: {e}"}

def obtener_historial_sitios_web() -> dict:
    """Obtiene los registros de estado de sitios web de la última hora."""
    with db_connection_manager() as conn:
        if not conn: return {"error": "No se pudo conectar a la base de datos."}
        try:

            query = """
            WITH RankedHistory AS (
                SELECT
                    hsw.fecha_hora,
                    hsw.estado,
                    d.direccion,
                    d.id_dispositivo,
                    ROW_NUMBER() OVER(PARTITION BY d.id_dispositivo ORDER BY hsw.fecha_hora DESC) as rn
                FROM HISTORIAL_SITIOS_WEB AS hsw
                JOIN DISPOSITIVOS AS d ON hsw.DISPOSITIVOS_id_dispositivo = d.id_dispositivo
                WHERE d.TIPOS_DISPOSITIVO_id_tipo = (SELECT id_tipo FROM TIPOS_DISPOSITIVO WHERE nombre_tipo = 'Sitio Web')
            )
            -- Parte 1: Obtener el último estado conocido de cada sitio
            SELECT fecha_hora, estado, direccion, id_dispositivo
            FROM RankedHistory
            WHERE rn = 1
            UNION
            -- Parte 2: Obtener todos los cambios de la última hora
            SELECT fecha_hora, estado, direccion, id_dispositivo
            FROM RankedHistory
            WHERE fecha_hora >= DATEADD(hour, -1, GETUTCDATE())
            ORDER BY fecha_hora ASC;
            """
            cursor = conn.cursor()
            cursor.execute(query)
            resultados = cursor.fetchall()
            return {"data": resultados}
            
        except Exception as e:
            logging.error(f"Error al obtener el historial de sitios web: {e}")
            return {"error": f"Error al obtener el historial de sitios web: {e}"}

def obtener_tipos_dispositivos_crud() -> list:
    """Obtiene una lista de tipos de dispositivos para la interfaz CRUD."""
    with db_connection_manager() as conn:
        if not conn:
            logging.error("No se pudo conectar a la BD para obtener tipos de dispositivos.")
            return []
        try:
            cursor = conn.cursor()
            # Excluimos tipos que no se gestionan manualmente o son abstractos.
            query = """
            SELECT id_tipo, nombre_tipo FROM TIPOS_DISPOSITIVO 
            WHERE nombre_tipo NOT IN ('Servicios Contpaqi')
            ORDER BY nombre_tipo;"""
            cursor.execute(query)
            return [{'id': row.id_tipo, 'nombre': row.nombre_tipo} for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Error al obtener tipos de dispositivos para CRUD: {e}")
            return []

def obtener_edificios() -> list:
    """Obtiene una lista de todos los edificios."""
    with db_connection_manager() as conn:
        if not conn:
            logging.error("No se pudo conectar a la BD para obtener edificios.")
            return []
        try:
            cursor = conn.cursor()
            query = "SELECT id_edificio, nombre FROM EDIFICIOS ORDER BY nombre"
            cursor.execute(query)
            # Aseguramos que el valor 'N/A' no tenga un ID nulo, sino un valor manejable por el Dropdown
            edificios = [{'id': row.id_edificio, 'nombre': row.nombre} for row in cursor.fetchall()]
            # Si existe un edificio con ID None, lo cambiamos a una cadena vacía.
            return [{'id': e['id'] if e['id'] is not None else '', 'nombre': e['nombre']} for e in edificios]
        except Exception as e:
            logging.error(f"Error al obtener edificios: {e}")
            return []

def obtener_dispositivos_crud(id_tipo) -> dict:
    """Obtiene dispositivos de DISPOSITIVOS o DISPOSITIVOS_ESPECIALES por id_tipo para la tabla CRUD."""
    with db_connection_manager() as conn:
        if not conn: return {"error": "No se pudo conectar a la base de datos."}
        try:
            cursor = conn.cursor()
            
            # 1. Obtener el nombre del tipo para saber si buscar en Especiales
            cursor.execute("SELECT nombre_tipo FROM TIPOS_DISPOSITIVO WHERE id_tipo = ?", id_tipo)
            tipo_row = cursor.fetchone()
            if not tipo_row: return {"error": "Tipo de dispositivo no encontrado."}
            nombre_tipo = tipo_row[0]
            
            # Tipos que usan la tabla DISPOSITIVOS_ESPECIALES
            is_special = nombre_tipo in ['Checador', 'Camara DVR', 'Firewall FortiGate']

            if is_special:
                # Dispositivos Especiales (gestionados con id_especial)
                query = """
                SELECT de.id_especial AS id, de.nombre, 
                       ISNULL(CAST(de.descripcion AS NVARCHAR(MAX)), '') AS descripcion, 
                       de.direccion, de.puerto_checador, de.puerto_web, 
                       de.usuario, de.contrasena, de.ultima_verificacion, e.nombre AS nombre_edificio, 
                       es.nombre_estado AS estado, de.EDIFICIOS_id_edificio as id_edificio
                FROM DISPOSITIVOS_ESPECIALES de
                LEFT JOIN EDIFICIOS e ON de.EDIFICIOS_id_edificio = e.id_edificio
                JOIN ESTADOS es ON de.ESTADOS_id_estado = es.id_estado
                WHERE de.TIPOS_DISPOSITIVO_id_tipo = ?
                ORDER BY de.nombre;
                """
            else:
                # Dispositivos Comunes (DISPOSITIVOS)
                query = """
                SELECT d.id_dispositivo AS id, d.nombre, 
                       ISNULL(CAST(d.descripcion AS NVARCHAR(MAX)), '') AS descripcion,
                       d.direccion, d.usuario, d.contrasena, 
                       d.ultima_verificacion, e.nombre AS nombre_edificio, 
                       es.nombre_estado AS estado, d.EDIFICIOS_id_edificio as id_edificio
                FROM DISPOSITIVOS d
                LEFT JOIN EDIFICIOS e ON d.EDIFICIOS_id_edificio = e.id_edificio
                JOIN ESTADOS es ON d.ESTADOS_id_estado = es.id_estado
                WHERE d.TIPOS_DISPOSITIVO_id_tipo = ?
                ORDER BY d.nombre;
                """
            
            cursor.execute(query, id_tipo)
            column_names = [column[0] for column in cursor.description]
            dispositivos_list = [dict(zip(column_names, row)) for row in cursor.fetchall()]
            
            return {"data": dispositivos_list, "is_special": is_special, "id_tipo": id_tipo, "nombre_tipo": nombre_tipo}
            
        except Exception as e:
            logging.error(f"Error al obtener dispositivos para CRUD del tipo {id_tipo}: {e}")
            return {"error": str(e)}

# --- 3. FUNCIONES DE ESCRITURA (WRITERS / UPDATERS) ---

def actualizar_credenciales_dispositivo(id_dispositivo, usuario, contrasena) -> dict:
    """Actualiza el usuario y la contraseña de un dispositivo."""
    with db_connection_manager() as conn:
        if not conn: return {"error": "No se pudo conectar a la base de datos."}
        try:
            cursor = conn.cursor()
            query = "UPDATE DISPOSITIVOS SET usuario = ?, contrasena = ? WHERE id_dispositivo = ?"
            cursor.execute(query, usuario, contrasena, id_dispositivo)
            if cursor.rowcount == 0:
                return {"error": "No se encontró el dispositivo para actualizar."}
            return {"success": True}
        except Exception as e:
            logging.error(f"Error al actualizar credenciales del dispositivo {id_dispositivo}: {e}")
            return {"error": str(e)}

def registrar_cambio_estado_sitio(id_dispositivo, nuevo_estado):
    """Registra el cambio de estado de un sitio web."""
    with db_connection_manager() as conn:
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO HISTORIAL_SITIOS_WEB (fecha_hora, estado, DISPOSITIVOS_id_dispositivo) VALUES (GETUTCDATE(), ?, ?)",
                nuevo_estado, id_dispositivo
            )

def update_device_in_db(cursor, data, estados_map):
    """Actualiza el estado de un dispositivo/servicio en la BD y gestiona el historial de fallas."""
    es_especial = data.get('es_especial', False)
    es_servicio_contpaqi = data.get('es_servicio_contpaqi', False)

    id_dispositivo = data.get('id_dispositivo')
    estado_final = data.get('estado_final')
    estado_anterior = data.get('estado_anterior')
    tipo_dispositivo = data.get('tipo')

    try:
        # Determinar la tabla a actualizar
        if es_servicio_contpaqi:
            tabla_a_actualizar = "SERVICIOS_CONTPAQI"
            id_columna = "id_servicio"
            id_historial = "SERVICIOS_CONTPAQI_id_servicio"
        elif es_especial:
            tabla_a_actualizar = "DISPOSITIVOS_ESPECIALES"
            id_columna = "id_especial"
            id_historial = "DISPOSITIVOS_ESPECIALES_id_especial"
        else:
            tabla_a_actualizar = "DISPOSITIVOS"
            id_columna = "id_dispositivo"
            id_historial = "DISPOSITIVOS_id_dispositivo"

        id_estado = estados_map.get(estado_final)
        if id_estado:
            query_update = f"UPDATE {tabla_a_actualizar} SET ESTADOS_id_estado = ?, ultima_verificacion = GETDATE() WHERE {id_columna} = ?"
            cursor.execute(query_update, id_estado, id_dispositivo)

        # Lógica de registro de historial de fallas (iniciar o cerrar)
        if tipo_dispositivo != 'PC' and estado_anterior not in ['Error', 'Inactivo'] and estado_final == 'Error':
            detalle = f"Dispositivo cambió a estado {estado_final}."
            query_insert = f"INSERT INTO HISTORIAL_FALLAS (fecha_hora_inicio, detalle_falla, {id_historial}) VALUES (GETDATE(), ?, ?)"
            cursor.execute(query_insert, detalle, id_dispositivo)
            logging.warning(f"Nueva falla registrada para {tipo_dispositivo} {id_dispositivo}: {detalle}")
        elif tipo_dispositivo != 'PC' and estado_anterior == 'Error' and estado_final in ['Activo', 'Advertencia']:
            query_update_fallas = f"UPDATE HISTORIAL_FALLAS SET fecha_hora_fin = GETDATE() WHERE {id_historial} = ? AND fecha_hora_fin IS NULL"
            cursor.execute(query_update_fallas, id_dispositivo)
            logging.info(f"Falla finalizada para {tipo_dispositivo} {id_dispositivo}.")
    except Exception as e:
        logging.error(f"ERROR: Fallo al actualizar el estado del dispositivo/servicio {id_dispositivo} en la BD: {e}")

def registrar_historial_internet(data):
    """Inserta el registro de velocidad de internet."""
    with db_connection_manager() as conn:
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO HISTORIAL_INTERNET (
                    fecha_hora, velocidad_descarga, velocidad_carga, ping, 
                    dispositivos_remotos, dispositivos_empresariales
                ) VALUES (GETUTCDATE(), ?, ?, ?, ?, ?)
                """,
                data.get('velocidad_descarga'), 
                data.get('velocidad_carga'), 
                data.get('ping'),
                data.get('remotos'),
                data.get('empresariales')
            )

def eliminar_dispositivo(id_dispositivo, is_special) -> dict:
    """Elimina un dispositivo de DISPOSITIVOS o DISPOSITIVOS_ESPECIALES, incluyendo la eliminación en cascada de registros relacionados."""
    with db_connection_manager() as conn:
        if not conn: return {"error": "No se pudo conectar a la base de datos."}
        try:
            cursor = conn.cursor()
            
            # 1. Determinar tablas y columnas
            tabla_principal = "DISPOSITIVOS_ESPECIALES" if is_special else "DISPOSITIVOS"
            id_columna_principal = "id_especial" if is_special else "id_dispositivo"
            id_columna_historial = "DISPOSITIVOS_ESPECIALES_id_especial" if is_special else "DISPOSITIVOS_id_dispositivo"
            
            # 2. ELIMINACIÓN EN CASCADA: Borrar registros relacionados en HISTORIAL_FALLAS
            query_cascada = f"DELETE FROM HISTORIAL_FALLAS WHERE {id_columna_historial} = ?"
            cursor.execute(query_cascada, id_dispositivo)
            logging.info(f"Eliminados {cursor.rowcount} registros de fallas para {tabla_principal} ID {id_dispositivo}.")
            
            # 3. ELIMINACIÓN DE TABLAS ADICIONALES (EJEMPLO: SERVICIOS_CONTPAQI)
            # Aunque la lógica de tu monitoreo maneja los servicios por separado, 
            # si el dispositivo eliminado es un servidor que aloja SERVICIOS_CONTPAQI, 
            # también deben eliminarse o reasignarse esos servicios.
            if not is_special and tabla_principal == "DISPOSITIVOS":
                query_servicios = "DELETE FROM SERVICIOS_CONTPAQI WHERE DISPOSITIVOS_id_dispositivo = ?"
                cursor.execute(query_servicios, id_dispositivo)
                logging.info(f"Eliminados {cursor.rowcount} servicios ContpaQi relacionados al DISPOSITIVO ID {id_dispositivo}.")

            # 4. ELIMINACIÓN DEL REGISTRO PRINCIPAL
            query_principal = f"DELETE FROM {tabla_principal} WHERE {id_columna_principal} = ?"
            cursor.execute(query_principal, id_dispositivo)
            
            if cursor.rowcount == 0:
                # Si la eliminación principal falló, devolvemos un error
                return {"error": "Dispositivo no encontrado para eliminar."}
            
            return {"success": True}
        except Exception as e:
            logging.error(f"Error CRÍTICO al eliminar dispositivo {id_dispositivo} (Cascada): {e}", exc_info=True)
            return {"error": str(e)}
        
def insertar_o_actualizar_dispositivo(data) -> dict:
    """Inserta o actualiza un dispositivo (común o especial) en la base de datos."""

    with db_connection_manager() as conn:
        if not conn: return {"error": "No se pudo conectar a la base de datos."}
        try:
            cursor = conn.cursor()
            
            # Obtener el ID de estado 'Activo' para nuevos registros
            estados_map = get_estados_map()
            id_estado_activo = estados_map.get('Activo', 1) # Fallback a 1 si no existe
            
            # Determinar tablas y columnas
            is_new = data['device_id'] in ['NEW', None, '']
            is_special = data['is_special']
            descripcion = data.get('descripcion', '')

            if is_special:
                tabla = "DISPOSITIVOS_ESPECIALES"
                id_columna = "id_especial"
                puerto_checador = data.get('puerto_checador')
                puerto_web = data.get('puerto_web')
                
                # --- Agregar descripción a los campos ---
                base_campos = "nombre, descripcion, direccion, usuario, contrasena, TIPOS_DISPOSITIVO_id_tipo, EDIFICIOS_id_edificio"
                base_valores = "?, ?, ?, ?, ?, ?, ?"
                base_params = [
                    data['nombre'], descripcion, data['direccion'], data['usuario'],
                    data['contrasena'], data['id_tipo'], data['id_edificio']
                ]

                if puerto_checador is not None:
                    base_campos += ", puerto_checador"
                    base_valores += ", ?"
                    base_params.append(puerto_checador)
                
                if puerto_web is not None:
                    base_campos += ", puerto_web"
                    base_valores += ", ?"
                    base_params.append(puerto_web)
                
                # --- Actualización ---
                update_set = "nombre = ?, descripcion = ?, direccion = ?, usuario = ?, contrasena = ?, EDIFICIOS_id_edificio = ?"
                update_params = [
                    data['nombre'], descripcion, data['direccion'], data['usuario'],
                    data['contrasena'], data['id_edificio']
                ]
                if puerto_checador is not None:
                    update_set += ", puerto_checador = ?"
                    update_params.append(puerto_checador)
                if puerto_web is not None:
                    update_set += ", puerto_web = ?"
                    update_params.append(puerto_web)
            else:
                tabla = "DISPOSITIVOS"
                id_columna = "id_dispositivo"
                # --- Agregar descripción a los campos ---
                base_campos = "nombre, descripcion, direccion, usuario, contrasena, TIPOS_DISPOSITIVO_id_tipo, EDIFICIOS_id_edificio"
                base_valores = "?, ?, ?, ?, ?, ?, ?"
                base_params = [
                    data['nombre'], descripcion, data['direccion'], data['usuario'],
                    data['contrasena'], data['id_tipo'], data['id_edificio']
                ]

                update_set = "nombre = ?, descripcion = ?, direccion = ?, usuario = ?, contrasena = ?, EDIFICIOS_id_edificio = ?"
                update_params = [
                    data['nombre'], descripcion, data['direccion'], data['usuario'],
                    data['contrasena'], data['id_edificio']
                ]
            
            # --- Lógica de Inserción ---
            if is_new:
                final_campos = f"{base_campos}, ESTADOS_id_estado, ultima_verificacion"
                final_valores = f"{base_valores}, ?, GETDATE()"
                final_params = base_params + [id_estado_activo]
                
                query = f"INSERT INTO {tabla} ({final_campos}) VALUES ({final_valores})"
                cursor.execute(query, final_params)
                logging.info(f"Nuevo dispositivo insertado en {tabla} con tipo {data['id_tipo']}.")
                return {"success": True, "action": "insertado"}
                
            # --- Lógica de Actualización ---
            else:
                device_id = data['device_id']
                if isinstance(device_id, str) and device_id.isdigit():
                    device_id = int(device_id)
                final_update_set = f"{update_set}, ultima_verificacion = GETDATE()"
                final_params = update_params + [device_id]
                
                query = f"UPDATE {tabla} SET {final_update_set} WHERE {id_columna} = ?"
                cursor.execute(query, final_params)
                
                if cursor.rowcount == 0:
                    return {"error": "Dispositivo no encontrado para actualizar."}
                
                logging.info(f"Dispositivo actualizado en {tabla} ID {device_id}.")
                return {"success": True, "action": "actualizado"}

        except Exception as e:
            logging.error(f"Error al guardar/actualizar dispositivo en {tabla}: {e}", exc_info=True)
            return {"error": str(e)}

def obtener_detalles_servicio_contpaqi(id_servicio) -> dict:
    """Obtiene los detalles de un servicio CONTPAQI por su id_servicio."""
    with db_connection_manager() as conn:
        if not conn:
            return {"error": "No se pudo conectar a la base de datos."}
        try:
            cursor = conn.cursor()
            query = """
                SELECT sc.id_servicio, sc.nombre_servicio AS nombre, d.direccion AS servidor, sc.nombre_servicio_windows
                FROM SERVICIOS_CONTPAQI sc
                JOIN DISPOSITIVOS d ON sc.DISPOSITIVOS_id_dispositivo = d.id_dispositivo
                WHERE sc.id_servicio = ?
            """
            cursor.execute(query, id_servicio)
            row = cursor.fetchone()
            if row:

                return {
                    'id_servicio': row.id_servicio,
                    'nombre': row.nombre,
                    'servidor': row.servidor,
                    'nombre_servicio': row.nombre_servicio_windows
                }
            return {"error": "Servicio CONTPAQI no encontrado."}
        except Exception as e:
            logging.error(f"Error al obtener detalles del servicio CONTPAQI {id_servicio}: {e}")
            return {"error": str(e)}

def actualizar_servicio_contpaqi(id_servicio, servidor, nombre_servicio) -> dict:
    """Actualiza el dispositivo asociado (servidor) y el nombre del servicio de un servicio CONTPAQI."""
    with db_connection_manager() as conn:
        if not conn:
            return {"error": "No se pudo conectar a la base de datos."}
        try:
            cursor = conn.cursor()
            # 1. Encontrar el id_dispositivo que corresponde a la nueva IP/hostname del servidor
            cursor.execute("SELECT id_dispositivo FROM DISPOSITIVOS WHERE direccion = ?", servidor)
            dispositivo_row = cursor.fetchone()
            if not dispositivo_row:
                return {"error": f"No se encontró un servidor registrado con la dirección '{servidor}'. Asegúrate de que el servidor esté registrado en el sistema."}
            
            id_dispositivo_nuevo = dispositivo_row.id_dispositivo

            query = "UPDATE SERVICIOS_CONTPAQI SET DISPOSITIVOS_id_dispositivo = ?, nombre_servicio_windows = ? WHERE id_servicio = ?"
            cursor.execute(query, id_dispositivo_nuevo, nombre_servicio, id_servicio)
            if cursor.rowcount == 0:
                return {"error": "No se encontró el servicio CONTPAQI para actualizar."}
            return {"success": True}
        except Exception as e:
            logging.error(f"Error al actualizar servicio CONTPAQI {id_servicio}: {e}")
            return {"error": str(e)}

def obtener_historial_fallas(dias: int = 7):
    """
    Obtiene el historial de fallas de los últimos N días, incluyendo dispositivo, tipo, fechas y duración.
    """
    with db_connection_manager() as conn:
        if not conn:
            return {"error": "No se pudo conectar a la base de datos."}
        try:
            cursor = conn.cursor()
            query = """
            SELECT
                COALESCE(d.nombre, de.nombre) AS nombre_dispositivo,
                COALESCE(td.nombre_tipo, tde.nombre_tipo, 'Servicio ContpaQi') AS tipo_dispositivo,
                hf.fecha_hora_inicio,
                hf.fecha_hora_fin,
                DATEDIFF(MINUTE, hf.fecha_hora_inicio, ISNULL(hf.fecha_hora_fin, GETDATE())) AS duracion_minutos,
                CASE
                    WHEN hf.fecha_hora_fin IS NULL THEN 'Abierta'
                    ELSE 'Cerrada'
                END AS estado_falla
            FROM HISTORIAL_FALLAS hf
            LEFT JOIN DISPOSITIVOS d ON hf.DISPOSITIVOS_id_dispositivo = d.id_dispositivo
            LEFT JOIN TIPOS_DISPOSITIVO td ON d.TIPOS_DISPOSITIVO_id_tipo = td.id_tipo
            LEFT JOIN DISPOSITIVOS_ESPECIALES de ON hf.DISPOSITIVOS_ESPECIALES_id_especial = de.id_especial
            LEFT JOIN TIPOS_DISPOSITIVO tde ON de.TIPOS_DISPOSITIVO_id_tipo = tde.id_tipo
            LEFT JOIN SERVICIOS_CONTPAQI sc ON hf.SERVICIOS_CONTPAQI_id_servicio = sc.id_servicio
            WHERE hf.fecha_hora_inicio >= DATEADD(day, ?, GETDATE())
            ORDER BY hf.fecha_hora_inicio DESC
            """
            cursor.execute(query, -dias)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            data = [dict(zip(columns, row)) for row in rows]
            return {"data": data}
        except Exception as e:
            logging.error(f"Error al obtener historial de fallas para los últimos {dias} días: {e}")
            return {"error": str(e)}