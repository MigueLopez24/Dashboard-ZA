import dash
from dash import dcc, html, Output, Input, State, MATCH, ALL, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import datetime
import logging
import time

from ..components.internet_module import crear_layout_internet_speed
from ..components.card_header import crear_header_modulo
from ..data.sql_connector import (
    obtener_detalles_dispositivo, actualizar_credenciales_dispositivo,
    obtener_detalles_servicio_contpaqi, actualizar_servicio_contpaqi
)
from src.plotting.chart_factory import create_faults_pie_chart, create_internet_history_figure, create_storyline_figure
import plotly.graph_objects as go
import json

# --- Registro de Módulos ---
MODULES_CONFIG = {
    'telefonos': {'title': "TELÉFONOS ACTIVOS", 'icon': '/assets/icons/telefono.png'},
    'sitios': {'title': "SITIOS WEB", 'icon': '/assets/icons/sitio_web.png'},
    'servidores': {'title': "SERVIDORES", 'icon': '/assets/icons/servidor.png'},
    'dvr': {'title': "DVR", 'icon': '/assets/icons/camara.png'},
    'internet_speed': {'title': "VELOCIDAD DE INTERNET", 'icon': '/assets/icons/velocidad.png'},
    'checadores': {'title': "CHECADORES", 'icon': '/assets/icons/checadores.png'},
    'contpaqi': {'title': "SERVICIOS CONTPAQI", 'icon': '/assets/icons/contpaqi.png'},
    'fallas': {'title': "FALLAS POR DISPOSITIVO", 'icon': '/assets/icons/fallas.png'},
    'internet_history': {'title': "HISTORIAL DE INTERNET", 'icon': '/assets/icons/historial.png'},
    'pcs': {'title': "PC ENCENDIDAS", 'icon': '/assets/icons/pc.png'},
    'conmutador': {'title': "CONMUTADOR", 'icon': '/assets/icons/conmutador.png'},
}

# --- Definición de Callbacks Estándar y Gráficas ---
CALLBACK_REGISTRY = [
    {'id': 'servidores', 'cache_key': 'servidores_data', 'config_key': 'servidores', 'type': 'standard'},
    {'id': 'dvr', 'cache_key': 'dvr_data', 'config_key': 'dvr', 'type': 'standard'},
    {'id': 'pcs', 'cache_key': 'pcs_data', 'config_key': 'pcs', 'type': 'standard'},
    {'id': 'checadores', 'cache_key': 'checadores_data', 'config_key': 'checadores', 'type': 'standard'},
    {'id': 'sitios-web', 'cache_key': 'sitios_web_data', 'config_key': 'sitios', 'type': 'standard'},
    {'id': 'internet-speed', 'cache_key': 'internet_speed_data', 'config_key': 'internet_speed', 'type': 'standard'},
    {'id': 'contpaqi', 'cache_key': 'contpaqi_data', 'config_key': 'contpaqi', 'type': 'standard'},
    
]


_GRAPHS_BUILD_INTERVAL = 30  # segundos

# Timestamp del último rebuild de gráficas; inicializado a 0 para forzar la primera construcción.
_LAST_GRAPHS_BUILD_TS = 0

def _resolve_module_content(module_data):
    """
    Normaliza el contenido recibido desde el monitor cache para los módulos.
    - Acepta: {'layout': {...}, 'updates': [...]}
    - Acepta: {'header': ..., 'body': ...} (legacy)
    - Acepta: go.Figure o dict-figura (devuelve directamente)
    - Si contiene 'error', lo deja pasar tal cual.
    """
    if not module_data:
        return None

    # Passthrough de errores
    if isinstance(module_data, dict) and 'error' in module_data:
        return module_data

    # Si es figura de plotly o dict de figura -> devolver tal cual
    try:
        import plotly.graph_objects as go
        if isinstance(module_data, go.Figure):
            return module_data
    except Exception:
        pass
    if isinstance(module_data, dict) and ('data' in module_data or 'layout' in module_data or 'figure' in module_data):
        return module_data

    # Nuevo contrato: {'layout': {...}, 'updates': ...}
    if isinstance(module_data, dict) and 'layout' in module_data:
        inner = module_data['layout']
        # Si inner es figura o dict-figura, devolver eso
        if isinstance(inner, dict) and ('data' in inner or 'layout' in inner):
            return inner
        return inner

    # Legacy: ya tiene header/body en top-level
    if isinstance(module_data, dict) and ('header' in module_data or 'body' in module_data or 'items' in module_data):
        return module_data

    # Fallback: envolver en body genérico
    return {'header': None, 'body': str(module_data)}

