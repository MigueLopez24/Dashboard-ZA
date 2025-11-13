# src/callbacks/admin_callbacks.py

from dash import dcc, html, Output, Input, State, MATCH, ALL
import dash_bootstrap_components as dbc
import dash
import pandas as pd
import logging
from datetime import datetime

from ..data.sql_connector import obtener_dispositivos_crud, obtener_edificios, eliminar_dispositivo, insertar_o_actualizar_dispositivo

# -------------------------- FUNCIONES DE AYUDA DE LAYOUT --------------------------

def generate_device_table(devices_data, search_term=""):
    """Genera la tabla interactiva de dispositivos con botones de acción."""
    if devices_data.get('error'):
        return dbc.Alert(f"Error al cargar datos: {devices_data['error']}", color="danger")
        
    df = pd.DataFrame(devices_data['data'])

    if df.empty:
        return html.Div([
            dbc.Button("Agregar Nuevo Dispositivo", id="add-device-button", color="success", className="mb-3 w-100"),
            dbc.Alert("No hay dispositivos de este tipo registrados.", color="warning", className="mt-4 text-center")
        ])

    # --- Agregar columna de descripción si existe ---
    if 'descripcion' not in df.columns:
        df['descripcion'] = ""

    # --- Filtrar por término de búsqueda ---
    if search_term and not df.empty:
        search_term = search_term.lower()
        # Asegurarse de que las columnas de búsqueda existan en el DataFrame
        search_cols = [col for col in ['nombre', 'descripcion', 'direccion'] if col in df.columns]
        df = df[df.apply(
            lambda row: any(str(row[col]).lower().find(search_term) != -1 for col in search_cols),
            axis=1
        )]


    # Mapeo de columnas para la visualización
    df = df.rename(columns={
        'id': 'ID', 'nombre': 'Nombre', 'descripcion': 'Descripción', 'direccion': 'Dirección/IP', 
        'ultima_verificacion': 'Última Verificación', 'nombre_edificio': 'Edificio',
        'estado': 'Estado'
    })
    
    # Agregar botones de acción
    df['Acciones'] = [
        html.Div([
            dbc.Button("Editar", id={'type': 'edit-device-button', 'index': row['ID']}, 
                       color="primary", size="sm", className="me-2", outline="True"),
            dbc.Button("Eliminar", id={'type': 'delete-device-button', 'index': row['ID']}, 
                       color="danger", size="sm", outline="True")
        ], className="d-flex justify-content-center")
        for index, row in df.iterrows()
    ]
    
    # Formatear la columna de fecha de forma segura
    def safe_strftime(x):
        if pd.notna(x) and isinstance(x, datetime):
            return x.strftime('%Y-%m-%d %H:%M')
        return x if isinstance(x, str) else 'N/A'

    df['Última Verificación'] = df['Última Verificación'].apply(safe_strftime)
    
    # Seleccionar y reordenar columnas
    cols = ['Nombre', 'Descripción', 'Dirección/IP', 'Edificio', 'Estado', 'Acciones']
    
    table = dbc.Table.from_dataframe(
        df[cols],
        striped=True, 
        bordered=True, 
        hover=True,
        color="dark",
        responsive=True,
        className="text-center"
    )
    
    # Contenedor deslizable para la tabla
    scrollable_table_container = html.Div(
        table,
        className="device-table-scroll"
    )
    
    return html.Div([
        dbc.Button("Agregar Nuevo Dispositivo", id="add-device-button", color="success", className="mb-3"),
        scrollable_table_container
    ])

