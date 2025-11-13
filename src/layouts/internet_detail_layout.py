# src/layouts/internet_detail_layout.py

from dash import html, dcc
import dash_bootstrap_components as dbc
from ..components.dashboard_header_row import create_dashboard_header_row
from src.config import OVERSCAN_PADDING

def create_internet_detail_layout():
    """
    Crea y retorna el layout para la página de detalles de Internet.
    """
    return dbc.Container([
         # Fila 1: Título, Logo y Relojes 
         create_dashboard_header_row(),

        # Fila con las gráficas de velocidad, historial y storyline
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Velocidad Actual"),
                dbc.CardBody(id='internet-detail-speed-content', className="d-flex justify-content-center align-items-center", style={'minHeight': '110px'})
            ], className="bg-dark text-white h-100"), lg=3, md=12),
            
            dbc.Col(dbc.Card([
                dbc.CardHeader("Historial de Velocidad (Última Hora)"),
                dbc.CardBody(
                    dcc.Graph(
                        id='internet-detail-history-graph',
                        config={'displayModeBar': False, 'responsive': True},
                        className='main-graph-history',
                        style={'width': '100%', 'height': '100%', 'minHeight': '140px'}
                    ),
                    className="p-0 h-100"
                )
            ], className="bg-dark text-white h-100"), lg=5, md=12),
            
            dbc.Col(dbc.Card([
                dbc.CardHeader("Storyline de Sitios Web"),
                dbc.CardBody(
                    dcc.Graph(
                        id='internet-detail-storyline-graph',
                        config={'displayModeBar': False, 'responsive': True},
                        className='main-graph-storyline',
                        style={'width': '100%', 'height': '100%', 'minHeight': '140px'}
                    ),
                    className="p-0 h-100"
                )
            ], className="bg-dark text-white h-100"), lg=4, md=12, className="h-100"),
        ], className="g-2 mb-2 mx-0"),  # Menos gap y sin margen horizontal

        # Fila con la tabla de usuarios VPN
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Usuarios Conectados por VPN"),
                dbc.CardBody(id='internet-detail-vpn-table', className="internet-detail-vpn-table")
            ], className="bg-dark text-white"), width=12)
        ], className="g-2 mb-2 mx-0"),  # Menos gap y sin margen horizontal

    ], fluid=True, className="internet-detail-layout", style=OVERSCAN_PADDING)