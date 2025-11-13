import dash
from dash import dcc, html, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import datetime
import threading
import time
import logging
from flask import request
from concurrent.futures import as_completed, TimeoutError
from src.utils.concurrency import get_shared_executor as get_executor
# Layouts
from src.layouts.main_layout import create_main_layout
from src.layouts.internet_detail_layout import create_internet_detail_layout
from src.layouts.admin_layout import create_admin_layout
# Callbacks
from src.callbacks.register_callbacks import register_all_callbacks
from src.callbacks.admin_callbacks import register_admin_callbacks
from src.callbacks.reports_callbacks import register_reports_callbacks

# Lógica de Monitoreo (Workers)
from src.models.internet_logic import monitorear_velocidad_internet, all_users, process_sitios_web_history
from src.layouts.telefonos_layout import create_telefonos_layout 
from src.layouts.servidores_layout import create_servidores_layout
from src.layouts.pcs_layout import create_pcs_layout
from src.layouts.dvr_layout import create_dvr_layout
from src.layouts.contpaqi_layout import create_contpaqi_layout
from src.layouts.checadores_layout import create_checadores_layout
from src.layouts.sitios_web_layout import create_sitios_web_layout
from src.layouts.conmutador_layout import create_conmutador_layout
from src.layouts.termometros_layout import create_termometros_layout

# Acceso a Datos 
from src.data.sql_connector import db_connection_manager, update_device_in_db, get_estados_map, obtener_conteo_fallas, obtener_historial_internet, registrar_historial_internet
from src.components.card_header import crear_header_modulo
from src.components.internet_module import crear_layout_internet_speed
from src.plotting.chart_factory import create_faults_pie_chart, create_internet_history_figure, create_storyline_figure


# --- 2. CONFIGURACIÓN Y DECLARACIÓN DE VARIABLES GLOBALES ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SPACELAB], suppress_callback_exceptions=True)
ROTATION_INTERVAL_SECONDS = 300

# --- CACHE CLEANER CONFIG ---
# Intervalo en segundos para limpiar cache (por defecto 1 hora)
CACHE_CLEAN_INTERVAL_SECONDS = 60 * 60
# Límites para mantener estructuras en tamaño razonable
_MAX_VPN_USERS = 200
# keys pesadas a resetear parcialmente (se usan para evitar growth indefinido)
_HEAVY_KEYS = [
    'fallas_pie_chart', 'internet_history_line_chart', 'internet_storyline_chart',
    'vpn_users_details'
]

# Timestamp de la última limpieza (solo para info)
_LAST_CACHE_CLEAN_TS = None
# ------------------------------

# Intervalo del worker dedicado de termómetros (segundos)
TERMOMETROS_INTERVAL_SECONDS = 20

# Cache y Locks Globales
monitor_cache = {
    'last_update': None,
    'telefonos_data': {'header': 'Cargando...', 'body': 'Cargando...'},
    'servidores_data': {'header': 'Cargando...', 'body': 'Cargando...'},
    'pcs_data': {'header': 'Cargando...', 'body': 'Cargando...'},
    'conmutador_data': {'body': 'Cargando...'},
    'dvr_data': {'header': 'Cargando...', 'body': 'Cargando...'},
    'sitios_web_data': {'header': 'Cargando...', 'body': 'Cargando...'},
    'checadores_data': {'header': 'Cargando...', 'body': 'Cargando...'},
    'termometros_data': {'header': 'Cargando...', 'body': 'Cargando...'},
    'contpaqi_data': {'header': 'Cargando...', 'body': 'Cargando...'},
    'internet_speed_data': {'header': 'Cargando...', 'body': 'Cargando...'},
    'welcome_message': 'Cargando...',
    'usuarios_conectados': '...',
    'reloj_hora': '00:00:00',
    'reloj_fecha': '00/00/0000',
    'fallas_pie_chart': go.Figure(),
    'internet_history_line_chart': go.Figure(),
    'internet_storyline_chart': go.Figure(),
    'live_internet_metrics': {},
    'vpn_users_details': [],
}
cache_lock = threading.Lock()
db_lock = threading.Lock()

