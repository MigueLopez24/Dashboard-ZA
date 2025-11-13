# src/components/contpaqi_module.py

from dash import html, dcc
import dash_bootstrap_components as dbc
from ..components.card_header import crear_header_modulo

def crear_layout_contpaqi(resultados_servicios, total_activos, total_servicios):
    """
    Crea el layout de las tarjetas de servicios de ContpaQi para el dashboard.
    """
    header_layout = crear_header_modulo("SERVICIOS CONTPAQI", '/assets/icons/contpaqi.png', f"{total_activos}/{total_servicios}")
    
    servicios_cards = []

    # Mapa para asignar un icono a cada tipo de servicio
    service_icon_map = {
        'Contabilidad': '/assets/icons/contpaqi_contabilidad.png',
        'Nóminas': '/assets/icons/contpaqi_nominas.png'
    }
    default_icon = '/assets/icons/contpaqi.png'

    for idx, servicio in enumerate(sorted(resultados_servicios, key=lambda x: x['nombre'])):
        if 'id_servicio' not in servicio or servicio['id_servicio'] is None:
            continue

        estado_final = servicio['estado']
        
        # Asignar icono de estado
        if estado_final == "Activo":
            status_icon_src = '/assets/icons/check.png'
        elif estado_final == "Inactivo":
            status_icon_src = '/assets/icons/warning.png' 
        else: # Error
            status_icon_src = '/assets/icons/error.png'

        # Asignar icono de servicio
        service_type_icon = default_icon
        for key, icon in service_icon_map.items():
            if key in servicio['nombre']:
                service_type_icon = icon
                break

        nombre_corto = servicio['nombre'].replace("SQL Server para ", "").replace("Servicio de ", "")

        # Tarjeta con ícono clickeable
        card_servicio = dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div(
                            html.Img(
                                src=service_type_icon,
                                className="img-fluid contpaqi-service-icon"
                            ),
                            id={'type': 'abrir-modal-contpaqi', 'index': servicio['id_servicio']},
                            n_clicks=0,
                            className="mb-2",
                            style={'cursor': 'pointer'},
                            title=f"Editar {servicio['nombre']}"
                        ),
                        html.P(nombre_corto, className="text-center fw-bold contpaqi-service-title"),
                        html.Img(src=status_icon_src, alt=estado_final, className="contpaqi-status-icon")
                    ],
                    className="d-flex flex-column align-items-center justify-content-between p-3 h-100" 
                ),
                className="bg-dark border-0 shadow-sm h-100"
            ),
            className="my-2",
            lg=4, md=6, xs=6
        )
        servicios_cards.append(card_servicio)

    body_content = html.Div([
        dbc.Row(servicios_cards, className="g-2 p-2 align-items-center", justify="center"),
        # Los modales y stores se definen en el layout principal para evitar duplicados
    ])

    return {"header": header_layout, "body": body_content}