def create_standard_callback_func(module_info):
    def update_module_ui(data):
        if not data or module_info['cache_key'] not in data:
            raise dash.exceptions.PreventUpdate

        raw = data[module_info['cache_key']]
        resolved = _resolve_module_content(raw)

        # Si vino un error, preservar mensaje de error
        if isinstance(resolved, dict) and 'error' in resolved:
            config = MODULES_CONFIG.get(module_info['config_key'], {'title': module_info['config_key'].upper(), 'icon': ''})
            header = crear_header_modulo(config['title'], config.get('icon', ''), "Error")
            body = html.Div(resolved['error'], className="text-danger p-2")
            return header, body

        # Si resolved es una figura (plotly) o dict-figura, renderizar en un Graph dentro del body
        try:
            import plotly.graph_objects as go
            if isinstance(resolved, go.Figure) or (isinstance(resolved, dict) and ('data' in resolved or 'layout' in resolved)):
                fig = go.Figure(resolved) if not isinstance(resolved, go.Figure) else resolved
                # Construir header desde config si es necesario
                config = MODULES_CONFIG.get(module_info['config_key'], {'title': module_info['config_key'].upper(), 'icon': ''})
                header = crear_header_modulo(config['title'], config.get('icon', ''), "")
                body = dcc.Graph(figure=fig, config={'displayModeBar': False, 'responsive': True}, className="w-100")
                return header, body
        except Exception:
            pass

        # Si resolved es dict con header/body
        if isinstance(resolved, dict):
            header = resolved.get('header') or crear_header_modulo(MODULES_CONFIG.get(module_info['config_key'], {}).get('title', module_info['config_key']), MODULES_CONFIG.get(module_info['config_key'], {}).get('icon', ''), "")
            body = resolved.get('body', html.Div("Datos no disponibles", className="text-white"))
            return header, body

        # Fallback textual
        header = crear_header_modulo(MODULES_CONFIG.get(module_info['config_key'], {}).get('title', module_info['config_key']), MODULES_CONFIG.get(module_info['config_key'], {}).get('icon', ''), "")
        body = html.Div(str(resolved), className="text-white")
        return header, body

    return update_module_ui

def create_graph_callback_func(module_info):
    def update_graph_ui(data):
        if not data or module_info['cache_key'] not in data:
            raise dash.exceptions.PreventUpdate

        raw = data[module_info['cache_key']]
        resolved = _resolve_module_content(raw)

        # Si ya es figura o dict-figura, devolverlo
        try:
            import plotly.graph_objects as go
            if isinstance(resolved, go.Figure):
                return resolved
            if isinstance(resolved, dict) and ('data' in resolved or 'layout' in resolved):
                return go.Figure(resolved)
        except Exception:
            pass

        # Si viene en la forma {"figure": ...} o {"layout": {...}} intentar extraer figure
        if isinstance(raw, dict) and 'figure' in raw:
            try:
                import plotly.graph_objects as go
                return go.Figure(raw['figure'])
            except Exception:
                pass

        # Si no se pudo construir, prevenir actualización
        raise dash.exceptions.PreventUpdate

    return update_graph_ui


