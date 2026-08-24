"""Distinguishes where a given parameter's value actually came from.

Not wired into the elbow's data flow today (its provenance is already
tracked at the whole-dataset level via core/library/provenance.py). This
enum exists because it will matter per-field once supports are modeled:
a support's pipe size is USER_INPUT, its bolt diameter might be a
DATABASE_VALUE from a manufacturer table, its profile a RULE_DERIVED
value from a sizing rule, and a hole position GEOMETRY_DERIVED from the
3D model — four different trust levels that a single "where did this
dataset come from" provenance record cannot express by itself.

Illustrative mapping for the current elbow (documentation only, not
enforced in code yet):

    DN / PN / angle selection      -> USER_INPUT
    OD, espesor, ID, R, Le, Z      -> DATABASE_VALUE   (Modo A, from BD_Codos/BD_PN)
    Z (Modo B, sin definir manual) -> RULE_DERIVED      (Z = Le + R*tan(angle/2))
    Segment axis/cut-plane points  -> GEOMETRY_DERIVED
    "Configuracion" text           -> SOURCE_DOCUMENT
"""

from __future__ import annotations

from enum import Enum


class ParameterOrigin(str, Enum):
    USER_INPUT = "USER_INPUT"
    DATABASE_VALUE = "DATABASE_VALUE"
    RULE_DERIVED = "RULE_DERIVED"
    GEOMETRY_DERIVED = "GEOMETRY_DERIVED"
    SOURCE_DOCUMENT = "SOURCE_DOCUMENT"
