# src/layouts/admin_layout.py

from dash import dcc, html
import dash_bootstrap_components as dbc
from ..data.sql_connector import obtener_tipos_dispositivos_crud
from ..components.dashboard_header_row import create_dashboard_header_row

def create_admin_layout():
    """
    Crea el layout para la página de administración (CRUD de dispositivos).
    """
    
    tipos_dispositivo = obtener_tipos_dispositivos_crud()
    
    options = [
        {'label': d['nombre'], 'value': d['id']} for d in tipos_dispositivo
    ]
    
    return dbc.Container([
        # Fila 1: Header Reutilizable
        create_dashboard_header_row(),

        # Título de la página
        dbc.Row([
            dbc.Col(
                html.H1("⚙️ Panel de Gestión de Dispositivos", className="text-white text-center"),
                className="text-center mt-2 mb-2"
            )
        ], className="mx-0"),

        # Selección de tipo de dispositivo
        dbc.Row([
            dbc.Col(
                html.Div([
                    # label en bloque y centrado para asegurar alineación
                    dbc.Label("Seleccionar Tipo de Dispositivo a Gestionar:", html_for="dropdown-tipo-dispositivo", className="text-white d-block text-center w-100"),
                    # Wrapper para controlar ancho y centrado del dropdown
                    html.Div(
                        dcc.Dropdown(
                            id='dropdown-tipo-dispositivo',
                            options=options,
                            placeholder="Elige un tipo de dispositivo...",
                            className="mb-2 admin-dropdown"
                        ),
                        className="admin-dropdown-wrapper"
                    ),
                ]),
                lg=6, xl=4, md=8, sm=12, xs=12, className="mx-auto"
            )
        ], className="mt-1 mx-0 admin-controls-row"),  # fila más compacta

        # Barra de búsqueda (ahora visible y 100% ancho)
        dbc.Row([
            dbc.Col(
                dbc.Input(
                    id='search-device-input',
                    placeholder='Buscar por Nombre, Descripción, Dirección/IP...',
                    type='text',
                    className='mb-2 w-100',
                    style={'width': '100%'}
                ),
                lg=4, xl=6, md=8, sm=12, xs=12, className="mx-auto"
            )
        ], id='search-bar-row', className="mx-0 admin-controls-row"), 

        # Contenedor de la tabla de dispositivos dentro de una Card con scroll interno
        dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader("Dispositivos"),
                    dbc.CardBody(
                        html.Div(
                            id='dispositivos-crud-container',
                            children=dbc.Alert("Selecciona un tipo de dispositivo para comenzar a gestionar.", color="info", className="mt-2"),
                            className="device-table-scroll"
                        ),
                        className="p-1"
                    )
                ], className="bg-dark text-white h-100"),
                lg=11, md=12, xs=12, className="mx-auto", style={'minWidth': 0}
            )
        ], className="mb-2 mx-0"),

        # Botón oculto requerido por callbacks que referencian add-device-button
        html.Button(id='add-device-button', n_clicks=0, style={'display': 'none'}),

        # --- Alertas y Stores (Necesarios para el estado de la página) ---
        html.Div(id='crud-notification-output', className='crud-notification-output'),
        dcc.Store(id='crud-data-store', data={}), 
        dbc.Modal(
            [
                dbc.ModalHeader(id='crud-modal-header'),
                dbc.ModalBody(id='crud-modal-body'),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="crud-modal-close", className="ms-auto", n_clicks=0, color="secondary"),
                    dbc.Button("Guardar", id="crud-modal-save", className="ms-2", n_clicks=0, color="primary"),
                ]),
            ],
            id="crud-add-edit-modal",
            is_open=False,
            centered=True,
            backdrop="static",
            size="lg"
        ),
        # --- Modal de Confirmación de Eliminación ---
        dbc.Modal(
            [
                dbc.ModalHeader("Confirmar Eliminación"),
                dbc.ModalBody(id='crud-delete-modal-body', children="¿Estás seguro de que deseas eliminar este dispositivo? Esta acción es irreversible."),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="crud-delete-modal-close", n_clicks=0, color="secondary"),
                    dbc.Button("Eliminar", id="crud-delete-modal-confirm", n_clicks=0, color="danger"),
                ]),
            ],
            id="crud-delete-modal",
            is_open=False,
            centered=True,
            backdrop="static",
        ),

    ], fluid=True, className="admin-layout-container p-0")