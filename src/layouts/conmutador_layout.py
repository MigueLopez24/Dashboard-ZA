# src/layouts/conmutador_layout.py

from ..models.special_devices_logic import monitorear_conmutador
from ..components.conmutador_module import crear_layout_conmutador

def create_conmutador_layout():
    """
    Orquesta el monitoreo del Conmutador y crea el layout.
    """
    resultados = monitorear_conmutador()
    if "error" in resultados:
        return resultados
    estado = resultados.get('layout', {}).get('estado', resultados.get('estado', 'Desconocido'))
    layout_conmutador = crear_layout_conmutador(estado)
    return {"layout": {"body": layout_conmutador}, "updates": resultados.get('updates', [])}