def generate_modal_form(device_data, is_new=False):
    """Genera el cuerpo del modal de edición/creación."""
    
    # Obtener datos auxiliares
    edificios = obtener_edificios()
    edificio_options = [{'label': 'N/A', 'value': ''}] + [{'label': e['nombre'], 'value': e['id']} for e in edificios]
    
    # Determinar si es un dispositivo especial para mostrar campos extra
    is_special = device_data.get('is_special', False)
    nombre_tipo = device_data.get('nombre_tipo', 'Dispositivo')
    id_tipo = device_data.get('id_tipo')

    # --- Determinar si es servidor ---
    es_servidor = False
    if isinstance(nombre_tipo, str) and nombre_tipo.lower() in ['servidor', 'servidores']:
        es_servidor = True
    # Permitir edición de usuario/contraseña si es servidor O si ya existen valores guardados (para edición)
    usuario_guardado = device_data.get('usuario', '')
    contrasena_guardada = device_data.get('contrasena', '')
    puede_editar_credenciales = es_servidor or (usuario_guardado or contrasena_guardada)

    # Rellenar valores iniciales
    d = device_data if not is_new else {}

    # Asegurar que id_edificio sea una cadena vacía si es None para que el Dropdown lo seleccione correctamente
    if 'id_edificio' in d and (d['id_edificio'] is None or d['id_edificio'] == 0):
        d['id_edificio'] = ''
    form_items = [
        # Campos ocultos para el estado
        dcc.Store(id='modal-id-dispositivo', data=d.get('id', None)),
        dcc.Store(id='modal-is-special', data=is_special),
        dcc.Store(id='modal-id-tipo', data=id_tipo),

        dbc.Row([
            dbc.Label("Nombre", html_for="modal-nombre-input", width=2, className="text-dark"), 
            dbc.Col(dbc.Input(type="text", id="modal-nombre-input", value=d.get('nombre', '')), width=10)
        ], className="mb-3"),

        dbc.Row([
            dbc.Label("Descripción", html_for="modal-descripcion-input", width=2, className="text-dark"),
            dbc.Col(
                dbc.Textarea(id="modal-descripcion-input", value=d.get('descripcion', ''), placeholder="Descripción del dispositivo"),
                width=10
            )
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Label("Dirección/IP", html_for="modal-direccion-input", width=2, className="text-dark"), 
            dbc.Col(dbc.Input(type="text", id="modal-direccion-input", value=d.get('direccion', '')), width=10)
        ], className="mb-3"),

        dbc.Row([
            dbc.Label("Edificio", html_for="modal-edificio-select", width=2, className="text-dark"), 
            dbc.Col(dcc.Dropdown(id="modal-edificio-select", options=edificio_options, value=d.get('id_edificio'), placeholder="Seleccionar edificio (Opcional)", style={'color': 'black'}), width=10)
        ], className="mb-3"),

        # Credenciales
        dbc.Row([
            dbc.Label("Usuario", html_for="modal-usuario-input", width=2, className="text-dark"), 
            dbc.Col(
                dbc.Input(
                    type="text",
                    id="modal-usuario-input",
                    value=usuario_guardado,
                    disabled=not puede_editar_credenciales
                ),
                width=10
            )
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Label("Contraseña", html_for="modal-contrasena-input", width=2, className="text-dark"), 
            dbc.Col(
                dbc.Input(
                    type="password",
                    id="modal-contrasena-input",
                    value=contrasena_guardada,
                    disabled=not puede_editar_credenciales
                ),
                width=10
            )
        ], className="mb-3"),
    ]
    
    # Campos Especiales (solo para DISPOSITIVOS_ESPECIALES)
    if is_special:
        # Checador (ID 6)
        if id_tipo == 6: 
            form_items.append(
                dbc.Row([
                    dbc.Label("Puerto Checador", html_for={'type': 'modal-puerto-checador-input', 'index': 'dynamic'}, width=2, className="text-dark"), 
                    dbc.Col(dbc.Input(type="number", id={'type': 'modal-puerto-checador-input', 'index': 'dynamic'}, value=d.get('puerto_checador', 4370)), width=10)
                ], className="mb-3")
            )
        # DVR (ID 4) o Firewall (ID 12)
        elif id_tipo in [4, 12]:
             form_items.append(
                dbc.Row([
                    dbc.Label("Puerto Web", html_for={'type': 'modal-puerto-web-input', 'index': 'dynamic'}, width=2, className="text-dark"), 
                    dbc.Col(dbc.Input(type="number", id={'type': 'modal-puerto-web-input', 'index': 'dynamic'}, value=d.get('puerto_web', 80)), width=10)
                ], className="mb-3")
            )

    return dbc.Form(form_items)

# -------------------------- REGISTRO DE CALLBACKS --------------------------

