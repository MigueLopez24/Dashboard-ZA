from ..models.special_devices_logic import monitorear_dvr
from ..components.device_module import crear_layout_modulo_dispositivos
from ..components.device_group import crear_layout_camaras_por_edificio

def create_dvr_layout():
    """
    Orquesta el monitoreo de DVRs, procesa los resultados y crea el layout.
    """
    # 1. Llama a la capa de lógica/monitoreo
    resultados = monitorear_dvr()

    if "error" in resultados:
        return resultados

    data = resultados['layout']
    
    # 2. Llama a la capa de componentes para generar el HTML, usando el componente específico para cámaras
    layout = crear_layout_modulo_dispositivos(
        titulo=data['titulo'],
        icono=data['icono'],
        total_activos=data['total_activos'],
        total_dispositivos=data['total_dispositivos'],
        # Pasamos el layout de cámaras ya renderizado por su componente específico
        children=crear_layout_camaras_por_edificio(data['datos_por_edificio'], show_tooltip=True)
    )
    
    # 3. Devuelve el resultado final (Layout + Updates para la BD)
    return {"layout": layout, "updates": resultados['updates']}