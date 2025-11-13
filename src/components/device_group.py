# src/components/device_group.py

from dash import html
from ..models.monitoring_logic import ip_to_int_tuple

color_map = {
    'Activo': '#28a745',
    'Inactivo': '#6c757d',
    'Advertencia': '#ffc107',
    'Error': '#dc3545',
}

def crear_layout_dispositivos_por_edificio(dispositivos_por_edificio, show_tooltip=True):
    """
    Crea el layout de barras de estado agrupadas por edificio (para PCs, Teléfonos, DVRs).
    """
    dispositivos_layout = []
    # Aseguramos el ordenamiento de edificios y dispositivos dentro
    for edificio in sorted(dispositivos_por_edificio.keys()):
        device_list = sorted(dispositivos_por_edificio[edificio], 
                             key=lambda d: ip_to_int_tuple(d.get('ip', ''))) # Usa la función del modelo
        
        estado_barra_layout = html.Div(
            [
                html.Div(edificio, className="fw-bold me-2 edificio-label"),
                html.Div(
                    [
                        html.Div(
                            # Lógica correcta: Muestra un ID corto (último octeto de la IP) en la bolita.
                            device.get('ip', '?').split('.')[-1] if '.' in device.get('ip', '') else '?',
                            title=(
                                # Tooltip correcto: Muestra el ID (nombre) y la IP.
                                f"ID: {device.get('identifier', device.get('nombre', 'N/A'))}\n"
                                f"IP Actual: {device.get('ip', 'N/A')}\n"
                                f"Estado: {device.get('estado', 'Desconocido')}"
                            ) if show_tooltip else None,
                            className="device-dot",
                            style={
                                'backgroundColor': color_map.get(device['estado'], '#6c757d')
                            }
                        )
                        for device in device_list
                    ],
                    className="d-flex align-items-center flex-wrap device-bar"
                )
            ],
            className="d-flex align-items-center mb-1"
        )
        dispositivos_layout.append(estado_barra_layout)
    
    return html.Div(dispositivos_layout, className="p-2")

def crear_layout_camaras_por_edificio(dispositivos_por_edificio, show_tooltip=True):
    """
    Crea un layout de barras de estado específico para las cámaras de los DVRs.
    """
    dispositivos_layout = []
    # Aseguramos el ordenamiento de edificios y dispositivos dentro
    for edificio in sorted(dispositivos_por_edificio.keys()):
        # Ordenamos por el identificador del canal, que debería ser numérico
        def sort_key(d):
            identifier = d.get('identifier')
            if isinstance(identifier, str) and identifier.isdigit():
                return int(identifier)
            return 0

        device_list = sorted(dispositivos_por_edificio[edificio], key=sort_key)
        
        estado_barra_layout = html.Div(
            [
                html.Div(edificio, className="fw-bold me-2", style={'width': '65px', 'color': 'white', 'fontSize': '10px'}),
                html.Div(
                    [
                        html.Div(
                            device.get('identifier', '?'),
                            title=(
                                f"Nombre: {device.get('name', 'N/A')}\n"
                                f"Canal: {device.get('identifier', 'N/A')}\n"
                                f"DVR IP: {device.get('ip', 'N/A')}"
                            ) if show_tooltip else None,
                            className="device-dot",
                            style={
                                'backgroundColor': color_map.get(device['estado'], '#6c757d')
                            }
                        )
                        for device in device_list
                    ],
                    className="d-flex align-items-center flex-wrap device-bar"
                )
            ],
            className="d-flex align-items-center mb-1"
        )
        dispositivos_layout.append(estado_barra_layout)
    
    return html.Div(dispositivos_layout, className="p-2")