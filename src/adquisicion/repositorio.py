"""Persistencia de HTML crudo, texto limpio y json, con id_noticia como clave."""

from __future__ import annotations

from pathlib import Path
import json

from src.config import DIR_JSON, DIR_PROCESSED, DIR_RAW
from src.modelos import NoticiaFuente

class RepositorioNoticias:
    """Guarda y lee archivos intermedios del pipeline de captura y extracción."""

    def __init__(
        self,
        dir_raw: Path = DIR_RAW,
        dir_processed: Path = DIR_PROCESSED,
        dir_json: Path = DIR_JSON,
    ) -> None:
        """ Define, o crea, las direcciones de las carpetas donde se almacenarán los archivos a almacenar.
        """
        self.dir_json = dir_json
        self.dir_raw = dir_raw
        self.dir_processed = dir_processed
        self.dir_json.mkdir(parents=True, exist_ok=True)
        self.dir_raw.mkdir(parents=True, exist_ok=True)
        self.dir_processed.mkdir(parents=True, exist_ok=True)

    def guardar_html(self, noticia: NoticiaFuente, html: str) -> Path:
        """ Almacena en un archivo html la noticia cruda """
        ruta = self.dir_raw / f"{noticia.id_noticia}.html"
        ruta.write_text(html, encoding="utf-8")
        return ruta

    def guardar_texto(self, noticia: NoticiaFuente, texto: str) -> Path:
        """ Crea y almacena el texto procesado de cada noticia """
        ruta = self.dir_processed / f"{noticia.id_noticia}.txt"
        ruta.write_text(texto, encoding="utf-8")
        return ruta

    def leer_texto(self, id_noticia: str) -> str:
        """ Obtiene y lee el texto de una noticia almacenada"""
        return (self.dir_processed / f"{id_noticia}.txt").read_text(encoding="utf-8")

    def guardar_json(self, noticia: NoticiaFuente, json_noticia: dict) -> Path:
        """ Convierte un diccionario de python en un formato JSON para almacenarlo """
        ruta = self.dir_json / f"{noticia.id_noticia}.json"
        ruta.write_text(json.dumps(json_noticia, ensure_ascii=False, indent=4), encoding="utf-8") 
        return ruta

    def leer_json(self, id_noticia: str) -> dict:
        """ Convierte el texto almacenado de un JSON en un diccionario"""
        return json.loads((self.dir_json / f"{id_noticia}.json").read_text(encoding="utf-8"))
