# src/layouts/checadores_layout.py

from ..models.special_devices_logic import monitorear_checadores
from ..components.checadores_module import crear_layout_checadores

def create_checadores_layout():
    """
    Orquesta el monitoreo de Checadores y crea el layout.
    """
    resultados = monitorear_checadores() # Llama a la lógica de monitoreo

    if "error" in resultados:
        return resultados

    data = resultados['layout']
    
    # Crea el layout llamando a la capa de componentes
    layout = crear_layout_checadores(data['datos'], data['ok'], data['total'])
    
    return {"layout": layout, "updates": resultados['updates']}