def register_all_callbacks(app):
    
    # --- Flujo de Control Global ---
    @app.callback(
        [Output('welcome-message', 'children'),
         Output('usuarios-conectados-content', 'children')],
        Input('monitoreo-store', 'data'),
        prevent_initial_call=True
    )
    def update_welcome_and_users_ui(data):
        if not data or 'welcome_message' not in data: raise dash.exceptions.PreventUpdate
        welcome_message_text = data['welcome_message']
        welcome_message_gif = data.get('welcome_gif')
        usuarios_conectados = data['usuarios_conectados']
        if welcome_message_gif:
            welcome_component = html.Div([
                html.H2(welcome_message_text, className="dashboard-header-welcome-title"),
                html.Img(src=welcome_message_gif, className="dashboard-header-welcome-gif")
            ], className="dashboard-header-welcome d-flex align-items-center")
        else:
            welcome_component = html.H2(welcome_message_text, className="dashboard-header-welcome-title")
        return welcome_component, usuarios_conectados

    # --- Construir figuras centrales y guardarlas en graphs-store ---
    @app.callback(
        Output('graphs-store', 'data'),
        Input('monitoreo-store', 'data'),
        prevent_initial_call=True
    )
    def build_and_store_graphs(mon_data):
        """
        Normaliza y guarda en graphs-store. Acepta:
         - go.Figure -> to_dict()
         - figura dict (con 'data' o 'layout') -> uso directo
         - datos crudos -> llamar a la factory correspondiente
        Se ejecuta cada vez que cambia monitoreo-store para evitar inconsistencias
        al navegar entre páginas.
        """
        if not mon_data:
            raise dash.exceptions.PreventUpdate
        try:
            def normalize(source, factory):
                # ya es plotly Figure
                if isinstance(source, go.Figure):
                    return source.to_dict()
                # ya es dict de figura
                if isinstance(source, dict) and ('data' in source or 'layout' in source):
                    return source
                # intentar construir con la factory (si source es datos crudos)
                try:
                    if source is None:
                        return {}
                    fig = factory(source)
                    return fig.to_dict() if hasattr(fig, 'to_dict') else {}
                except Exception as e:
                    logging.warning("normalize(): no se pudo construir figura con factory: %s", e)
                    return {}

            fallas_src = mon_data.get('fallas_pie_chart')
            history_src = mon_data.get('internet_history_line_chart')
            storyline_src = mon_data.get('internet_storyline_chart')

            fallas_entry = normalize(fallas_src, create_faults_pie_chart)
            history_entry = normalize(history_src, create_internet_history_figure)
            storyline_entry = normalize(storyline_src, create_storyline_figure)

            return {
                'fallas': fallas_entry,
                'internet_history': history_entry,
                'storyline': storyline_entry
            }
        except Exception as e:
            logging.error(f"Error construyendo figuras en graphs-store: {e}")
            raise dash.exceptions.PreventUpdate
            
    # --- Nuevo: propagar figuras a los componentes de la PÁGINA PRINCIPAL (pathname == '/') ---
    @app.callback(
        [Output('fallas-pie-chart', 'figure'),
         Output('internet-history-line-chart', 'figure')],
        [Input('graphs-store', 'data'), Input('url', 'pathname')],
        prevent_initial_call=True
    )
    def update_main_graphs(graphs_data, pathname):
        if pathname != '/': raise dash.exceptions.PreventUpdate
        if not graphs_data: raise dash.exceptions.PreventUpdate
        try:
            def _to_fig(key):
                d = graphs_data.get(key)
                return go.Figure(d) if d else go.Figure()
            return _to_fig('fallas'), _to_fig('internet_history')
        except Exception as e:
            logging.error(f"Error actualizando gráficos de la página principal: {e}")
            return go.Figure(), go.Figure()
    
    # --- Nuevo: propagar figuras a los componentes de INTERNET DETAIL (pathname == '/internet-detail') ---
    @app.callback(
        [Output('internet-detail-history-graph', 'figure'),
         Output('internet-detail-storyline-graph', 'figure')],
        [Input('graphs-store', 'data'), Input('url', 'pathname')],
        prevent_initial_call=True
    )
    def update_internet_detail_graphs(graphs_data, pathname):
        if pathname != '/internet-detail': raise dash.exceptions.PreventUpdate
        if not graphs_data: raise dash.exceptions.PreventUpdate
        try:
            def _to_fig(key):
                d = graphs_data.get(key)
                return go.Figure(d) if d else go.Figure()
            return _to_fig('internet_history'), _to_fig('storyline')
        except Exception as e:
            logging.error(f"Error actualizando gráficos de internet-detail: {e}")
            return go.Figure(), go.Figure()

    # --- Ajuste: update_internet_detail_page ahora sólo maneja velocidad y tabla VPN ---
    @app.callback(
        [Output('internet-detail-speed-content', 'children'),
         Output('internet-detail-vpn-table', 'children')],
        Input('monitoreo-store', 'data'),
        prevent_initial_call=True
    )
    def update_internet_detail_page(data):
        if not data: raise dash.exceptions.PreventUpdate

        live_metrics = data.get('live_internet_metrics', {})
        velocidad_descarga = live_metrics.get('velocidad_descarga', 0); velocidad_carga = live_metrics.get('velocidad_carga', 0); ping = live_metrics.get('ping', 0)
        speed_fig = crear_layout_internet_speed(velocidad_descarga)['figure']
        speed_fig.update_layout(height=90, width=200)

        speed_content_layout = html.Div([
            dcc.Graph(figure=speed_fig, config={'displayModeBar': False}),
            html.Div([
                html.Div([html.Img(src='/assets/icons/ping.png', style={'width': '14px', 'marginRight': '4px'}), html.Span(f"{ping} ms", style={'color': 'white', 'fontSize': '12px'}),], className="d-flex align-items-center"),
                html.Div([html.Img(src='/assets/icons/download.png', style={'width': '14px', 'marginRight': '4px'}), html.Span(f"{velocidad_descarga} Mbps", style={'color': 'white', 'fontSize': '12px'}),], className="d-flex align-items-center"),
                html.Div([html.Img(src='/assets/icons/upload.png', style={'width': '14px', 'marginRight': '4px'}), html.Span(f"{velocidad_carga} Mbps", style={'color': 'white', 'fontSize': '12px'}),], className="d-flex align-items-center"),
            ], className="d-flex justify-content-around my-2 w-100")
        ], className="d-flex flex-column align-items-center w-100")

        # Tabla de usuarios VPN (misma lógica que antes)
        vpn_users = data.get('vpn_users_details', [])
        if isinstance(vpn_users, list) and vpn_users and not isinstance(vpn_users, dict):
            try:
                processed_users = []
                for user in vpn_users:
                    subsession = user.get('subsessions', [{}])[0]
                    processed_users.append({
                        'user_name': user.get('user_name', 'N/A'),
                        'remote_host': user.get('remote_host', 'N/A'),
                        'duration': user.get('duration', 0),
                        'aip': subsession.get('aip', 'N/A'),
                        'in_bytes': subsession.get('in_bytes', 0),
                        'out_bytes': subsession.get('out_bytes', 0)
                    })
                df = pd.DataFrame(processed_users)
                def format_bytes(byte_count):
                    if byte_count is None or not isinstance(byte_count, (int, float)): return "0 B"
                    power = 1024; n = 0; power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
                    while byte_count >= power and n < len(power_labels) -1 : byte_count /= power; n += 1
                    return f"{byte_count:.2f} {power_labels[n]}B"
                df['Recibido'] = df['in_bytes'].apply(format_bytes)
                df['Enviado'] = df['out_bytes'].apply(format_bytes)
                df['Duración'] = df['duration'].apply(lambda s: str(datetime.timedelta(seconds=s)))
                df_display = df.rename(columns={'user_name': 'Usuario', 'remote_host': 'IP Pública', 'aip': 'IP VPN Asignada'})[['Usuario', 'IP Pública', 'IP VPN Asignada', 'Duración', 'Recibido', 'Enviado']]
                vpn_table = html.Div(
                    dbc.Table.from_dataframe(df_display, striped=True, bordered=True, hover=True, color="dark", responsive=True),
                    className="device-table-scroll"
                )
            except Exception as e:
                logging.error(f"Error al procesar datos de VPN para la tabla: {e}"); vpn_table = dbc.Alert(f"Error al procesar datos de VPN: {e}", color="danger")
        else:
            vpn_table = dbc.Alert("No hay usuarios VPN conectados o no se pudieron obtener los datos.", color="info")

        return speed_content_layout, vpn_table

    # --- 2. Callbacks de Módulos ---

    for module in CALLBACK_REGISTRY:
        if module['type'] == 'standard':
            app.callback(
                [Output(f"{module['id']}-header", 'children'),
                 Output(f"{module['id']}-content", 'children')],
                Input('monitoreo-store', 'data'),
                prevent_initial_call=True
            )(create_standard_callback_func(module))
        # los módulos tipo 'graph' se gestionan por graphs-store (no registrar aquí)

    # --- 3. Callback de Teléfonos ---

    # Callback para el módulo de Teléfonos
    @app.callback(
        [Output('telefonos-header', 'children'),
         Output('telefonos-content', 'children')],
        [Input('monitoreo-store', 'data'),
         Input('url', 'pathname')],
        prevent_initial_call=True
    )
    def update_telefonos_module(data, pathname):
        if pathname != '/': raise dash.exceptions.PreventUpdate
        if not data or 'telefonos_data' not in data: raise dash.exceptions.PreventUpdate
        telefonos_data = data['telefonos_data']

        if "error" in telefonos_data:
            telefonos_header = crear_header_modulo(MODULES_CONFIG['telefonos']['title'], MODULES_CONFIG['telefonos']['icon'], "Error")
            telefonos_body = html.Div(telefonos_data['error'], className="text-danger p-2")
        else:
            telefonos_header = telefonos_data.get('header', crear_header_modulo(MODULES_CONFIG['telefonos']['title'], MODULES_CONFIG['telefonos']['icon'], '...'))
            telefonos_body = telefonos_data.get('body', "Cargando contenido...")
        return telefonos_header, telefonos_body

    # Callback separado para el módulo de Conmutador
    @app.callback(
        Output('conmutador-card', 'children'),
        [Input('monitoreo-store', 'data'),
         Input('url', 'pathname')],
        prevent_initial_call=True
    )
    def update_conmutador_module(data, pathname):
        if pathname != '/': raise dash.exceptions.PreventUpdate
        if not data or 'conmutador_data' not in data: raise dash.exceptions.PreventUpdate
        conmutador_data = data['conmutador_data']
        if "error" in conmutador_data:
            return dbc.Alert(conmutador_data['error'], color="danger", className="p-1 m-0")
        return conmutador_data.get('body', "Cargando...")

    # --- 5. Callbacks para el Modal de Edición de Servidores ---
    @app.callback(
        [Output('servidor-edit-modal', 'is_open'),
         Output('servidor-id-store', 'data')],
        [Input({'type': 'abrir-modal-servidor', 'index': ALL}, 'n_clicks'),
         Input('servidor-modal-close-button', 'n_clicks'),
         Input('servidor-modal-save-button', 'n_clicks')], 
        prevent_initial_call=True
    )
    def toggle_servidor_modal(n_clicks_open, n_clicks_close, n_clicks_save):
        ctx = dash.callback_context
        if not ctx.triggered: raise dash.exceptions.PreventUpdate
        trigger_id = ctx.triggered_id

        if 'servidor-modal-close-button' == trigger_id or 'servidor-modal-save-button' == trigger_id:
            return False, None 
        
        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'abrir-modal-servidor':
            for i, n in enumerate(n_clicks_open):
                if n and n > 0 and ctx.triggered_id['index'] == ctx.inputs_list[0][i]['id']['index']:
                    server_id = ctx.triggered_id['index']
                    return True, {'server_id': server_id}
        
        raise dash.exceptions.PreventUpdate

    @app.callback(
        [Output('servidor-edit-modal-header', 'children'),
         Output('servidor-edit-modal-body', 'children')],
        Input('servidor-id-store', 'data'), 
        prevent_initial_call=True
    )
    def update_servidor_modal_content(store_data):
        if not store_data or not store_data.get('server_id'):
            raise dash.exceptions.PreventUpdate

        server_id = store_data['server_id']
        detalles = obtener_detalles_dispositivo(server_id)
        if "error" in detalles:
            header = "Error"
            body = html.Div(f"No se pudieron cargar los detalles: {detalles['error']}", className="text-danger")
        else:
            header = f"Editar Credenciales: {detalles.get('nombre', '')} ({detalles.get('ip', '')})"
            body = dbc.Form([
                dbc.Row([dbc.Label("Usuario", html_for="servidor-usuario-input", width=2), dbc.Col(dbc.Input(type="text", id="servidor-usuario-input", value=detalles.get('usuario', '')), width=10)], className="mb-3"),
                dbc.Row([dbc.Label("Contraseña", html_for="servidor-contrasena-input", width=2), dbc.Col(dbc.Input(type="password", id="servidor-contrasena-input", value=detalles.get('contrasena', '')), width=10)], className="mb-3"),
            ])
        return header, body

    # --- Callback para guardar credenciales de Servidor ---
    @app.callback(
        Output('servidor-edit-notification', 'children'),
        Input('servidor-modal-save-button', 'n_clicks'),
        [State('servidor-id-store', 'data'), State('servidor-usuario-input', 'value'), State('servidor-contrasena-input', 'value')],
        prevent_initial_call=True
    )
    def save_servidor_credentials(n_clicks, server_data, usuario, contrasena):
        if not n_clicks or not server_data: raise dash.exceptions.PreventUpdate
        server_id = server_data.get('server_id')
        resultado = actualizar_credenciales_dispositivo(server_id, usuario, contrasena)
        if "error" in resultado:
            return dbc.Alert(f"Error al guardar: {resultado['error']}", color="danger", duration=4000)
        return dbc.Alert("Credenciales actualizadas con éxito. Los cambios se reflejarán en el próximo ciclo de monitoreo.", color="success", duration=4000)

    # --- Callbacks para el Modal de Edición de Servicios CONTPAQI ---
    @app.callback(
        [
            Output('contpaqi-edit-modal', 'is_open'),
            Output('contpaqi-edit-id-store', 'data'), 
        ],
        [
            Input({'type': 'abrir-modal-contpaqi', 'index': ALL}, 'n_clicks'),
            Input('contpaqi-modal-close-button', 'n_clicks'),
            Input('contpaqi-modal-save-button', 'n_clicks'),
        ],
        prevent_initial_call=True
    )
    def toggle_contpaqi_modal(n_clicks_open, n_clicks_close, n_clicks_save):
        ctx = dash.callback_context
        if not ctx.triggered: raise dash.exceptions.PreventUpdate

        trigger_id = ctx.triggered_id

        if 'contpaqi-modal-close-button' == trigger_id or 'contpaqi-modal-save-button' == trigger_id:
            return False, None # is_open=False, data=None

        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'abrir-modal-contpaqi':
            for i, n in enumerate(n_clicks_open):
                if n and n > 0 and ctx.triggered_id['index'] == ctx.inputs_list[0][i]['id']['index']:
                    service_id = ctx.triggered_id['index']
                    return True, {'service_id': service_id}

        raise dash.exceptions.PreventUpdate 

    @app.callback(
        [Output('contpaqi-edit-modal-header', 'children'),
         Output('contpaqi-edit-modal-body', 'children')],
        Input('contpaqi-edit-id-store', 'data'), 
        prevent_initial_call=True
    )
    def update_contpaqi_modal_content(store_data):
        if not store_data or not store_data.get('service_id'):
            raise dash.exceptions.PreventUpdate

        service_id = store_data['service_id']
        detalles = obtener_detalles_servicio_contpaqi(service_id)

        if "error" in detalles:
            header = "Error"
            body = html.Div(f"No se pudieron cargar los detalles: {detalles['error']}", className="text-danger")
        else:
            header = f"Editar Servicio: {detalles.get('nombre', '')}"
            body = dbc.Form([
                dbc.Row([
                    dbc.Label("Servidor", html_for="contpaqi-servidor-input", width=3),
                    dbc.Col(
                        dbc.Input(
                            type="text",
                            id="contpaqi-servidor-input",
                            value=detalles.get('servidor', ''),
                            placeholder="IP o Hostname del servidor"
                        ),
                        width=9
                    )
                ], className="mb-3"),
                dbc.Row([
                    dbc.Label("Nombre del Servicio", html_for="contpaqi-nombre-servicio-input", width=3),
                    dbc.Col(
                        dbc.Input(
                            type="text",
                            id="contpaqi-nombre-servicio-input",
                            value=detalles.get('nombre_servicio', ''),
                            placeholder="Nombre exacto del servicio en Windows"
                        ),
                        width=9
                    )
                ], className="mb-3"),
                html.Small(
                    "El monitoreo usará estos datos para conectarse y verificar el estado del servicio.",
                    className="text-muted"
                )
            ])
            return header, body

    # --- Callback para guardar servicio CONTPAQI ---
    @app.callback(
        Output('contpaqi-edit-notification', 'children'),
        Input('contpaqi-modal-save-button', 'n_clicks'),
        [
            State('contpaqi-edit-id-store', 'data'),
            State('contpaqi-servidor-input', 'value'),
            State('contpaqi-nombre-servicio-input', 'value'),
        ],
        prevent_initial_call=True
    )
    def save_contpaqi_service(n_clicks, store_data, servidor, nombre_servicio):
        if not n_clicks or not store_data:
            raise dash.exceptions.PreventUpdate

        service_id = store_data.get('service_id')
        if not service_id:
            return dbc.Alert("Error: No se pudo identificar el servicio a actualizar.", color="danger", duration=4000)

        resultado = actualizar_servicio_contpaqi(service_id, servidor, nombre_servicio)

        if "error" in resultado:
            return dbc.Alert(f"Error al guardar: {resultado['error']}", color="danger", duration=4000)

        return dbc.Alert("Servicio actualizado con éxito. Los cambios se reflejarán en el próximo ciclo.", color="success", duration=4000)