def register_admin_callbacks(app):
    """
    Registra los callbacks específicos para la página de administración (CRUD).
    """
    

    # 2. Callback para cargar/filtrar la tabla y guardar metadata
    @app.callback(
        [Output('dispositivos-crud-container', 'children'),
         Output('crud-data-store', 'data', allow_duplicate=True),
         Output('search-bar-row', 'style')],
        [Input('dropdown-tipo-dispositivo', 'value'),
         Input('search-device-input', 'value')],
        State('crud-data-store', 'data'),
        prevent_initial_call=True
    )
    def load_or_filter_device_table(id_tipo_seleccionado, search_term, current_store):
        ctx = dash.callback_context
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if id_tipo_seleccionado is None:
            return dbc.Alert("Selecciona un tipo de dispositivo para comenzar a gestionar.", color="info", className="mt-4"), dash.no_update, {'display': 'none'}

        # Si el trigger es el dropdown, recargamos los datos desde la BD
        if trigger_id == 'dropdown-tipo-dispositivo':
            data = obtener_dispositivos_crud(id_tipo_seleccionado)
            # Guardar metadata para usar en acciones CRUD
            metadata = {
                'id_tipo': data.get('id_tipo'),
                'nombre_tipo': data.get('nombre_tipo'),
                'is_special': data.get('is_special'),
                'data': data.get('data', []), # Guardamos la lista completa
                'data_map': {d['id']: d for d in data.get('data', [])} # Mapa para edición rápida
            }
            table = generate_device_table(data, search_term)
            return table, metadata, {'display': 'block'}
        
        # Si el trigger es la barra de búsqueda, filtramos los datos ya guardados en el store
        elif trigger_id == 'search-device-input' and current_store:
            filtered_data = {'data': current_store.get('data', [])} # Usamos los datos completos del store
            table = generate_device_table(filtered_data, search_term)
            return table, dash.no_update, dash.no_update

        raise dash.exceptions.PreventUpdate

    # 3. Callback para abrir los modales (Agregar, Editar, Eliminar)
    @app.callback(
        [Output('crud-add-edit-modal', 'is_open'),
         Output('crud-delete-modal', 'is_open'),
         Output('crud-modal-header', 'children'),
         Output('crud-modal-body', 'children'),
         Output('crud-delete-modal-body', 'children'),
         Output('crud-data-store', 'data')], # Actualizamos el store con el ID del dispositivo a afectar
        [Input('add-device-button', 'n_clicks'),
         Input({'type': 'edit-device-button', 'index': ALL}, 'n_clicks'),
         Input({'type': 'delete-device-button', 'index': ALL}, 'n_clicks'),
         Input('crud-modal-close', 'n_clicks'),
         Input('crud-delete-modal-close', 'n_clicks')],
        [State('crud-data-store', 'data')],
        prevent_initial_call=True
    )
    def handle_modal_toggles(n_add, n_edit, n_delete, n_close_edit, n_close_delete, current_store):
        ctx = dash.callback_context
        if not ctx.triggered: raise dash.exceptions.PreventUpdate
        
        trigger = ctx.triggered[0]
        prop_id = trigger['prop_id']
        
        # Cierre de modales
        if 'crud-modal-close' in prop_id or 'crud-delete-modal-close' in prop_id:
            current_store['device_to_affect_id'] = None # Limpiamos el ID
            return False, False, dash.no_update, dash.no_update, dash.no_update, current_store
        
        # Abrir Modal de Añadir
        if 'add-device-button' in prop_id and trigger.get('value'):
            header = f"Agregar Nuevo {current_store.get('nombre_tipo', 'Dispositivo')}"
            temp_data = {'id': 'NEW', 'id_tipo': current_store['id_tipo'], 'nombre_tipo': current_store['nombre_tipo'], 'is_special': current_store['is_special']}
            body = generate_modal_form(temp_data, is_new=True)
            current_store['device_to_affect_id'] = 'NEW'
            return True, False, header, body, dash.no_update, current_store
            
        # Abrir Modal de Editar
        if 'edit-device-button' in prop_id and trigger.get('value'):
            device_id = ctx.triggered_id['index']
            # --- CORRECCIÓN: Asegurarse de que device_id sea del mismo tipo que las llaves de data_map ---
            device_info = current_store['data_map'].get(device_id) or current_store['data_map'].get(str(device_id))
            if not device_info:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            header = f"Editar {current_store.get('nombre_tipo', 'Dispositivo')}: {device_info.get('nombre', '')}"
            # --- CORRECCIÓN: Pasar todos los datos del dispositivo al formulario ---
            edit_data = {**device_info, 'id_tipo': current_store['id_tipo'], 'is_special': current_store['is_special']}
            body = generate_modal_form(edit_data, is_new=False)
            current_store['device_to_affect_id'] = edit_data.get('id') # Aseguramos que el ID correcto se guarda
            return True, False, header, body, dash.no_update, current_store

        # Abrir Modal de Eliminar
        if 'delete-device-button' in prop_id and trigger.get('value'):
            device_id = ctx.triggered_id['index']
            device_info = current_store['data_map'].get(device_id, {})
            body_text = html.Div([
                html.P(f"¿Estás seguro de que deseas eliminar permanentemente el dispositivo '{device_info.get('nombre', 'N/A')}' (ID: {device_id})?", className="lead text-dark"),
                dbc.Alert("Esta acción no se puede deshacer y eliminará registros de fallas asociados.", color="danger")
            ])
            current_store['device_to_affect_id'] = device_id
            return False, True, dash.no_update, dash.no_update, body_text, current_store
            
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # 4. Callback para confirmar la eliminación (Lógica REAL)
    @app.callback(
        [Output('crud-delete-modal', 'is_open', allow_duplicate=True),
         Output('crud-notification-output', 'children', allow_duplicate=True),
         Output('dropdown-tipo-dispositivo', 'value', allow_duplicate=True)], # Recargar la tabla
        Input('crud-delete-modal-confirm', 'n_clicks'),
        [State('crud-data-store', 'data'),
         State('dropdown-tipo-dispositivo', 'value')],
        prevent_initial_call=True
    )
    def confirm_delete_device(n_clicks, crud_data, current_id_tipo):
        if not n_clicks or not current_id_tipo: raise dash.exceptions.PreventUpdate
        
        device_id = crud_data.get('device_to_affect_id')
        is_special = crud_data.get('is_special')
        
        if not device_id:
            return False, dbc.Alert("Error: ID del dispositivo no encontrado.", color="danger", duration=4000), dash.no_update
        
        # Llamada a la función real de eliminación en cascada
        resultado = eliminar_dispositivo(device_id, is_special)
        
        if "error" in resultado:
            alert = dbc.Alert(f"Error al eliminar el dispositivo ID {device_id}: {resultado['error']}", color="danger", duration=6000)
        else:
            alert = dbc.Alert(f"Dispositivo ID {device_id} eliminado con éxito.", color="success", duration=4000)

        # Usamos el valor del dropdown para forzar la recarga de la tabla con los datos actualizados
        return False, alert, current_id_tipo 
        
    # 5. Callback para guardar 
    @app.callback(
        [Output('crud-add-edit-modal', 'is_open', allow_duplicate=True),
         Output('crud-notification-output', 'children', allow_duplicate=True),
         Output('dropdown-tipo-dispositivo', 'value', allow_duplicate=True)],
        Input('crud-modal-save', 'n_clicks'),
        [State('crud-data-store', 'data'),
         State('modal-id-dispositivo', 'data'),
         State('modal-is-special', 'data'),
         State('modal-id-tipo', 'data'),
         State('modal-nombre-input', 'value'),
         State('modal-descripcion-input', 'value'),
         State('modal-direccion-input', 'value'),
         State('modal-usuario-input', 'value'),
         State('modal-contrasena-input', 'value'),
         State('modal-edificio-select', 'value'),
         State({'type': 'modal-puerto-checador-input', 'index': ALL}, 'value'), 
         State({'type': 'modal-puerto-web-input', 'index': ALL}, 'value'),      
         State('dropdown-tipo-dispositivo', 'value')
        ],
        prevent_initial_call=True
    )
    def save_device(
        n_clicks, crud_data, device_id, is_special, id_tipo, nombre, descripcion, direccion, usuario, contrasena,
        id_edificio, puerto_checador, puerto_web, current_id_tipo
    ):
        if not n_clicks: raise dash.exceptions.PreventUpdate

        if not nombre or not nombre.strip() or not direccion or not direccion.strip():
            alert = dbc.Alert("El 'Nombre' y la 'Dirección/IP' son campos obligatorios.", color="warning", duration=5000)
            return True, alert, dash.no_update

        if device_id in [None, '', 0]:
            device_id = 'NEW'
        if id_edificio in [None, '', 0, '0']:
            id_edificio_db = None
        else:
            id_edificio_db = id_edificio

        puerto_checador_val = puerto_checador[0] if puerto_checador else None
        puerto_web_val = puerto_web[0] if puerto_web else None

        data_to_save = {
            'device_id': device_id,
            'is_special': is_special,
            'id_tipo': id_tipo,
            'nombre': nombre,
            'descripcion': descripcion,
            'direccion': direccion,
            'usuario': usuario,
            'contrasena': contrasena,
            'id_edificio': id_edificio_db,
            'puerto_checador': puerto_checador_val,
            'puerto_web': puerto_web_val,
        }

        resultado = insertar_o_actualizar_dispositivo(data_to_save)
        action = "actualizado" if device_id != 'NEW' else "agregado"

        if "success" in resultado:
            alert = dbc.Alert(f"Dispositivo '{nombre}' {action} con éxito.", color="success", duration=4000)
        else:
            alert = dbc.Alert(f"Error al {action} el dispositivo: {resultado.get('error', 'Error desconocido')}", color="danger", duration=6000)

        return False, alert, current_id_tipo