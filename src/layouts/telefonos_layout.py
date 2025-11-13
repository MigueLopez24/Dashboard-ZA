from ..models.network_monitoring import monitorear_dispositivos_ping
from ..models.monitoring_logic import ip_to_int_tuple
from ..components.device_module import crear_layout_modulo_dispositivos

def create_telefonos_layout():
    """
    Orquesta el monitoreo de Teléfonos, procesa y crea el layout.
    """
    resultados_monitoreo = monitorear_dispositivos_ping('Telefono IP', agrupar_por_edificio=True)

    if "error" in resultados_monitoreo:
        return resultados_monitoreo

    # Procesamiento y ordenamiento de resultados (Lógica de telefonos.py)
    lista_dispositivos = []
    for ip, data in resultados_monitoreo['items'].items():
        nombre_dispositivo = data.get('nombre', ip)
        device_info = {**data, 'ip': ip, 'identifier': nombre_dispositivo}
        lista_dispositivos.append(device_info)

    lista_dispositivos.sort(key=lambda x: (x.get('nombre_edificio', ''), ip_to_int_tuple(x.get('ip', ''))))

    telefonos_por_edificio = {}
    for device in lista_dispositivos:
        nombre_edificio = device['nombre_edificio']
        telefonos_por_edificio.setdefault(nombre_edificio, []).append(device)

    # Crea el layout llamando a la capa de componentes
    layout = crear_layout_modulo_dispositivos(
        titulo="TELÉFONOS ACTIVOS",
        icono='/assets/icons/telefono.png',
        datos_por_edificio=telefonos_por_edificio,
        total_activos=resultados_monitoreo['total_activos'],
        total_dispositivos=resultados_monitoreo['total_dispositivos'],
        show_tooltip=True 
    )

    return {
        "layout": layout,
        "updates": resultados_monitoreo.get('updates', [])
    }