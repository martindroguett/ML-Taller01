"""Validación del JSON producido por el LLM.

El LLM no es la fuente de verdad: el código debe verificar el esquema.
"""

from __future__ import annotations

from pathlib import Path

from src.excepciones import EtapaPendienteAlumno

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

    def validar(self, ruta: str | Path) -> dict:
        """Lee, parsea y valida un JSON. Debe lanzar ValueError si falta un campo.

        TODO(alumno):
        1. Cargar el archivo con json.loads.
        2. Verificar que existan CAMPOS_OBLIGATORIOS.
        3. Verificar tipos mínimos (listas en delitos, personas, etc.).
        4. Registrar JSON inválidos para Data Understanding.
        """


        json_noticia = json.loads()

        raise EtapaPendienteAlumno(
            modulo="src.validacion.validador.ValidadorJSON.validar",
            pista=(
                "Implemente json.loads y compare las claves del documento "
                f"contra {self.CAMPOS_OBLIGATORIOS}."
            ),
        )
