from dash import html
import dash_bootstrap_components as dbc
from ..components.card_header import crear_header_modulo

icon_map = {
    'cold': '/assets/icons/cold.png',
    'ambient': '/assets/icons/ambient.png',
    'hot': '/assets/icons/hot.png',
    'error': '/assets/icons/error.png',
}

# Gradient/background per category
gradient_map = {
    'cold': 'linear-gradient(to right, #0ea5e9, #0284c7)',      
    'ambient': 'linear-gradient(to right, #facc15, #f59e0b)',   
    'hot': 'linear-gradient(to right, #fb923c, #f97316)',       
    'error': 'linear-gradient(to right, #dc3545, #bd2130)',     
    'unknown': 'linear-gradient(to right, #6c757d, #545b62)',
}

def _category_from_temp_and_status(temp_value, status_flag):
    
    if status_flag == 'error':
        return 'error'
    try:
        t = float(temp_value)
    except Exception:
        return 'unknown'
    if t <= 24:
        return 'cold'
    if t > 24 and t <= 25:
        return 'ambient'
    if t > 25:
        return 'hot'
    return 'unknown'

def crear_layout_termometros(lista_termometros, ok_count, total_termometros):
    
    header = crear_header_modulo("Temperaturas SITES", '/assets/icons/termometro.png', f"{ok_count}/{total_termometros}")

    lista_sorted = sorted(lista_termometros, key=lambda x: x.get('nombre_edificio', ''))

    term_cards = []
    for t in lista_sorted:
        edificio = t.get('nombre_edificio', 'Desconocido')
        temp = t.get('temp', 'N/A')
        status_flag = t.get('status', None)

        category = _category_from_temp_and_status(temp, status_flag)
        gradient_style = gradient_map.get(category, gradient_map['unknown'])
        icon_src = icon_map.get(category, icon_map['error'])

        card = dbc.Col(
            dbc.Card(
                html.Div(
                    [
                        html.P(f"{temp}°C", className="mb-0 text-center checador-hora"),
                        html.P(f"{edificio}", className="mb-0 fw-bold text-center checador-edificio"),
                        html.Img(src=icon_src, className="termometro-icon", style={'marginTop': '6px'}),
                    ],
                    className="d-flex flex-column align-items-center justify-content-center checador-card"
                ),
                className="border-0 shadow-sm h-100",
                style={'background': gradient_style, 'padding': '1px', 'borderRadius': '6px', 'minHeight': '90px'}
            ),
            lg=4, md=6, xs=12, className="my-1"
        )
        term_cards.append(card)

    body = html.Div([
        dbc.Row(term_cards, className="g-1 justify-content-center p-1")
    ], className="p-1")

    return {"header": header, "body": body}
