# src/layouts/sitios_web_layout.py

from dash import html
import dash_bootstrap_components as dbc
from ..models.special_devices_logic import monitorear_sitios_web
from ..components.card_header import crear_header_modulo

def create_sitios_web_layout():
    """
    Orquesta el monitoreo de Sitios Web y crea el layout.
    """
    # 1. Llama a la capa de lógica/monitoreo
    resultados = monitorear_sitios_web()

    if "error" in resultados:
        return resultados 

    data = resultados['layout']
    
    resultados_layout = data['resultados']
    sitios_activos = data['activos']
    total_sitios = data['total']

    sitios_layout = []
    for i, res in enumerate(resultados_layout):
        estado = res['estado']
        direccion = res['direccion']
        
        badge_class = "bg-success" if estado == "Activo" else "bg-danger"
        link_url = direccion if direccion.startswith(('http://', 'https://')) else f"http://{direccion}"
        link_id = f"sitio-web-link-{i}"

        sitio_card = html.Div(
            [
                html.Div(
                    [
                        html.Img(src='/assets/icons/link.png', className="sitio-web-link-icon"),
                        html.A(
                            direccion, id=link_id, href=link_url, target="_blank",
                            className="text-white mb-0 sitio-web-link",
                        ),
                        dbc.Tooltip(direccion, target=link_id, placement='top')
                    ],
                    className="d-flex align-items-center sitio-web-link-row"
                ),
                html.Span(estado, className=f"badge rounded-pill {badge_class}"),
            ],
            className="d-flex align-items-center justify-content-between mb-2 p-2 rounded sitio-web-card"
        )
        sitios_layout.append(sitio_card)
    
    # Crea el layout final
    header = crear_header_modulo("SITIOS WEB", '/assets/icons/sitio_web.png', f"{sitios_activos}/{total_sitios}")
    body = html.Div(sitios_layout, className="p-1")

    return {"layout": {"header": header, "body": body}, "updates": resultados['updates']}