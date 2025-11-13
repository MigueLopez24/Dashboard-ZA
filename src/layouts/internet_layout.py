# src/layouts/internet_layout.py

from ..models.internet_logic import monitorear_velocidad_internet, all_users
from ..components.internet_module import crear_layout_internet_speed

def create_internet_module_layout():
    """
    Orquesta el monitoreo de Internet y crea el layout del módulo.
    """

    speed_data = monitorear_velocidad_internet()
    user_counts = all_users()
    
    if "error" in speed_data:
        # Devuelve el error de velocidad para que el worker lo maneje
        return {"error": speed_data['error']}

    # Combina los resultados
    live_internet_data = {**speed_data, **user_counts}
    
    # Crea el layout llamando a la capa de componentes
    internet_speed_layout = crear_layout_internet_speed(
        velocidad_descarga=live_internet_data.get('velocidad_descarga', 0),
        velocidad_carga=live_internet_data.get('velocidad_carga', 0),
        ping=live_internet_data.get('ping', 0),
        remotos=live_internet_data.get('remotos', 0),
        empresariales=live_internet_data.get('empresariales', 0),
    )
    
    return {"layout": internet_speed_layout, "data": live_internet_data}