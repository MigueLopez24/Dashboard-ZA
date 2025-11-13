# src/layouts/contpaqi_layout.py

from ..models.special_devices_logic import monitorear_servicios_contpaqi
from ..components.contpaqi_module import crear_layout_contpaqi
import logging

def create_contpaqi_layout():
    """
    Orquesta el monitoreo de Servicios ContpaQi y crea el layout.
    """
    # 1. Llama a la capa de lógica/monitoreo
    resultados = monitorear_servicios_contpaqi()

    if "error" in resultados:
        return resultados # Devuelve el error para que el worker lo maneje

    data = resultados['layout']

    # --- Filtra servicios que no tengan id_servicio ---
    servicios_validos = []
    for servicio in data.get('resultados', []):
        if 'id_servicio' in servicio and servicio['id_servicio'] is not None:
            servicios_validos.append(servicio)
        else:
            logging.warning(f"Servicio sin id_servicio: {servicio}")

    # 2. Llama a la capa de componentes para generar el HTML
    layout = crear_layout_contpaqi(servicios_validos, data['activos'], data['total'])
    
    # 3. Devuelve el resultado final (Layout + Updates para la BD)
    return {"layout": layout, "updates": resultados['updates']}