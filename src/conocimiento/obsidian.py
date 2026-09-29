"""Persistencia final: red de notas Markdown para Obsidian.

No se usa SQLite, MongoDB ni Neo4j. Cada noticia y cada entidad debe
tener su propia nota, enlazada con [[wiki-links]].
"""

from __future__ import annotations

import json

from abc import ABC, abstractmethod
from pathlib import Path

from src.config import DIR_VAULT, DIR_JSON

from collections import defaultdict
from src.conocimiento.utilidades import enlace_obsidian, normalizar_entidad, slugify

class EscritorObsidian(ABC):
    """Contrato para generar la bóveda a partir de JSON validado."""

    @abstractmethod
    def escribir_noticia(self, data: dict) -> Path:
        """Crea obsidian_vault/Noticias/{id_noticia}.md con frontmatter y enlaces."""

    @abstractmethod
    def escribir_entidades(self, noticias: list[dict]) -> None:
        """Agrega notas de delitos, personas, organizaciones, lugares y objetos."""

    @abstractmethod
    def escribir_indice(self, noticias: list[dict]) -> Path:
        """Crea obsidian_vault/00_Indice.md."""

    @abstractmethod
    def escribir_vault(self, noticias: list[dict]) -> None:
        """Orquesta noticia + entidades + índice."""


