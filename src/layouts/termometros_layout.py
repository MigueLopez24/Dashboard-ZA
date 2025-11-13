from ..components.termometros_module import crear_layout_termometros

def create_termometros_layout():
    """
    Layout para termómetros (datos simulados por ahora).
    """
    simulated = [
        {'nombre_edificio': 'Site A', 'temp': 22.4, 'status': 'ok'},
        {'nombre_edificio': 'Site B', 'temp': 22, 'status': 'ok'},
        {'nombre_edificio': 'Site C', 'temp': 22.6, 'status': 'ok'},
    ]
    ok_count = sum(1 for s in simulated if s['status'] == 'ok')
    total = len(simulated)
    layout = crear_layout_termometros(simulated, ok_count, total)
    return {"layout": layout, "updates": []}
