# src/layouts/pcs_layout.py

import logging
from concurrent.futures import as_completed
from ..models.internet_logic import get_primary_ip
from ..models.monitoring_logic import ping_dispositivo
from ..data.sql_connector import obtener_dispositivos
from ..components.device_module import crear_layout_modulo_dispositivos
from ..utils.concurrency import get_shared_executor as get_executor

def _process_single_pc(pc):
    """
    Función auxiliar para procesar una única PC. Resuelve la IP y luego hace ping.
    Esto permite que el proceso se ejecute de forma concurrente.
    """
    hostname = pc.get('ip') # En la BD, la IP de la PC es su hostname
    ip_resuelta = get_primary_ip(hostname) # Intenta resolver el nombre
    
    if ip_resuelta != hostname:
        ping_exitoso = ping_dispositivo(ip_resuelta)
        pc['estado'] = 'Activo' if ping_exitoso else 'Inactivo'
        # Mantenemos la IP resuelta para el layout, pero usamos 'N/A' si está inactiva
        pc['ip_display'] = ip_resuelta if ping_exitoso else 'N/A'
        pc['ip'] = ip_resuelta # La IP real para referencia interna
    else:
        pc['estado'] = 'Inactivo'
        pc['ip_display'] = 'N/A'
    
    pc['identifier'] = pc.get('nombre', hostname)
    return pc

def create_pcs_layout():
    """
    Orquesta el monitoreo de PCs y construye el layout con los resultados.
    """
    # 1. Obtener la lista de PCs desde la base de datos
    pcs_from_db = obtener_dispositivos('PC', agrupar_por_edificio=True)
    if not pcs_from_db:
        return {"error": "No se encontraron PCs para monitorear."}

    # 2. Procesar todas las PCs en paralelo para determinar su estado real
    lista_dispositivos = []
    updates_to_db = []
    executor = get_executor(max_workers=20)
    future_to_pc = {executor.submit(_process_single_pc, pc): pc for pc in pcs_from_db}
    for future in as_completed(future_to_pc):
        try:
            processed_pc = future.result()
            lista_dispositivos.append(processed_pc)
            # Generar el diccionario para la actualización en BD
            updates_to_db.append({
                'id_dispositivo': processed_pc['id_dispositivo'],
                'estado_final': processed_pc['estado'],
                # El estado anterior no es relevante para PCs ya que no registran fallas
                'estado_anterior': 'Desconocido', 
                'tipo': 'PC'
            })
        except Exception as e:
            pc_original = future_to_pc[future]
            logging.error(f"Error procesando la PC {pc_original.get('nombre')}: {e}")

    # Ordenar la lista de dispositivos alfabéticamente por nombre para una visualización estable
    lista_dispositivos.sort(key=lambda x: x.get('nombre', ''))

    # Calcular el total de activos después del procesamiento
    total_activos = sum(1 for pc in lista_dispositivos if pc['estado'] == 'Activo')

    # 3. Agrupar resultados por edificio para el layout
    pcs_por_edificio = {}
    for device in lista_dispositivos:
        nombre_edificio = device.get('nombre_edificio', 'Sin Edificio')
        if nombre_edificio not in pcs_por_edificio:
            pcs_por_edificio[nombre_edificio] = []
        device_for_layout = device.copy()
        device_for_layout['ip'] = device_for_layout.get('ip_display', 'N/A')
        pcs_por_edificio[nombre_edificio].append(device_for_layout)
    
    # 4. Crea el layout llamando a la capa de componentes
    layout = crear_layout_modulo_dispositivos(
        titulo="PC ENCENDIDAS",
        icono='/assets/icons/pc.png',
        datos_por_edificio=pcs_por_edificio,
        total_activos=total_activos,
        total_dispositivos=len(pcs_from_db),
        show_tooltip=True
    )

    return {
        "layout": layout,
        "updates": updates_to_db 
    }