# src/components/device_module.py
from dash import html
from ..components.card_header import crear_header_modulo
from .device_group import crear_layout_dispositivos_por_edificio

def crear_layout_modulo_dispositivos(titulo, icono, total_activos, total_dispositivos, datos_por_edificio=None, children=None, show_tooltip=True):
    """
    Crea el layout general para módulos de dispositivos (PCs, Teléfonos, etc).
    """
    contenido = children if children is not None else crear_layout_dispositivos_por_edificio(datos_por_edificio, show_tooltip)

    header_layout = crear_header_modulo(
        titulo, icono, f"{total_activos}/{total_dispositivos}"
    )
    
    # El layout de los módulos de ContpaQi y Sitios Web es diferente, así que lo manejamos.
    if titulo in ["SERVICIOS CONTPAQI", "SITIOS WEB"]:
        return {"header": header_layout, "body": contenido}

    return {"header": header_layout, "body": html.Div(contenido, className="text-white")}