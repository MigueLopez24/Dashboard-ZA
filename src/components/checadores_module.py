# src/components/checadores_module.py

from dash import html
import dash_bootstrap_components as dbc
from ..components.card_header import crear_header_modulo
from ..models.monitoring_logic import ip_to_int_tuple

def crear_layout_checadores(lista_datos_checadores, checadores_ok, total_checadores):
    """
    Crea el layout para la tarjeta de checadores con bordes de estado degradados.
    """
    header = crear_header_modulo("CHECADORES", '/assets/icons/checadores.png', f"{checadores_ok}/{total_checadores}")
    
    # 1. Ordenamiento
    lista_datos_checadores.sort(key=lambda x: (x.get('nombre_edificio', ''), ip_to_int_tuple(x.get('ip', ''))))

    checadores_cards = []
    
    # 2. Mapeo de estados y estilos
    status_map = {
        'ok': {'icon': '/assets/icons/check.png', 'color': 'green'},
        'error': {'icon': '/assets/icons/error.png', 'color': 'red'},
        'warning': {'icon': '/assets/icons/warning.png', 'color': 'orange'}
    }

    gradient_map = {
        'Activo': 'linear-gradient(to right, #28a745, #1e7e34)',
        'Advertencia': 'linear-gradient(to right, #ffc107, #e0a800)',
        'Error': 'linear-gradient(to right, #dc3545, #bd2130)',
        'Inactivo': 'linear-gradient(to right, #6c757d, #545b62)'
    }

    # 3. Construcción del layout
    for data in lista_datos_checadores:
        edificio = data.get('nombre_edificio', 'Desconocido')
        ip = data.get('ip', 'N/A')
        status = data.get('status', 'error')
        hora = data.get('hora_reloj', 'N/A')
        info = status_map.get(status, status_map['error'])
        
        # Lógica para determinar el color final del borde
        final_status_for_color = 'Activo'
        if data.get('estado_ping', 'Error') == 'Error' or status == 'error':
            final_status_for_color = 'Error'
        elif data.get('estado_ping', 'Error') == 'Advertencia' or status == 'warning':
            final_status_for_color = 'Advertencia'
        elif data.get('estado_ping', 'Error') == 'Inactivo':
            final_status_for_color = 'Inactivo'
        
        gradient_style = gradient_map.get(final_status_for_color, gradient_map['Error'])

        checadores_cards.append(
            dbc.Col(
                dbc.Card(
                    html.Div(
                        [
                            html.P(f"{hora}", className="mb-0 text-center checador-hora"),
                            html.P(f"{edificio}", className="mb-0 fw-bold text-center checador-edificio"),
                            html.P(f"IP: {ip.split('.')[-1]}", className="mb-0 text-center checador-ip"),
                            html.Img(src=info['icon'], className="checador-icon"),
                        ],
                        className="d-flex flex-column align-items-center justify-content-center checador-card"
                    ),
                    className="border-0 shadow-sm h-100",
                    style={'background': gradient_style, 'padding': '1px', 'borderRadius': '6px', 'minHeight': '90px'}
                ),
                lg=4, md=6, xs=12,
                className="my-1"
            )
        )
        
    body = html.Div([
        html.Div([
            #html.Img(src='/assets/icons/checadores.png', className="checador-main-icon"),
            dbc.Row(checadores_cards, className="g-1 justify-content-center")
        ], className="p-1")
    ], className="p-1")
    
    return {"header": header, "body": body}