class EscritorVaultObsidian(EscritorObsidian):
    """Implementación objetivo del laboratorio.

    Use src.conocimiento.utilidades.slugify y enlace_obsidian.
    Jerarquía esperada:
        obsidian_vault/
        ├── 00_Indice.md
        ├── Noticias/
        ├── Delitos/
        ├── Personas/
        ├── Organizaciones/
        ├── Lugares/
        ├── Objetos/
        └── Relaciones/
    """

    #campo del json: (carpeta, tipo, clave con el detalle extra)
    CAMPOS = {
        "delitos": ("Delitos", "delito", None),
        "personas": ("Personas", "persona", "rol"),
        "organizaciones": ("Organizaciones", "organizacion", None),
        "lugares": ("Lugares", "lugar", None),
        "objetos": ("Objetos", "objeto", "tipo"),
    }

    #campos que tienen que ser listas
    CAMPOS_LISTA = ("delitos", "personas", "organizaciones",
                    "lugares", "objetos", "relaciones")

    #campos de texto que deberian venir en cada noticia
    CAMPOS_TEXTO = ("titulo", "fecha_publicacion", "fuente", "url", "resumen")

    #carpetas de la jerarquia del vault
    CARPETAS = ("Noticias", "Delitos", "Personas",
                "Organizaciones", "Lugares", "Objetos", "Relaciones")

    def __init__(self, vault: Path = DIR_VAULT, dir_json: Path = DIR_JSON) -> None:
        self.vault = vault
        self.dir_json = dir_json

    @staticmethod
    def _nombre(item) -> str:
        """Nombre de una entidad, venga como texto o como dict."""
        if isinstance(item, str):
            return item.strip()
        if isinstance(item, dict):
            for clave in ("nombre", "nombre_o_referencia", "tipo", "titulo"):
                valor = item.get(clave)
                if isinstance(valor, str) and valor.strip():
                    return valor.strip()
        return ""

    def cargar_noticias(self) -> list[dict]:
        """Lee data/json/*.json y valida lo minimo de cada archivo."""
        noticias = []
        for ruta in sorted(self.dir_json.glob("*.json")):

            #un archivo malo no debe tumbar el lote completo
            try:
                data = json.loads(ruta.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                print(f" Se omite {ruta.name}: JSON invalido ({exc})")
                continue

            if not isinstance(data, dict):
                print(f" Se omite {ruta.name}: el archivo no trae un objeto JSON")
                continue

            #si falta el id uso el nombre del archivo
            if not data.get("id_noticia"):
                data["id_noticia"] = ruta.stem

            #lo que venga null o no sea lista queda como lista vacia
            for campo in self.CAMPOS_LISTA:
                if not isinstance(data.get(campo), list):
                    data[campo] = []

            #aviso de los campos de texto que falten, pero la noticia igual entra
            faltantes = []
            for campo in self.CAMPOS_TEXTO:
                if not data.get(campo):
                    faltantes.append(campo)
            if faltantes:
                print(f" Aviso en {ruta.name}: sin {', '.join(faltantes)}")

            noticias.append(data)
        return noticias

    def escribir_noticia(self, data: dict) -> Path:
        """Crea obsidian_vault/Noticias/{id_noticia}.md con frontmatter y enlaces."""

        #extraer los datos del diccionario
        id_noticia = data.get("id_noticia") or "N000"
        titulo = data.get("titulo") or "Sin título"
        fecha = data.get("fecha_publicacion") or "Fecha desconocida"
        fuente = data.get("fuente") or "Fuente desconocida"
        url = data.get("url") or "URL desconocida"
        resumen = data.get("resumen") or "Resumen no disponible"
        titulo_yaml = str(titulo).replace('"', "'")

        #armar yaml y contenido markdown
        lineas = [
            "---",
            f"id: {id_noticia}",
            f'titulo: "{titulo_yaml}"',
            f"fecha: {fecha}",
            f"fuente: {fuente}",
            f"url: {url}",
            "tipo: noticia",
            "---",
            f"\n# {titulo}\n",
            f"**Fuente:** {fuente}  \n**Fecha:** {fecha}  \n[Enlace a la noticia]({url})\n",
            f"\n## Resumen\n{resumen}\n",
            "## Delitos\n",
        ]

        #listar delitos
        for crime in data.get("delitos") or []:
            nombre = normalizar_entidad(self._nombre(crime))
            if nombre:
                lineas.append(f"- {enlace_obsidian(nombre)}")

        #listar personas cn su rol
        lineas.append("\n## Personas\n")
        for people in data.get("personas") or []:
            nombre = normalizar_entidad(self._nombre(people))
            rol = "Rol desconocido"
            if isinstance(people, dict):
                rol = people.get("rol") or "Rol desconocido"
            if not nombre:
                continue
            if "victim" in str(rol).lower():
                continue
            lineas.append(f"- {enlace_obsidian(nombre)} ({rol})")

        #listar victimas (en este esquema son personas con rol victima)
        lineas.append("\n## Víctimas\n")
        for people in data.get("personas") or []:
            rol = ""
            if isinstance(people, dict):
                rol = people.get("rol") or ""
            if "victim" not in str(rol).lower():
                continue
            nombre = normalizar_entidad(self._nombre(people))
            if nombre:
                lineas.append(f"- {enlace_obsidian(nombre)}")

        #listar organizaciones
        lineas.append("\n## Organizaciones\n")
        for org in data.get("organizaciones") or []:
            nombre = normalizar_entidad(self._nombre(org))
            if nombre:
                lineas.append(f"- {enlace_obsidian(nombre)}")

        #listar lugares
        lineas.append("\n## Lugares\n")
        for place in data.get("lugares") or []:
            nombre = normalizar_entidad(self._nombre(place))
            if nombre:
                lineas.append(f"- {enlace_obsidian(nombre)}")

        #listar objetos
        lineas.append("\n## Objetos\n")
        for obj in data.get("objetos") or []:
            nombre_obj = normalizar_entidad(self._nombre(obj))
            tipo_obj = "objeto"
            if isinstance(obj, dict):
                tipo_obj = obj.get("tipo") or "objeto"
            if nombre_obj:
                lineas.append(f"- {enlace_obsidian(nombre_obj)} ({tipo_obj})")

        #listar relaciones
        lineas.append("\n## Relaciones\n")
        for rel in data.get("relaciones") or []:
            if not isinstance(rel, dict):
                continue
            origen = normalizar_entidad(self._nombre(rel.get("origen")))
            destino = normalizar_entidad(self._nombre(rel.get("destino")))
            tipo = rel.get("tipo") or "se_relaciona_con"
            if not origen or not destino:
                continue
            lineas.append(f"- {enlace_obsidian(origen)} -- \"{tipo}\" --> {enlace_obsidian(destino)}")

        #guardar el archivo
        ruta_arch = self.vault / "Noticias" / f"{id_noticia}.md"
        ruta_arch.parent.mkdir(parents=True, exist_ok=True)
        ruta_arch.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        return ruta_arch

    def escribir_entidades(self, noticias: list[dict]) -> None:
        """Agrega notas de delitos, personas, organizaciones, lugares y objetos."""

        #recorrer noticias y agrupar entidades
        indices = defaultdict(set)
        nombres = {}
        tipos = {}
        relaciones = defaultdict(set)
        nombres_rel = {}

        for noticia in noticias:
            id_noticia = noticia.get("id_noticia") or "N000"

            for campo, (carpeta, tipo, subtipo) in self.CAMPOS.items():
                for entidad in noticia.get(campo) or []:
                    nombre = self._nombre(entidad)
                    archivo = normalizar_entidad(nombre)
                    if not archivo:
                        continue
                    clave = (carpeta, archivo)
                    detalle = ""
                    if subtipo and isinstance(entidad, dict):
                        detalle = str(entidad.get(subtipo) or "").strip()
                    indices[clave].add((id_noticia, detalle))
                    nombres.setdefault(clave, nombre)
                    tipos.setdefault(clave, tipo)

            for rel in noticia.get("relaciones") or []:
                if not isinstance(rel, dict):
                    continue
                origen = self._nombre(rel.get("origen"))
                destino = self._nombre(rel.get("destino"))
                tipo_rel = str(rel.get("tipo") or "se_relaciona_con").strip()
                if not normalizar_entidad(origen) or not normalizar_entidad(destino):
                    continue
                archivo_rel = slugify(tipo_rel).lower()
                relaciones[archivo_rel].add((origen, destino, id_noticia))
                nombres_rel.setdefault(archivo_rel, tipo_rel)

        #escribir una nota por entidad
        for (carpeta, archivo), enlaces in indices.items():
            nombre = nombres[(carpeta, archivo)]
            nombre_yaml = nombre.replace('"', "'")
            menciones = len({id_noticia for id_noticia, _ in enlaces})

            lineas = [
                "---",
                f'entidad: "{nombre_yaml}"',
                f"categoria: {carpeta}",
                f"tipo: {tipos[(carpeta, archivo)]}",
                f"menciones: {menciones}",
                "---",
                f"\n# {nombre}\n",
                "## Noticias relacionadas\n",
            ]

            for id_noticia, detalle in sorted(enlaces):
                sufijo = f" ({detalle})" if detalle else ""
                lineas.append(f"- {enlace_obsidian(id_noticia)}{sufijo}")

            ruta = self.vault / carpeta / f"{archivo}.md"
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")

        #escribir una nota por tipo de relacion
        for archivo_rel, registros in relaciones.items():
            tipo_rel = nombres_rel.get(archivo_rel)
            lineas = [
                "---",
                f'tipo_relacion: "{tipo_rel}"',
                "tipo: relacion",
                f"conexiones: {len(registros)}",
                "---",
                f"\n# Relación: {tipo_rel}\n",
                "## Conexiones identificadas\n",
            ]

            for origen, destino, id_noticia in sorted(registros):
                origen_link = enlace_obsidian(normalizar_entidad(origen))
                destino_link = enlace_obsidian(normalizar_entidad(destino))
                lineas.append(f"- {origen_link} --> {destino_link} (noticia: {enlace_obsidian(id_noticia)})")

            ruta = self.vault / "Relaciones" / f"{archivo_rel}.md"
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")

        print(f" Entidades escritas: {len(indices)} | tipos de relación: {len(relaciones)}")

    def escribir_indice(self, noticias: list[dict]) -> Path:
        """Crea obsidian_vault/00_Indice.md."""
        lineas = [
            "---",
            "tipo: indice",
            f"noticias: {len(noticias)}",
            "---",
            "\n# Índice del vault\n",
        ]

        lineas.append("## Noticias\n")
        lineas.append("| ID | Fecha | Fuente | Título |")
        lineas.append("| --- | --- | --- | --- |")
        for noticia in noticias:
            id_noticia = noticia.get("id_noticia") or "N000"
            fecha = noticia.get("fecha_publicacion") or "Fecha desconocida"
            fuente = noticia.get("fuente") or "Fuente desconocida"
            titulo = noticia.get("titulo") or "Sin título"
            #un pipe en el titulo rompe la columna de la tabla
            titulo = str(titulo).replace("|", "/")
            lineas.append(f"| {enlace_obsidian(id_noticia)} | {fecha} | {fuente} | {titulo} |")

        #contar en cuantas noticias aparece cada entidad
        conteo = defaultdict(set)
        for noticia in noticias:
            id_noticia = noticia.get("id_noticia") or "N000"
            for campo, (carpeta, tipo, subtipo) in self.CAMPOS.items():
                for entidad in noticia.get(campo) or []:
                    archivo = normalizar_entidad(self._nombre(entidad))
                    if not archivo:
                        continue
                    conteo[(carpeta, archivo)].add(id_noticia)

        #una seccion por categoria, ordenada de mas a menos mencionada
        for campo, (carpeta, tipo, subtipo) in self.CAMPOS.items():
            filas = []
            for (c, archivo), ids in conteo.items():
                if c == carpeta:
                    filas.append((len(ids), archivo))
            filas.sort(reverse=True)

            lineas.append(f"\n## {carpeta} ({len(filas)})\n")

            for cuenta, archivo in filas:
                lineas.append(f"- {enlace_obsidian(archivo)} ({cuenta} menciones)")

        #contar conexiones por tipo de relacion
        conteo_rel = defaultdict(set)
        for noticia in noticias:
            id_noticia = noticia.get("id_noticia") or "N000"
            for rel in noticia.get("relaciones") or []:
                if not isinstance(rel, dict):
                    continue
                origen = normalizar_entidad(self._nombre(rel.get("origen")))
                destino = normalizar_entidad(self._nombre(rel.get("destino")))
                if not origen or not destino:
                    continue
                tipo_rel = str(rel.get("tipo") or "se_relaciona_con").strip()
                archivo_rel = slugify(tipo_rel).lower()
                conteo_rel[archivo_rel].add((origen, destino, id_noticia))

        filas_rel = []
        for archivo_rel, registros in conteo_rel.items():
            filas_rel.append((len(registros), archivo_rel))
        filas_rel.sort(reverse=True)

        lineas.append(f"\n## Relaciones ({len(filas_rel)})\n")
        for cuenta, archivo_rel in filas_rel:
            lineas.append(f"- {enlace_obsidian(archivo_rel)} ({cuenta} conexiones)")

        ruta = self.vault / "00_Indice.md"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        return ruta

    def escribir_vault(self, noticias: list[dict] | None = None) -> None:
        """Orquesta noticia + entidades + índice."""

        #si no le pasan noticias las lee de data/json/*.json
        if not noticias:
            noticias = self.cargar_noticias()
        if not noticias:
            print(f" No hay noticias que escribir en {self.dir_json}")
            return

        #crear la jerarquia completa, incluida Relaciones/
        for carpeta in self.CARPETAS:
            (self.vault / carpeta).mkdir(parents=True, exist_ok=True)

        for noticia in noticias:
            self.escribir_noticia(noticia)
        print(f" Noticias escritas: {len(noticias)}")

        self.escribir_entidades(noticias)
        ruta = self.escribir_indice(noticias)
        print(f" Vault listo en {self.vault} (indice: {ruta.name})")