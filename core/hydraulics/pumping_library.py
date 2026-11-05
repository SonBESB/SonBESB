"""Libreria de casos de bombeo guardados — persistencia real en Supabase.

Diseno decidido con el usuario:
- Proyecto Supabase DEDICADO a BESB Piping (no el de finanzas personales
  que ya existia en la misma cuenta) — tabla `pumping_cases`.
- Sin login: la "privacidad" es por posesion de un link personal
  (?owner=<uuid> en la URL), igual que un documento "cualquiera con el
  link". Row Level Security esta activo pero su politica permite
  cualquier operacion a la key anonima — no puede verificar quien es
  el dueno real sin autenticacion, asi que la proteccion real es que
  el UUID es impredecible, no una regla de acceso en la base de datos.
  Esto se declara explicitamente en la UI, no se presenta como
  seguridad real.

Limitacion deliberada: esta libreria SOLO guarda y permite descargar
de nuevo el JSON de un caso pasado. No reconstruye automaticamente los
widgets del formulario (tramos, catalogos, escenarios, accesorios) a
partir de un caso guardado — el formulario tiene demasiadas claves de
estado interdependientes (seleccion de catalogo por tramo y SDR,
cantidad de cada accesorio por tramo, escenarios VDF, golpe de ariete
por material) para reconstruirlas con seguridad sin arriesgar una
restauracion silenciosamente incorrecta. Mejor no reconstruir el
formulario que reconstruirlo mal.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import requests
import streamlit as st

_REQUEST_TIMEOUT_S = 8


@dataclass(frozen=True)
class LibraryConfig:
    url: str
    api_key: str


def get_library_config() -> LibraryConfig | None:
    """Lee SUPABASE_URL / SUPABASE_ANON_KEY de st.secrets.

    Nunca lanza: si faltan credenciales, la libreria queda deshabilitada
    y quien llame debe mostrar un aviso, no fallar la app entera.
    """
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
    except Exception:
        return None
    if not url or not key:
        return None
    return LibraryConfig(url=url.rstrip("/"), api_key=key)


def get_owner_key() -> str:
    """Identificador del 'dueno' de la libreria: un UUID en la URL.

    Si la URL no trae ?owner=..., se genera uno nuevo y se escribe en
    los query params para que el usuario pueda guardar ese link.
    """
    params = st.query_params
    owner = params.get("owner")
    if owner:
        return owner
    new_owner = str(uuid.uuid4())
    st.query_params["owner"] = new_owner
    return new_owner


def _headers(config: LibraryConfig, *, prefer: str | None = None) -> dict:
    headers = {
        "apikey": config.api_key,
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def save_case(
    owner_key: str,
    project_name: str,
    case: dict,
    q_l_s: float | None,
    h_m: float | None,
    p_elec_kw: float | None,
) -> tuple[bool, str]:
    """Guarda un caso. Devuelve (ok, mensaje) — nunca lanza hacia la UI."""
    config = get_library_config()
    if config is None:
        return False, "Libreria no configurada (faltan credenciales de Supabase)."
    payload = {
        "owner_key": owner_key,
        "project_name": project_name or "Mi sistema de bombeo",
        "case_json": case,
        "q_l_s": q_l_s,
        "h_m": h_m,
        "p_elec_kw": p_elec_kw,
    }
    try:
        resp = requests.post(
            f"{config.url}/rest/v1/pumping_cases",
            headers=_headers(config, prefer="return=minimal"),
            json=payload,
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        return False, f"No se pudo conectar con la libreria: {exc}"
    if resp.status_code not in (200, 201):
        return False, f"La libreria rechazo el guardado (HTTP {resp.status_code}): {resp.text[:300]}"
    return True, "Caso guardado."


def list_cases(owner_key: str) -> tuple[list[dict], str | None]:
    """Devuelve (casos, error). casos=[] y error=None si la libreria
    esta deshabilitada o simplemente no hay casos guardados todavia."""
    config = get_library_config()
    if config is None:
        return [], None
    try:
        resp = requests.get(
            f"{config.url}/rest/v1/pumping_cases",
            headers=_headers(config),
            params={
                "owner_key": f"eq.{owner_key}",
                "order": "created_at.desc",
                "select": "id,project_name,created_at,q_l_s,h_m,p_elec_kw,case_json",
                "limit": "50",
            },
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        return [], f"No se pudo conectar con la libreria: {exc}"
    if resp.status_code != 200:
        return [], f"La libreria no respondio correctamente (HTTP {resp.status_code})."
    return resp.json(), None


def delete_case(owner_key: str, case_id: str) -> tuple[bool, str]:
    config = get_library_config()
    if config is None:
        return False, "Libreria no configurada."
    try:
        resp = requests.delete(
            f"{config.url}/rest/v1/pumping_cases",
            headers=_headers(config),
            params={"id": f"eq.{case_id}", "owner_key": f"eq.{owner_key}"},
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        return False, f"No se pudo conectar con la libreria: {exc}"
    if resp.status_code not in (200, 204):
        return False, f"No se pudo eliminar (HTTP {resp.status_code})."
    return True, "Caso eliminado."
