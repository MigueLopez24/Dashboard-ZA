# src/layouts/servidores_layout.py

from ..models.network_monitoring import monitorear_dispositivos_ping
from ..components.server_module import crear_layout_servidores

def create_servidores_layout():
    """
    Orquesta el monitoreo de Servidores y crea el layout.
    """
    resultados_monitoreo = monitorear_dispositivos_ping('Servidor', agrupar_por_edificio=False)

    if "error" in resultados_monitoreo:
        return resultados_monitoreo

    # Añadimos el id_dispositivo a cada item para pasarlo al layout (necesario para el modal)
    updates = resultados_monitoreo['updates']
    for ip, data in resultados_monitoreo['items'].items():
        data['id_dispositivo'] = next((d['id_dispositivo'] for d in updates if d['ip'] == ip), None)

    # Crea el layout llamando a la capa de componentes
    layout = crear_layout_servidores(
        resultados_ordenados=resultados_monitoreo['items'],
        total_servidores_activos=resultados_monitoreo['total_activos'],
        total_servidores=resultados_monitoreo['total_dispositivos']
    )
    
    return {
        "layout": layout,
        "updates": resultados_monitoreo.get('updates', [])
    }