# Configuración de Módulos
MODULES_CONFIG = {
    'telefonos': {'title': "TELÉFONOS ACTIVOS", 'icon': '/assets/icons/telefono.png'},
    'sitios_web': {'title': "SITIOS WEB", 'icon': '/assets/icons/sitio_web.png'},
    'servidores': {'title': "SERVIDORES", 'icon': '/assets/icons/servidor.png'},
    'dvr': {'title': "DVR", 'icon': '/assets/icons/camara.png'},
    'internet_speed': {'title': "VELOCIDAD DE INTERNET", 'icon': '/assets/icons/velocidad.png'},
    'checadores': {'title': "CHECADORES", 'icon': '/assets/icons/checadores.png'},
    'contpaqi': {'title': "SERVICIOS CONTPAQI", 'icon': '/assets/icons/contpaqi.png'},
    'pcs': {'title': "PC ENCENDIDAS", 'icon': '/assets/icons/pc.png'},
    'conmutador': {'title': "CONMUTADOR", 'icon': '/assets/icons/conmutador.png'},
}

# --- 3. LAYOUT PRINCIPAL ---
app.layout = html.Div([

    html.Button(
        html.Img(src='/assets/icons/next.png', style={'height': '50px'}),
        id='next-page-button',
        n_clicks=0,
        className='next-page-btn'
    ),
    dcc.Location(id='url', refresh=False),
    # Dummy target for clientside animation callback (hidden)
    html.Div(id='animation-dummy', style={'display': 'none'}),
    html.Button(id='add-device-button', n_clicks=0, style={'display': 'none'}),
    dcc.Store(id='graphs-store', storage_type='memory'),
    dcc.Store(id='page-rotation-state', data={'current_page_index': 0, 'pages': ['/', '/internet-detail']}),
    html.Div(id='interval-container', children=[
        dcc.Interval(id='page-rotation-interval', interval=ROTATION_INTERVAL_SECONDS * 1000, n_intervals=0)
    ]),
    html.Div(id='page-content'),

    dcc.Store(id='monitoreo-store', storage_type='memory'),
    dcc.Store(id='admin-busy', data=False),  
    dcc.Interval(id='interval-monitoreo', interval=3*1000, n_intervals=0),
    dcc.Interval(id='interval-reloj', interval=1*1000, n_intervals=0), 
])

@app.server.after_request
def add_cache_headers(response):
	try:
		if request.path.startswith('/assets/'):
			response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
	except Exception:
		pass
	return response

# ----------------------------------------------------------------------
# --- 4. LÓGICA DE WORKERS Y THREADS ---
# ----------------------------------------------------------------------

def clock_worker():
    global monitor_cache
    while True:
        now = datetime.datetime.now()
        with cache_lock:
            monitor_cache['reloj_hora'] = now.strftime('%H:%M:%S')
            monitor_cache['reloj_fecha'] = now.strftime('%d/%m/%Y')
        time.sleep(1)

def welcome_message_worker():
    global monitor_cache
    while True:
        now = datetime.datetime.now()
        if 5 <= now.hour < 12: welcome_message_text = "Buen día." ; welcome_gif = '/assets/gifs/coffee.gif'
        elif 12 <= now.hour < 18: welcome_message_text = "Buena tarde" ; welcome_gif = '/assets/gifs/atardecer.gif'
        else: welcome_message_text = "Buena noche. Ve a descansar" ; welcome_gif = '/assets/gifs/buho.gif'
        with cache_lock:
            monitor_cache['welcome_message'] = welcome_message_text
            monitor_cache['welcome_gif'] = welcome_gif
        time.sleep(60)

