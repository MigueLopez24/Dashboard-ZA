# src/components/card_header.py

from dash import html

def crear_header_modulo(titulo, icono_src, contador=None, color_contador='#007bff'):
    """
    Crea el contenido para un dbc.CardHeader de forma reutilizable.
    """
    header_title = html.Div([
        html.Img(src=icono_src, className="header-icon"),
        html.Span(titulo, className="header-title")
    ], className="d-flex align-items-center")

    if contador is not None:
        header_counter = html.Div(
            f"{contador}",
            className="header-counter d-flex justify-content-center align-items-center rounded-pill px-3 py-1",
            style={
                'backgroundColor': color_contador
            }
        )
        return html.Div([header_title, header_counter], className="d-flex justify-content-between align-items-center w-100")

    return header_title