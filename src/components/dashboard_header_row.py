# src/components/dashboard_header_row.py

from dash import html, dcc
import dash_bootstrap_components as dbc

CARD_BACKGROUND_COLOR = '#2A2A2A'

def create_dashboard_header_row():
    """
    Crea la fila superior del dashboard que contiene el logo, bienvenida,
    usuarios conectados y relojes.
    """
    
    # --- Placeholders iniciales para el contenido (se llenarán con callbacks) ---
    welcome_message_initial = "Cargando..."
    usuarios_conectados_initial = "..."
    reloj_content_initial = "Cargando..."
    fecha_content_initial = "01/01/2024"
    # --------------------------------------------------------------------------

    return dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    html.Div([
                        dcc.Loading(
                            type="circle",
                            children=html.Button(
                                html.Img(
                                    src='/assets/icons/logo_za.png',
                                    className="dashboard-header-icon",
                                ),
                                id='logo-button',
                                n_clicks=0,
                                className="dashboard-header-logo-btn"
                            )
                        ),
                        html.Div(id='welcome-message', className="dashboard-header-welcome"),
                        # Botón oculto global requerido por callbacks (evita ReferenceError)
                        html.Button(id='add-device-button', n_clicks=0, style={'display': 'none'}),
                    ], className="d-flex align-items-center w-100")
                ),
                className="h-100",
                style={'backgroundColor': CARD_BACKGROUND_COLOR}
            ),
            lg=3, md=12, xs=12, style={'minWidth': 0}
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    html.Div([
                        html.Img(
                            src='assets/icons/usuarios.png',
                            className="dashboard-header-icon",
                        ),
                        html.Div(id='usuarios-conectados-content', children=usuarios_conectados_initial, className="dashboard-header-value")
                    ], className="d-flex align-items-center justify-content-center w-100")
                ), className="h-100", style={'backgroundColor': CARD_BACKGROUND_COLOR}
            ),
            lg=2, md=4, xs=12, style={'minWidth': 0}
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    html.Div([
                        html.Img(
                            src='assets/icons/reloj.png',
                            className="dashboard-header-icon",
                        ),
                        html.Div(id='reloj-hora-content', children=reloj_content_initial, className="dashboard-header-value")
                    ], className="d-flex align-items-center justify-content-center w-100")
                ), className="h-100", style={'backgroundColor': CARD_BACKGROUND_COLOR}
            ),
            lg=2, md=4, xs=12, style={'minWidth': 0}
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    html.Div([
                        html.Img(src='assets/icons/calendario.png', className="dashboard-header-icon"),
                        html.Div(id='reloj-fecha-content', children=fecha_content_initial, className="dashboard-header-value")
                    ], className="d-flex align-items-center justify-content-center w-100")
                ), className="h-100", style={'backgroundColor': CARD_BACKGROUND_COLOR}
            ),
            lg=3, md=4, xs=12, style={'minWidth': 0}
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    dcc.Link(
                        html.Img(src='/assets/icons/config.png', className="dashboard-header-icon"),
                        href="/admin",
                        id="admin-page-link",
                        className="dashboard-header-link",
                    ),
                ), className="h-100", style={'backgroundColor': CARD_BACKGROUND_COLOR}
            ),
            lg=2, md=2, xs=12,
            className="d-flex align-items-stretch"
        ),
    ], className="g-3 mb-3")