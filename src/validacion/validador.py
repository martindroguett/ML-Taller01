"""Validación del JSON producido por el LLM.

El LLM no es la fuente de verdad: el código debe verificar el esquema.
"""

from __future__ import annotations

from pathlib import Path


import json


class ValidadorJSON:
    """Comprueba que cada archivo JSON cumpla el contrato de datos."""

    CAMPOS_OBLIGATORIOS = [
        "id_noticia",
        "titulo",
        "fecha_publicacion",
        "fuente",
        "url",
        "resumen",
        "delitos",
        "personas",
        "organizaciones",
        "lugares",
        "objetos",
        "relaciones",
    ]

    CAMPOS_LISTA = [
        "delitos",
        "personas",
        "organizaciones",
        "lugares",
        "objetos",
        "relaciones",
    ]

    def validar(self, ruta: str | Path) -> dict:
        """Lee, parsea y valida un JSON. Lanza ValueError si falta un campo.

        """
        ruta = Path(ruta)

        try:
            data = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Error leyendo/parsing {ruta}: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"El archivo {ruta} no contiene un objeto JSON (dict).")

        faltantes = [campo for campo in self.CAMPOS_OBLIGATORIOS if campo not in data]
        if faltantes:
            raise ValueError(
                f"El archivo {ruta} no contiene los campos obligatorios: {faltantes}"
            )

        for campo in self.CAMPOS_LISTA:
            if not isinstance(data[campo], list):
                raise ValueError(
                    f"El archivo {ruta}: el campo '{campo}' debe ser una lista, "
                    f"llegó {type(data[campo]).__name__}."
                )
        return data
