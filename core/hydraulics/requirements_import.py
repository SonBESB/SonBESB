"""Importador de una "tabla de requisitos" (CSV parametro,valor) hacia las
claves de session_state de la calculadora de bombeo.

Alcance deliberadamente acotado: solo rellena campos INDEPENDIENTES entre si
(fluido, desnivel, presiones de borde, un tramo con geometria manual y % de
accesorios, caudal de diseno). No reconstruye accesorios detallados por
pieza, catalogo HDPE/PEXGOL, curva de bomba ni escenarios VDF — esas claves
de estado son interdependientes y reconstruirlas mal es peor que no
reconstruirlas (misma razon por la que la libreria de casos guardados
tampoco lo hace, ver docs/HYDRAULICS_PUMP_OPERATING_POINT.md).

No requiere pandas: el formato soportado es CSV simple de dos columnas
(parametro, valor), igual al que ya usa el usuario al compartir tablas de
requisitos en el chat.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata

from core.hydraulics.pressure_rating import PN_BAR_TABLE

_UNIT_WORDS = [
    "m.c.a.", "m.c.a", "mca", "bar", "l/min", "l/s", "m3/h", "m³/h", "mm",
    "°c", "c", "m/s", "m", "%",
]


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_key(text: str) -> str:
    text = _strip_accents(text).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


def parse_number_es(raw: str) -> float | None:
    """Extrae un numero de un texto que puede traer unidades, un signo "="
    con una conversion al lado, o separador decimal "," (convencion local).

    Devuelve None si no se encuentra ningun numero interpretable. No intenta
    adivinar separadores de miles ambiguos mas alla de la regla descrita en
    el modulo; para esos casos, usar un valor sin ambiguedad en el CSV.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if "=" in text:
        text = text.rsplit("=", 1)[-1].strip()
    lowered = text.lower()
    for unit in _UNIT_WORDS:
        lowered = lowered.replace(unit, " ")
    match = re.search(r"[+-]?\d[\d.,]*", lowered)
    if not match:
        return None
    token = match.group(0)
    if "," in token and "." in token:
        token = token.replace(".", "").replace(",", ".")
    elif "," in token:
        token = token.replace(",", ".")
    try:
        return float(token)
    except ValueError:
        return None


def parse_requirements_csv(content: str) -> dict[str, str]:
    """Lee un CSV de dos columnas (parametro, valor) a un dict normalizado.

    Tolera encabezados en cualquier orden/mayuscula ("Parametro","Valor",
    "parametro","valor", etc.) y los omite si no son reconocibles como
    encabezado (en ese caso trata la primera fila como datos).
    """
    reader = list(csv.reader(io.StringIO(content)))
    if not reader:
        return {}
    header = [normalize_key(h) for h in reader[0]]
    rows = reader[1:] if header[:2] in (["parametro", "valor"], ["parametro", "value"]) else reader
    result: dict[str, str] = {}
    for row in rows:
        if len(row) < 2:
            continue
        key = normalize_key(row[0])
        if not key:
            continue
        result[key] = row[1].strip()
    return result


# alias reconocidos -> clave canonica usada abajo
_KEY_ALIASES = {
    "proyecto": "proyecto",
    "nombre_del_proyecto": "proyecto",
    "fluido": "fluido",
    "liquido": "fluido",
    "temperatura": "temperatura_c",
    "temperatura_c": "temperatura_c",
    "densidad": "densidad_kg_m3",
    "densidad_kg_m3": "densidad_kg_m3",
    "viscosidad": "viscosidad_pa_s",
    "viscosidad_pa_s": "viscosidad_pa_s",
    "desnivel_geometrico": "desnivel_geometrico_m",
    "desnivel_geometrico_m": "desnivel_geometrico_m",
    "desnivel": "desnivel_geometrico_m",
    "presion_disponible_en_tie_in": "presion_disponible_bar",
    "presion_disponible_tie_in": "presion_disponible_bar",
    "presion_disponible_bar": "presion_disponible_bar",
    "presion_disponible": "presion_disponible_bar",
    "presion_requerida_en_destino": "presion_requerida_bar",
    "presion_requerida_destino": "presion_requerida_bar",
    "presion_requerida_bar": "presion_requerida_bar",
    "presion_requerida": "presion_requerida_bar",
    "diametro_interior": "diametro_interior_mm",
    "diametro_interior_mm": "diametro_interior_mm",
    "rugosidad_absoluta": "rugosidad_mm",
    "rugosidad_absoluta_mm": "rugosidad_mm",
    "rugosidad": "rugosidad_mm",
    "rugosidad_mm": "rugosidad_mm",
    "longitud_de_tuberia": "longitud_m",
    "longitud": "longitud_m",
    "longitud_m": "longitud_m",
    "clase_de_presion": "clase_pn",
    "clase_pn": "clase_pn",
    "pn": "clase_pn",
    "perdidas_singulares": "pct_perdidas_singulares",
    "pct_perdidas_singulares": "pct_perdidas_singulares",
    "porcentaje_perdidas_singulares": "pct_perdidas_singulares",
    "caudal_de_diseno": "caudal_diseno_l_s",
    "caudal_diseno_l_s": "caudal_diseno_l_s",
    "caudal_diseno": "caudal_diseno_l_s",
}

