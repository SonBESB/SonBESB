"""Illustrative steady-flow profile, linear elevations and distributed losses."""
from core.hydraulics.system_curve import evaluate_system


def illustrative_profile(segments, flow_m3_s, pump_head_m, static_head_m, density_kg_m3, viscosity_pa_s, inlet_pressure_head_m=0.0):
    """static_head_m aqui es la elevacion geometrica REAL (desnivel destino -
    origen), nunca un "desnivel efectivo" con presion de borde ya sumada:
    esta funcion reparte esa elevacion a lo largo del trazado para dibujar
    el perfil, y mezclar ahi una carga que ya incluye presion produce una
    cota ficticia y presiones negativas espurias.

    inlet_pressure_head_m es la carga (m) de la presion real disponible en
    el origen (p.ej. un tie-in presurizado) antes de cualquier bomba; 0.0
    (default) reproduce el supuesto anterior de deposito abierto. pump_head_m
    es el aporte mecanico real de una bomba, 0.0 si no hay bomba.
    """
    detail = evaluate_system(segments, flow_m3_s, static_head_m, density_kg_m3, viscosity_pa_s)
    length = sum(s.length_m for s in segments)
    rows = []
    x = loss = 0.0
    entry_energy = inlet_pressure_head_m + pump_head_m
    for seg, ev in zip(segments, detail.segment_evaluations):
        velocity_head = ev.velocity_m_s ** 2 / (2 * 9.80665)
        for frac in (0.0, 1.0):
            position = x + frac * seg.length_m
            elevation = static_head_m * position / length
            energy = entry_energy - loss - frac * ev.total_head_loss_m
            piezometric = energy - velocity_head
            rows.append({'tramo': seg.label, 'distancia_m': position, 'cota_m': elevation,
                         'energia_m': energy, 'piezometrica_m': piezometric,
                         'presion_bar': (piezometric-elevation)*density_kg_m3*9.80665/100000})
        x += seg.length_m
        loss += ev.total_head_loss_m
    return rows
