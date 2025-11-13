# src/components/server_module.py

from dash import html
import dash_bootstrap_components as dbc
from ..components.card_header import crear_header_modulo
from ..models.monitoring_logic import ip_to_int_tuple

def crear_layout_servidores(resultados_ordenados, total_servidores_activos, total_servidores):
    """
    Crea el layout de las tarjetas de servidores para el dashboard.
    """
    header_layout = crear_header_modulo("SERVIDORES", '/assets/icons/servidor.png', f"{total_servidores_activos}/{total_servidores}")
    
    servidores_layout = []
    # Ordenamos por IP numérica usando la función del modelo
    for direccion, data in sorted(resultados_ordenados.items(), key=lambda item: ip_to_int_tuple(item[0])):
        estado_final = data['estado']
        id_dispositivo = data.get('id_dispositivo')
        
        # ... [Lógica de iconos de estado] ...
        if estado_final == "Activo": status_icon_src = '/assets/icons/check.png'
        elif estado_final == "Inactivo": status_icon_src = '/assets/icons/circle_gray.png'
        elif estado_final == "Advertencia": status_icon_src = '/assets/icons/warning.png'
        else: status_icon_src = '/assets/icons/error.png'
        
        ip_last_digit = direccion.split('.')[-1] if direccion else "N/A"
        
        card_servidor = dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div(
                            html.Img(src='/assets/icons/servidor_icono.png', className="img-fluid server-icon"),
                            id={'type': 'abrir-modal-servidor', 'index': id_dispositivo},
                            n_clicks=0,
                            style={'cursor': 'pointer'},
                            title=f"Editar credenciales de {direccion}"
                        ),
                        html.P(ip_last_digit, className="text-center fw-bold mb-1 server-ip-label"),
                        html.Img(src=status_icon_src, alt=estado_final, className="server-status-icon")
                    ], className="d-flex flex-column align-items-center justify-content-center p-2"
                ), className="bg-dark border-0 shadow-sm h-100"
            ),
            className="my-2"
        )
        
        servidores_layout.append(card_servidor)
        
    body_content = dbc.Row(servidores_layout, className="g-2 p-2", justify="center")
    
    return {"header": header_layout, "body": body_content}

# --- Agrega este fragmento para el modal de edición de credenciales ---
from dash import dcc, Input, Output, State, callback, html as dhtml

def crear_modal_editar_servidor(nombre, usuario, contrasena):
    """
    Devuelve el contenido del modal para editar credenciales de servidor.
    Incluye opción para mostrar/ocultar la contraseña.
    """
    return html.Div([
        dbc.Row([
            dbc.Label("Usuario", width=2, className="text-dark"),
            dbc.Col(dbc.Input(type="text", id="servidor-modal-usuario-input", value=usuario or "", autoComplete="username"), width=10)
        ], className="mb-3"),
        dbc.Row([
            dbc.Label("Contraseña", width=2, className="text-dark"),
            dbc.Col([
                dbc.Input(type="password", id="servidor-modal-contrasena-input", value=contrasena or "", autoComplete="current-password"),
                dbc.Checkbox(id="servidor-modal-toggle-password", className="ms-2", style={"marginTop": "0.5rem"}),
                html.Label("Mostrar contraseña", htmlFor="servidor-modal-toggle-password", className="ms-2", style={"fontSize": "0.95rem"})
            ], width=10, className="d-flex align-items-center")
        ], className="mb-3"),
    ])

# --- Callback para mostrar/ocultar contraseña (agrega esto en tu archivo de callbacks principal) ---
from dash import Output, Input, callback

@callback(
    Output("servidor-modal-contrasena-input", "type"),
    Input("servidor-modal-toggle-password", "value"),
    prevent_initial_call=True
)
def toggle_password_visibility(show):
    return "text" if show else "password"