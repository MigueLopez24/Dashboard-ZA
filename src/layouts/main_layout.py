# src/layouts/main_layout.py 
from dash import html, dcc
import dash_bootstrap_components as dbc
from ..components.card_header import crear_header_modulo
from ..components.dashboard_header_row import create_dashboard_header_row
from src.config import OVERSCAN_PADDING

def create_main_layout(app):
    """
    Crea y retorna el layout principal del dashboard.
    """
    
    # --- Placeholders iniciales para el contenido de las tarjetas ---
    telefonos_content_initial = "Cargando..."
    sitios_web_content_initial = "Cargando..." 
    servidores_content_initial = "Cargando..."
    dvr_content_initial = "Cargando..."
    internet_speed_content_initial = "Cargando..."
    checadores_content_initial = "Cargando..."
    contpaqi_content_initial = "Cargando..."
    pcs_content_initial = "Cargando..."
    # --------------------------------------------------------------------------

    return dbc.Container([
         # Fila 1: Título, Logo y Relojes
         create_dashboard_header_row(),

        # Fila 2: Teléfonos, Sitios Web, Servidores, DVR
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(id='telefonos-header', children=crear_header_modulo("TELÉFONOS ACTIVOS", '/assets/icons/telefono.png')),                
                html.Div(
                    id='conmutador-card',
                    children=[], className="mb-2 conmutador-card"),
                dbc.CardBody([ # Add flex: 1 for vertical space distribution
                    html.Div(id='telefonos-content', children=telefonos_content_initial, className="text-white")
                ], className="text-white p-2")
            ], className="bg-dark text-white h-100"), lg=3, md=6, xs=12, style={'minWidth': 0}),

            dbc.Col(dbc.Card([
                dbc.CardHeader(id='sitios-web-header', children=crear_header_modulo("SITIOS WEB", '/assets/icons/sitio_web.png')),
                dbc.CardBody(id='sitios-web-content', children=sitios_web_content_initial, className="text-white") # <--- USO CORREGIDO
            ], className="bg-dark text-white h-100"), lg=3, md=6, xs=12, style={'minWidth': 0}),

            dbc.Col(dbc.Card([
                dbc.CardHeader(id='servidores-header', children=crear_header_modulo("SERVIDORES", '/assets/icons/servidor.png')),
                dbc.CardBody(id='servidores-content', children=servidores_content_initial, className="text-white")
            ], className="bg-dark text-white h-100"), lg=3, md=6, xs=12, style={'minWidth': 0}),

            dbc.Col(dbc.Card([
                dbc.CardHeader(id='dvr-header', children=crear_header_modulo("DVR", '/assets/icons/camara.png')),
                dbc.CardBody(id='dvr-content', children=dvr_content_initial, className="text-white")
            ], className="bg-dark text-white h-100"), lg=3, md=6, xs=12, style={'minWidth': 0}),
        ], className="g-3 mb-3 flex-nowrap"),

        # Fila 3: Velocidad de Internet, Checadores, Servicios ContpaQi, Fallas
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(id='internet-speed-header', children=crear_header_modulo("VELOCIDAD DE INTERNET", '/assets/icons/velocidad.png')),
                dbc.CardBody(id='internet-speed-content', children=internet_speed_content_initial, className="text-white")
            ], className="bg-dark text-white h-100"), lg=3, md=6, xs=12, style={'minWidth': 0}),

            # Columna: Checadores (existente)
            dbc.Col(dbc.Card([
                dbc.CardHeader(id='checadores-header', children=crear_header_modulo("CHECADORES", '/assets/icons/checadores.png')),
                dbc.CardBody(id='checadores-content', children=checadores_content_initial, className="text-white")
            ], className="bg-dark text-white h-100"), lg=2, md=6, xs=12, style={'minWidth': 0}),

            # (termómetros movidos a la fila 4, junto a Historial de Internet)

            dbc.Col(dbc.Card([
                dbc.CardHeader(id='contpaqi-header', children=crear_header_modulo("SERVICIOS CONTPAQI", '/assets/icons/contpaqi.png')),
                dbc.CardBody(id='contpaqi-content', children=contpaqi_content_initial, className="text-white")
            ], className="bg-dark text-white h-100"), lg=3, md=6, xs=12, style={'minWidth': 0}),

            dbc.Col(dbc.Card([
                dbc.CardHeader(
                    html.Div([
                        crear_header_modulo("FALLAS POR DISPOSITIVO", '/assets/icons/fallas.png'),
                        html.Div([
                            dbc.DropdownMenu(
                                [
                                    dbc.DropdownMenuItem("Últimos 7 días", id="download-report-7-days"),
                                    dbc.DropdownMenuItem("Últimos 30 días", id="download-report-30-days"),
                                    dbc.DropdownMenuItem(divider=True),
                                    dbc.DropdownMenuItem("Rango personalizado...", id="download-report-custom"),
                                ],
                                label=html.Img(src='/assets/icons/excel.png', style={'height': '26px'}),
                                color="secondary",
                                align_end=True,
                                toggle_style={'background': 'transparent', 'border': 'none', 'padding': '0'},
                                className="ms-auto",
                            ),
                            dbc.Tooltip("Descargar reporte de fallas", target="fallas-header", placement="top")
                        ], id="fallas-dropdown-container")
                    ], className="d-flex align-items-center justify-content-between w-100"),
                    id='fallas-header'
                ),
                dbc.CardBody(
                    html.Div(
                        dcc.Graph(
                            id='fallas-pie-chart',
                            config={'displayModeBar': False, 'responsive': True},
                            className="main-graph-pie",
                            style={'width': '100%', 'height': '100%', 'minHeight': '120px'}  # <-- forzar tamaño responsivo dentro del módulo
                        ),
                        className="d-flex justify-content-center align-items-center w-100"
                    ),
                    className="p-0"
                )
            ], className="bg-dark text-white h-100"), lg=3, md=6, xs=12, style={'minWidth': 0}),
        ], className="g-3 mb-3 flex-nowrap"),

        # Fila 4: Historial de Internet, Termómetros y PC Encendidas
        dbc.Row([
            # Historial de Internet (ahora más estrecho para dejar espacio a termómetros)
            dbc.Col(dbc.Card([
                dbc.CardHeader(id='internet-history-header', children=crear_header_modulo("HISTORIAL DE INTERNET", '/assets/icons/historial.png')),
                dbc.CardBody(
                    dcc.Graph(
                        id='internet-history-line-chart',
                        config={'displayModeBar': False, 'responsive': True},
                        style={'width': '100%', 'height': '100%', 'minHeight': '150px'}
                    ),
                    className="p-0 h-100"
                )
            ], className="bg-dark text-white h-100"), lg=6, md=12, xs=12, style={'minWidth': 0}),

            # Nueva columna: Termómetros (al lado derecho de Historial)
            dbc.Col(dbc.Card([
                dbc.CardHeader(id='termometros-header', children=crear_header_modulo("TERMÓMETROS", '/assets/icons/termometro.png')),
                dbc.CardBody(id='termometros-content', children="Cargando...", className="text-white")
            ], className="bg-dark text-white h-100"), lg=2, md=12, xs=12, style={'minWidth': 0}),

            # PCs permanecen a la derecha
            dbc.Col(dbc.Card([
                dbc.CardHeader(id='pcs-header', children=crear_header_modulo("PC ENCENDIDAS", '/assets/icons/pc.png')),
                dbc.CardBody(id='pcs-content', children=pcs_content_initial, className="text-white")
            ], className="bg-dark text-white h-100"), lg=4, md=12, xs=12, style={'minWidth': 0}),
        ], className="g-3 mb-3 flex-nowrap"),

        # --- Modal para Edición de Servidores ---
        dbc.Modal(
            [
                dbc.ModalHeader(id='servidor-edit-modal-header'),
                dbc.ModalBody(id='servidor-edit-modal-body'),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="servidor-modal-close-button", className="ms-auto", n_clicks=0, color="secondary"),
                    dbc.Button("Guardar Cambios", id="servidor-modal-save-button", className="ms-2", n_clicks=0, color="primary"),
                ]),
            ],
            id="servidor-edit-modal",
            is_open=False,
            centered=True,
            backdrop="static",
            size="xl",  # <-- Hacer el modal más grande
        ),
        dcc.Store(id='servidor-id-store', storage_type='memory'),
        html.Div(id='servidor-edit-notification', className='edit-notification'),

        # --- Modal para Edición de Servicios CONTPAQI ---
        dbc.Modal(
            [
                dbc.ModalHeader(id='contpaqi-edit-modal-header'),
                dbc.ModalBody(id='contpaqi-edit-modal-body'),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="contpaqi-modal-close-button", className="ms-auto", n_clicks=0, color="secondary"),
                    dbc.Button("Guardar Cambios", id="contpaqi-modal-save-button", className="ms-2", n_clicks=0, color="primary"),
                ]),
            ],
            id="contpaqi-edit-modal",
            is_open=False,
            centered=True,
            backdrop="static",
            size="lg",
        ),
        dcc.Store(id='contpaqi-edit-id-store', storage_type='memory'),
        html.Div(id='contpaqi-edit-notification', className='edit-notification')
    ,
        # --- Modal para reporte de fallas personalizado ---
        dbc.Modal([
            dbc.ModalHeader("Reporte de Fallas Personalizado"),
            dbc.ModalBody([
                dbc.Label("Número de días a incluir en el reporte:"),
                dbc.Input(id="report-days-input", type="number", min=1, max=365, step=1, value=15),
                dbc.FormText("Introduce un número entre 1 y 365."),
                html.Div(id="report-days-feedback", className="text-danger mt-2")
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="report-modal-close-button", color="secondary"),
                dbc.Button("Generar Reporte", id="report-modal-generate-button", color="primary"),
            ]),
        ], id="report-custom-days-modal", is_open=False, centered=True),

        # Componente para manejar la descarga de archivos
        dcc.Download(id="download-fallas-excel-dcc"),
    ], fluid=True, className="main-layout-container w-100", style=OVERSCAN_PADDING)