def run_monitoring_tasks(tasks, sleep_interval):
    global monitor_cache
    while True:
        logging.debug(f"Iniciando ciclo de monitoreo para: {', '.join(tasks.keys())}")
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max(len(tasks), 4)) as executor:
            futures = {executor.submit(func): name for name, func in tasks.items()}
        updates_to_db = []
        completed_task_names = set()
        try:
            for future in as_completed(futures, timeout=sleep_interval):
                task_name = futures[future]
                completed_task_names.add(task_name)
                try:
                    result = future.result()
                    if "error" in result:
                        with cache_lock:
                            monitor_cache[f'{task_name}_data'] = result
                    else:
                        layout_data = result.get('layout', result)
                        with cache_lock:
                            monitor_cache[f'{task_name}_data'] = layout_data
                        if "updates" in result and result.get("updates"):
                            updates_to_db.extend(result["updates"])
                except Exception as e:
                    logging.error(f"La subtarea de monitoreo '{task_name}' generó una excepción: {e}", exc_info=True)
                    config = MODULES_CONFIG.get(task_name, {'title': task_name.upper(), 'icon': '/assets/icons/fallas.png'})
                    error_layout = {'header': crear_header_modulo(config['title'], config.get('icon', ''), "Error"), 'body': html.Div(f"Fallo en sub-tarea: {e}", className="text-danger p-2")}
                    with cache_lock: monitor_cache[f'{task_name}_data'] = error_layout
        except TimeoutError:
            unfinished = set(tasks.keys()) - completed_task_names
            for task_name in unfinished:
                logging.error(f"La subtarea de monitoreo '{task_name}' no terminó a tiempo (timeout).")
                config = MODULES_CONFIG.get(task_name, {'title': task_name.upper(), 'icon': '/assets/icons/fallas.png'})
                error_layout = {'header': crear_header_modulo(config['title'], config.get('icon', ''), "Timeout"),
                                'body': html.Div("La tarea no terminó a tiempo.", className="text-danger p-2")}
                with cache_lock:
                    monitor_cache[f'{task_name}_data'] = error_layout

        # Escritura en la BD 
        if updates_to_db:
            with db_lock:
                with db_connection_manager() as conn:
                    if conn:
                        cursor = conn.cursor()
                        estados_map = get_estados_map() 
                        for update in updates_to_db:
                            update_device_in_db(cursor, update, estados_map)
                    else:
                        logging.error("No se pudo obtener conexión a la BD para las actualizaciones masivas.")

        time.sleep(sleep_interval)

def monitoring_fast_worker():
    #Monitoreo rápido para teléfonos y servidores
    tasks = {
        'telefonos': create_telefonos_layout,
        'servidores': create_servidores_layout,
    }
    run_monitoring_tasks(tasks, sleep_interval=20)

def monitoring_slow_worker():
    # Monitoreo intermedio para checadores, DVR, conmutador y PCs
    tasks = {
        'checadores': create_checadores_layout,
        'dvr': create_dvr_layout,
        'conmutador': create_conmutador_layout,  
        'pcs': create_pcs_layout,
    }
    run_monitoring_tasks(tasks, sleep_interval=60)

def monitoring_very_slow_worker():
    # Monitoreo lento para sitios web y servicios Contpaqi
    tasks = {
        'sitios_web': create_sitios_web_layout,
        'contpaqi': create_contpaqi_layout,
    }
    run_monitoring_tasks(tasks, sleep_interval=60)


