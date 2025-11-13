# src/components/conmutador_module.py

from dash import html

color_map = {
    'Activo': '#28a745',
    'Inactivo': '#6c757d',
    'Advertencia': '#ffc107',
    'Error': '#dc3545',
}

def crear_layout_conmutador(estado):
    """
    Crea el layout específico para el indicador de estado del Conmutador.
    """
    color = color_map.get(estado, '#dc3545')
    
    return html.Div(
        [
            html.Img(src='/assets/icons/conmutador.png', className="conmutador-icon-small"),
            html.Div(
                className="conmutador-bar-small",
                style={
                    'backgroundColor': color
                }
            )
        ],
        className="d-flex align-items-center justify-content-between mb-1 p-1 rounded conmutador-card-bg"
    )