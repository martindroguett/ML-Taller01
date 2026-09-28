"""Contrato de extracción con un LLM.

TODO(alumno): completar ExtractorGemini. El laboratorio NO inventa datos:
solo se extrae información explícita en la noticia, en JSON válido.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.excepciones import EtapaPendienteAlumno
from src.modelos import NoticiaFuente

from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.adquisicion.repositorio import RepositorioNoticias


import json
from google import generativeai as genai

class ExtractorLLM(ABC):
    """Interfaz de cualquier extractor basado en modelo generativo."""

    @abstractmethod
    def construir_prompt(self, noticia: NoticiaFuente) -> str:
        """Arma el prompt con el esquema JSON y el texto de la noticia."""

    @abstractmethod
    def extraer(self, noticia: NoticiaFuente) -> dict:
        """Devuelve un diccionario que cumple el contrato JSON del laboratorio."""


class ExtractorGemini(ExtractorLLM):
    """Extractor oficial del laboratorio (Gemini).

    Pasos sugeridos:
    1. Cargar GEMINI_API_KEY desde .env (nunca hardcodear la clave).
    2. Leer data/processed/{id_noticia}.txt
    3. Llamar al modelo (p. ej. gemini-1.5-flash) con construir_prompt().
    4. Devolver exclusivamente JSON válido (sin markdown ni explicaciones).
    5. Si un campo no aparece en la noticia, usar null o lista vacía.
    """

    def __init__(
            self,
            repositorio: RepositorioNoticias | None = None,
            ):

        self.repositorio = repositorio or RepositorioNoticias()

        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(model_name=GEMINI_MODEL)


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

    def construir_prompt(self, noticia: NoticiaFuente) -> str:

        return f"""
            Eres un sistema de extracción de información. Tu única tarea es
            leer la noticia delictual a continuación y devolver un JSON que describa
            ÚNICAMENTE lo que el texto dice explícitamente.

            REGLAS OBLIGATORIAS:
            1. No inventes personas, organizaciones, lugares, delitos ni relaciones que
            no estén mencionados literalmente en el texto.
            2. Si un dato no aparece en la noticia, usa null (para strings/objetos) o
            una lista vacía [] (para arreglos). Nunca completes con suposiciones.
            3. Distingue con cuidado los roles de las personas: detenido, imputado,
            acusado, condenado, víctima y testigo NO son equivalentes. Usa el rol
            exacto que el texto atribuye a cada persona, o null si no es claro.
            4. No afirmes culpabilidad si el texto no lo dice de forma explícita
            (por ejemplo, "imputado" no equivale a "culpable").
            5. Cada relación en "relaciones" debe estar respaldada por una frase
            concreta del texto; si no puedes citar esa frase, no la incluyas.
            6. Devuelve EXCLUSIVAMENTE JSON válido: sin texto antes ni después, sin
            bloques de código Markdown (nada de ```json), sin explicaciones ni preguntas.
            7. Normaliza el nombre de la fuente, por ejemplo teletrece.cl es lo mismo que T13 o que TeleTrece. Déjalos todos en un mismo formato.

            ESQUEMA JSON EXACTO (usa estas claves, en este orden, sin agregar ni omitir):
            {{
                "id_noticia": string,
                "titulo": string | null,
                "fecha_publicacion": string | null,
                "fuente": string | null,
                "url": string | null,
                "resumen": string | null,
                "delitos": [string, ...],
                "personas": [{{"nombre": string, "rol": string | null}}, ...],
                "organizaciones": [string, ...],
                "lugares": [string, ...],
                "objetos": [{{"tipo": string, "nombre": string, "cantidad": number | null, "unidad": string | null}}, ...],
                "relaciones": [{{"origen": string, "tipo": string, "destino": string}}, ...]
            }}

            Campos obligatorios (deben existir todos, aunque queden en null o []):
            {self.CAMPOS_OBLIGATORIOS}

            DATOS CONOCIDOS DE ESTA NOTICIA (úsalos tal cual, no los reinterpretes):
            - id_noticia: {noticia.id_noticia}
            - fuente: {noticia.fuente}
            - url: {noticia.url}

            NOTICIA:
            \"\"\"
            {noticia.texto_limpio}
            \"\"\"

            Responde solo con el JSON.
            Equivocarse es tremendamente perjudicial para el análisis. 
            Revisa la noticia las veces que sea necesario si hay algo que no está claro.
            """ 


    def extraer(self, noticia: NoticiaFuente) -> dict:
        try:

            response = self.model.generate_content(
                self.construir_prompt(noticia)
            )

            json_noticia = json.loads(response.text)
            self.repositorio.guardar_json(noticia, json_noticia)
            return json_noticia
        
        except (Exception):
            print(f"La noticia {noticia.id_noticia} falló en su extracción:")
            return None