def monitoring_api_worker():
    #Monitorea velocidad de internet y usuarios, actualiza cache y BD
    global monitor_cache
    while True:
        try:
            speed_data = monitorear_velocidad_internet()
            user_counts = all_users()
            # Si hubo error al medir velocidad, componer un payload con ceros/valores neutros
            if "error" in speed_data:
                logging.error(f"Error al obtener métricas de Internet: {speed_data.get('error')}")
                live_internet_data = {
                    'velocidad_descarga': 0,
                    'velocidad_carga': 0,
                    'ping': None,
                    'remotos': user_counts.get('remotos', 0) if isinstance(user_counts, dict) else 0,
                    'empresariales': user_counts.get('empresariales', 0) if isinstance(user_counts, dict) else 0,
                    'vpn_details': []
                }
                # Registrar igualmente en historial (para dejar constancia de la caída)
                try:
                    with db_lock:
                        registrar_historial_internet(live_internet_data)
                except Exception as e:
                    logging.warning(f"No se pudo registrar historial de internet al detectar error: {e}")

                # Generar layout con valores neutros y cachearlo
                try:
                    internet_speed_layout = crear_layout_internet_speed(
                        velocidad_descarga=live_internet_data['velocidad_descarga'],
                        velocidad_carga=live_internet_data['velocidad_carga'],
                        ping=live_internet_data['ping'],
                        remotos=live_internet_data['remotos'],
                        empresariales=live_internet_data['empresariales'],
                    )
                except Exception as e:
                    logging.warning(f"No se pudo generar layout de internet con valores 0: {e}")
                    internet_speed_layout = {'header': crear_header_modulo("VELOCIDAD DE INTERNET", '/assets/icons/velocidad.png', "Error"), 'body': html.Div("No disponible", className="text-danger")}

                with cache_lock:
                    monitor_cache['internet_speed_data'] = internet_speed_layout
                    monitor_cache['live_internet_metrics'] = live_internet_data
                    monitor_cache['vpn_users_details'] = live_internet_data.get('vpn_details', [])
                    monitor_cache['last_update'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            else:
                # Caso normal: éxito al medir velocidad
                live_internet_data = {**speed_data, **user_counts}
                
                # 2. Inserta en la BD
                with db_lock:
                    try:
                        registrar_historial_internet(live_internet_data) 
                    except Exception as e:
                        logging.warning(f"No se pudo registrar historial de internet: {e}")

                # 3. Crea y Cachea el layout de velocidad
                internet_speed_layout = crear_layout_internet_speed(
                    velocidad_descarga=live_internet_data.get('velocidad_descarga', 0),
                    velocidad_carga=live_internet_data.get('velocidad_carga', 0),
                    ping=live_internet_data.get('ping', 0),
                    remotos=live_internet_data.get('remotos', 0),
                    empresariales=live_internet_data.get('empresariales', 0),
                )
                with cache_lock:
                    monitor_cache['internet_speed_data'] = internet_speed_layout
                    monitor_cache['live_internet_metrics'] = live_internet_data
                    monitor_cache['vpn_users_details'] = live_internet_data.get('vpn_details', [])                    
                    monitor_cache['last_update'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

                    try:
                        term_layout_resp = create_termometros_layout()
                        monitor_cache['termometros_data'] = term_layout_resp.get('layout', term_layout_resp)
                    except Exception as e:
                        logging.warning(f"No se pudo generar termometros simulados: {e}")
        except Exception as e:
            logging.error(f"ERROR CRÍTICO en monitoring_api_worker: {e}")
        finally:
            time.sleep(60)

def monitoring_db_query_worker():
    # Actualiza gráficas y usuarios conectados en el cache global.
    global monitor_cache
    while True:
        try:
            fallas_data = obtener_conteo_fallas() 
            history_data = obtener_historial_internet() 
            storyline_data = process_sitios_web_history()
            
            fallas_pie_chart = create_faults_pie_chart(fallas_data)
            internet_history_fig = create_internet_history_figure(history_data)
            storyline_fig = create_storyline_figure(storyline_data)

            with cache_lock:
                monitor_cache['fallas_pie_chart'] = fallas_pie_chart
                monitor_cache['internet_history_line_chart'] = internet_history_fig
                monitor_cache['internet_storyline_chart'] = storyline_fig
                remotos = monitor_cache['live_internet_metrics'].get('remotos', 0)
                empresariales = monitor_cache['live_internet_metrics'].get('empresariales', 0)
                monitor_cache['usuarios_conectados'] = int(remotos) + int(empresariales)
                # actualizar marca de tiempo para ayudar al limpiador y al store
                monitor_cache['last_update'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                
        except Exception as e:
            logging.error(f"ERROR CRÍTICO en monitoring_db_query_worker: {e}")
            with cache_lock:
                monitor_cache['fallas_pie_chart'] = go.Figure()
                monitor_cache['internet_history_line_chart'] = go.Figure()
                monitor_cache['internet_storyline_chart'] = go.Figure()
        finally:
            # Reducimos la frecuencia de consultas a la BD/plotting para no sobrecargarla.
            logging.debug("monitoring_db_query_worker durmió 60s antes del próximo ciclo.")
            time.sleep(60)

def monitoring_termometros_worker():
    """Worker dedicado que actualiza termometros_data con layouts simulados."""
    global monitor_cache
    while True:
        try:
            term_resp = create_termometros_layout()
            # Guardar solo el layout (header/body) en el cache para que el store lo propague
            with cache_lock:
                monitor_cache['termometros_data'] = term_resp.get('layout', term_resp)
        except Exception as e:
            logging.error(f"ERROR en monitoring_termometros_worker: {e}")
        finally:
            time.sleep(TERMOMETROS_INTERVAL_SECONDS)

# ----------------------------------------------------------------------
# --- 5. CALLACKS DE FLUJO Y ARRANQUE (SE QUEDAN EN APP.PY) ---
# ----------------------------------------------------------------------

# --- Callbacks de Enrutamiento, Store y Rotación ---
@app.callback(Output('page-content', 'children'), Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/internet-detail':
        return create_internet_detail_layout()
    if pathname == '/admin':
        return create_admin_layout()
    return create_main_layout(app)

@app.callback(Output('monitoreo-store', 'data'), Input('interval-monitoreo', 'n_intervals'))
def update_store(n_intervals):
    with cache_lock: return monitor_cache.copy()

@app.callback(
    [Output('reloj-hora-content', 'children'), Output('reloj-fecha-content', 'children')],
    Input('interval-reloj', 'n_intervals'),
    prevent_initial_call=True
)
def update_clock_display(n):
    with cache_lock:
        return monitor_cache.get('reloj_hora', '00:00:00'), monitor_cache.get('reloj_fecha', '00/00/0000')

@app.callback(
    [Output('url', 'pathname', allow_duplicate=True), # Cambia la página
     Output('interval-container', 'children')],      # Resetea el temporizador
    [Input('page-rotation-interval', 'n_intervals'), Input('next-page-button', 'n_clicks')],
    [State('page-rotation-state', 'data'), State('url', 'pathname'), State('admin-busy', 'data')],
    prevent_initial_call=True
)
def rotate_page(n_intervals, n_clicks, page_state, current_pathname, admin_busy):
    ctx = dash.callback_context
    if not ctx.triggered or not any(t['value'] for t in ctx.triggered):
        raise dash.exceptions.PreventUpdate

    # Si el admin está ocupado (modal abierto), NO rotar automáticamente
    if admin_busy:
        triggered_id = ctx.triggered[0]['prop_id']
        # Permitir navegación manual por botón incluso si admin_busy=True
        if triggered_id.startswith('page-rotation-interval'):
            raise dash.exceptions.PreventUpdate

    # Si la rotación fue disparada por el Interval y estamos en /admin, no rotar:
    triggered_id = ctx.triggered[0]['prop_id']
    if triggered_id.startswith('page-rotation-interval') and current_pathname == '/admin':
        raise dash.exceptions.PreventUpdate

    pages = page_state['pages']
    try: current_page_index = pages.index(current_pathname)
    except ValueError: current_page_index = 0
    new_index = (current_page_index + 1) % len(pages)
    if 'next-page-button' in ctx.triggered[0]['prop_id'] or 'page-rotation-interval' in ctx.triggered[0]['prop_id']:
        # Devolvemos la nueva URL y un NUEVO componente Interval para resetear el contador.
        new_interval = dcc.Interval(id='page-rotation-interval', interval=ROTATION_INTERVAL_SECONDS * 1000, n_intervals=0)
        return pages[new_index], [new_interval]
    
    raise dash.exceptions.PreventUpdate

@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('logo-button', 'n_clicks'),
    prevent_initial_call=True
)
def handle_reinicio(n_clicks):
    """Callback para el botón del logo. Al ser presionado, navega a la página principal."""
    if n_clicks and n_clicks > 0: return '/'
    raise dash.exceptions.PreventUpdate

@app.callback(
    Output('admin-busy', 'data'),
    [Input('crud-add-edit-modal', 'is_open'), Input('crud-delete-modal', 'is_open')],
    prevent_initial_call=False
)
def set_admin_busy(is_add_open, is_delete_open):
    return bool(is_add_open) or bool(is_delete_open)

@app.callback(
    Output('termometros-content', 'children'),
    Input('monitoreo-store', 'data'),
    prevent_initial_call=False
)
def update_termometros_content(store_data):
    if not store_data:
        return "Cargando..."
    term = store_data.get('termometros_data')
    if not term:
        return "Cargando..."
    if isinstance(term, dict) and 'body' in term:
        return term['body']
    return term

# --- Clientside callback: aplicar animación slide al cambiar de página ---
app.clientside_callback(
    """
    function(pathname) {
        try {
            var el = document.getElementById('page-content');
            if (!el) return '';
            // Remove previous class to allow re-trigger
            el.classList.remove('slide-left-in');
            // Force reflow so the animation restarts
            void el.offsetWidth;
            el.classList.add('slide-left-in');
            // Remove the class after animation ends to keep DOM clean
            setTimeout(function(){ el.classList.remove('slide-left-in'); }, 700);
        } catch(e) {
            // ignore
        }
        return '';
    }
    """,
    Output('animation-dummy', 'children'),
    Input('url', 'pathname')
)

# -------------------------
# Cache cleaning utilities
# -------------------------
def _partial_clear_monitor_cache():
    """Limpia/recorta las entradas pesadas para evitar crecimiento indefinido."""
    global monitor_cache, _LAST_CACHE_CLEAN_TS
    with cache_lock:
        # Resetear gráficas pesadas a figura vacía
        monitor_cache['fallas_pie_chart'] = go.Figure()
        monitor_cache['internet_history_line_chart'] = go.Figure()
        monitor_cache['internet_storyline_chart'] = go.Figure()
        # Limitar lista de usuarios VPN a un máximo razonable
        vpn = monitor_cache.get('vpn_users_details')
        if isinstance(vpn, list) and len(vpn) > _MAX_VPN_USERS:
            monitor_cache['vpn_users_details'] = vpn[:_MAX_VPN_USERS]
        # marca de limpieza
        _LAST_CACHE_CLEAN_TS = datetime.datetime.now(datetime.timezone.utc).isoformat()
        monitor_cache['last_cache_clean'] = _LAST_CACHE_CLEAN_TS
        logging.info("Cache parcial limpiado automáticamente.")

def cache_cleaner_worker():
    """Worker que ejecuta limpieza periódica del cache."""
    while True:
        try:
            time.sleep(CACHE_CLEAN_INTERVAL_SECONDS)
            logging.info("Ejecutando cache_cleaner_worker...")
            _partial_clear_monitor_cache()
        except Exception as e:
            logging.error(f"Error en cache_cleaner_worker: {e}")

# --- Registrar nuevo worker en la configuración de hilos ---
THREAD_CONFIG = [
    {'name': 'FastWorker', 'target': monitoring_fast_worker, 'thread': None},
    {'name': 'SlowWorker', 'target': monitoring_slow_worker, 'thread': None},
    {'name': 'VerySlowWorker', 'target': monitoring_very_slow_worker, 'thread': None},
    {'name': 'ApiWorker', 'target': monitoring_api_worker, 'thread': None},
    {'name': 'TermometrosWorker', 'target': monitoring_termometros_worker, 'thread': None},
    {'name': 'DbQueryWorker', 'target': monitoring_db_query_worker, 'thread': None},
    {'name': 'ClockWorker', 'target': clock_worker, 'thread': None},
    {'name': 'WelcomeWorker', 'target': welcome_message_worker, 'thread': None},
    {'name': 'CacheCleaner', 'target': cache_cleaner_worker, 'thread': None},
]

def start_monitoring_threads():
    """Inicia todos los hilos de monitoreo configurados."""
    for config in THREAD_CONFIG:
        thread = threading.Thread(target=config['target'], daemon=True, name=config['name'])
        thread.start()
        config['thread'] = thread


# --- PUNTO DE ENTRADA ---
register_all_callbacks(app)
register_admin_callbacks(app)
register_reports_callbacks(app)

if __name__ == '__main__':
    start_monitoring_threads()
    logging.info("La aplicación Dash ha iniciado los hilos de monitoreo y está lista.")
    app.run(host='0.0.0.0', port=8050, debug=False)