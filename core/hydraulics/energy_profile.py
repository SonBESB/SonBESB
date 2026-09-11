"""Illustrative steady-flow profile, linear elevations and distributed losses."""
from core.hydraulics.system_curve import evaluate_system


def illustrative_profile(segments, flow_m3_s, pump_head_m, static_head_m, density_kg_m3, viscosity_pa_s):
    detail = evaluate_system(segments, flow_m3_s, static_head_m, density_kg_m3, viscosity_pa_s)
    length = sum(s.length_m for s in segments)
    rows = []
    x = loss = 0.0
    for seg, ev in zip(segments, detail.segment_evaluations):
        velocity_head = ev.velocity_m_s ** 2 / (2 * 9.80665)
        for frac in (0.0, 1.0):
            position = x + frac * seg.length_m
            elevation = static_head_m * position / length
            energy = pump_head_m - loss - frac * ev.total_head_loss_m
            piezometric = energy - velocity_head
            rows.append({'tramo': seg.label, 'distancia_m': position, 'cota_m': elevation,
                         'energia_m': energy, 'piezometrica_m': piezometric,
                         'presion_bar': (piezometric-elevation)*density_kg_m3*9.80665/100000})
        x += seg.length_m
        loss += ev.total_head_loss_m
    return rows