_FLUID_OPTIONS = ["Agua", "Agua salina", "Agua con glicol", "Aceite", "Diésel", "Etanol", "Glicerina", "Otro líquido"]


def build_session_state_updates(parsed: dict[str, str], key_prefix: str = "pump") -> tuple[dict[str, object], list[str], list[str]]:
    """Traduce el dict normalizado del CSV a actualizaciones de session_state.

    Devuelve (updates, aplicados, ignorados): `aplicados` e `ignorados` son
    listas de texto para mostrarle al usuario exactamente que se lleno y que
    quedo pendiente de ingresar a mano.
    """
    updates: dict[str, object] = {}
    applied: list[str] = []
    ignored: list[str] = []

    canonical: dict[str, str] = {}
    for raw_key, value in parsed.items():
        target = _KEY_ALIASES.get(raw_key)
        if target is None:
            ignored.append(f"{raw_key.replace('_', ' ')} = {value} (parámetro no reconocido o fuera del alcance de esta importación)")
            continue
        canonical[target] = value

    if "proyecto" in canonical:
        updates[f"{key_prefix}_project_name"] = canonical["proyecto"]
        applied.append(f"Proyecto = {canonical['proyecto']}")

    if "fluido" in canonical:
        label = canonical["fluido"].strip()
        match = next((opt for opt in _FLUID_OPTIONS if opt.lower() == label.lower()), None)
        if match:
            updates[f"{key_prefix}_liquid"] = match
            applied.append(f"Fluido = {match}")
        else:
            ignored.append(f"Fluido = {label} (no coincide con una opcion de la lista; déjalo en 'Otro líquido' manualmente)")

    temp = parse_number_es(canonical.get("temperatura_c"))
    if temp is not None:
        updates[f"{key_prefix}_fluid_temp"] = temp
        applied.append(f"Temperatura = {temp:g} °C")

    desnivel = parse_number_es(canonical.get("desnivel_geometrico_m"))
    if desnivel is not None:
        updates[f"{key_prefix}_static_head"] = desnivel
        applied.append(f"Desnivel geométrico = {desnivel:g} m")

    p_disp = parse_number_es(canonical.get("presion_disponible_bar"))
    if p_disp is not None:
        updates[f"{key_prefix}_p_tiein_bar"] = p_disp
        applied.append(f"Presión disponible en el origen = {p_disp:g} bar")

    p_req = parse_number_es(canonical.get("presion_requerida_bar"))
    if p_req is not None:
        updates[f"{key_prefix}_p_destino_bar"] = p_req
        applied.append(f"Presión requerida en el destino = {p_req:g} bar")

    # Tramo 1 (geometria manual). Mas tramos, o catalogo/accesorios
    # detallados, se ingresan a mano por diseño (ver docstring del modulo).
    has_segment_data = any(k in canonical for k in ("diametro_interior_mm", "rugosidad_mm", "longitud_m", "clase_pn"))
    if has_segment_data:
        updates[f"{key_prefix}_source_0"] = "Manual"
        di = parse_number_es(canonical.get("diametro_interior_mm"))
        if di is not None:
            updates[f"{key_prefix}_di_0"] = di
            applied.append(f"Diámetro interior (Tramo 1) = {di:g} mm")
        rough = parse_number_es(canonical.get("rugosidad_mm"))
        if rough is not None:
            updates[f"{key_prefix}_rough_0"] = rough
            applied.append(f"Rugosidad absoluta (Tramo 1) = {rough:g} mm")
        length = parse_number_es(canonical.get("longitud_m"))
        if length is not None:
            updates[f"{key_prefix}_len_0"] = length
            applied.append(f"Longitud (Tramo 1) = {length:g} m")
        pn_label = canonical.get("clase_pn", "").strip().upper().replace(" ", "")
        if pn_label:
            match_pn = next((k for k in PN_BAR_TABLE if k.upper() == pn_label), None)
            if match_pn:
                updates[f"{key_prefix}_pn_0"] = match_pn
                applied.append(f"Clase de presión (Tramo 1) = {match_pn}")
            else:
                ignored.append(f"Clase de presión = {canonical['clase_pn']} (no coincide con {', '.join(PN_BAR_TABLE)}; selecciónala a mano)")

    pct = parse_number_es(canonical.get("pct_perdidas_singulares"))
    if pct is not None:
        updates[f"{key_prefix}_minor_mode_0"] = "Aún no sé los accesorios — estimar como % de la fricción"
        updates[f"{key_prefix}_minor_pct_0"] = pct
        applied.append(f"Pérdidas singulares (Tramo 1) = {pct:g}% de la fricción")

    caudal = parse_number_es(canonical.get("caudal_diseno_l_s"))
    if caudal is not None:
        updates[f"{key_prefix}_no_pump_mode"] = True
        updates[f"{key_prefix}_design_flow_l_s"] = caudal
        applied.append(f"Caudal de diseño = {caudal:g} L/s (activa el modo 'sin bomba')")

    return updates, applied, ignored
