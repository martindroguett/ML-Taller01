"""Descubrimiento de noticias vía RSS de Google News (Chile).

No se scrapea el HTML de news.google.com. El canal soportado es el RSS
público, que entrega título, medio, fecha y un enlace redirector.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode, urlparse

import feedparser
from googlenewsdecoder import gnewsdecoder

from src.adquisicion.http import ClienteHTTP
from src.config import (
    COLUMNAS_URLS,
    GOOGLE_NEWS_PARAMS_BASE,
    GOOGLE_NEWS_RSS,
    RUTA_CONSULTAS,
    RUTA_URLS,
)


@dataclass
class ItemGoogleNews:
    """Una entrada del RSS antes de persistirla en urls.csv."""

    titulo: str
    enlace_google: str
    url_final: str
    fuente: str
    categoria_busqueda: str


class DescubridorGoogleNews:
    """Busca noticias, resuelve redirects y actualiza data/urls.csv."""

    def __init__(
        self,
        cliente: ClienteHTTP | None = None,
        ruta_urls: Path = RUTA_URLS,
        ruta_consultas: Path = RUTA_CONSULTAS,
        limite_por_consulta: int = 5,
    ) -> None:
        self.cliente = cliente or ClienteHTTP()
        self.ruta_urls = ruta_urls
        self.ruta_consultas = ruta_consultas
        self.limite_por_consulta = limite_por_consulta

    def buscar(self, consulta: str, limite: int | None = None) -> list:
        """Parsea el RSS de una consulta. No resuelve aún las URLs finales."""
        limite = limite if limite is not None else self.limite_por_consulta
        params = {**GOOGLE_NEWS_PARAMS_BASE, "q": consulta}
        url = f"{GOOGLE_NEWS_RSS}?{urlencode(params)}"
        # Se descarga con ClienteHTTP (User-Agent y pausa), no con urllib interno.
        xml = self.cliente.texto(url)
        feed = feedparser.parse(xml)
        return list(feed.entries)[:limite]

    def resolver_url_final(self, link_google: str) -> str:
        """Sigue las redirecciones hasta la URL del medio original."""
        resultado = gnewsdecoder(link_google)
        if not resultado.get("success"):
            raise ValueError(resultado.get("message", "Fallo desconocido del decodificador"))
        return resultado["decoded_url"]

    def _fuente_desde_entrada(self, entrada, url_final: str) -> str:
        fuente = ""
        source = getattr(entrada, "source", None)
        if source is not None:
            fuente = getattr(source, "title", "") or ""
        if not fuente:
            host = urlparse(url_final).netloc.lower()
            fuente = host.replace("www.", "")
        return fuente.strip() or "desconocida"

    def _siguiente_id(self, existentes: list[dict]) -> str:
        numeros = []
        for fila in existentes:
            ident = fila.get("id_noticia", "")
            if ident.startswith("N") and ident[1:].isdigit():
                numeros.append(int(ident[1:]))
        siguiente = (max(numeros) + 1) if numeros else 1
        return f"N{siguiente:03d}"

    def _leer_urls(self) -> list[dict]:
        if not self.ruta_urls.exists():
            return []
        with self.ruta_urls.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def _escribir_urls(self, filas: list[dict]) -> None:
        self.ruta_urls.parent.mkdir(parents=True, exist_ok=True)
        with self.ruta_urls.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNAS_URLS)
            writer.writeheader()
            for fila in filas:
                writer.writerow({col: fila.get(col, "") for col in COLUMNAS_URLS})

    def _leer_consultas(self) -> list[dict]:
        with self.ruta_consultas.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def actualizar_urls_csv(self, consultas: list[dict] | None = None) -> list[ItemGoogleNews]:
        """Ejecuta las consultas, resuelve URLs y agrega filas nuevas sin duplicar."""
        consultas = consultas if consultas is not None else self._leer_consultas()
        existentes = self._leer_urls()
        urls_vistas = {fila["url"].rstrip("/") for fila in existentes if fila.get("url")}
        nuevos: list[ItemGoogleNews] = []

        for consulta_row in consultas:
            texto = (consulta_row.get("consulta") or "").strip()
            categoria = (consulta_row.get("categoria_busqueda") or "").strip()
            try:
                limite = int(consulta_row.get("limite") or self.limite_por_consulta)
            except ValueError:
                limite = self.limite_por_consulta
            if not texto:
                continue

            print(f"  [Google News] Buscando: {texto!r} (máx. {limite})")
            try:
                entradas = self.buscar(texto, limite=limite)
            except Exception as exc:  
                print(f"    Error al leer RSS: {exc}")
                continue

            for entrada in entradas:
                enlace = getattr(entrada, "link", "") or ""
                if not enlace:
                    continue
                try:
                    url_final = self.resolver_url_final(enlace)
                except Exception as exc:  # noqa: BLE001
                    print(f"    No se resolvió redirect: {exc}")
                    continue

                clave = url_final.rstrip("/")
                if clave in urls_vistas:
                    continue

                item = ItemGoogleNews(
                    titulo=getattr(entrada, "title", "") or "",
                    enlace_google=enlace,
                    url_final=url_final,
                    fuente=self._fuente_desde_entrada(entrada, url_final),
                    categoria_busqueda=categoria,
                )
                nuevo_id = self._siguiente_id(existentes)
                existentes.append(
                    {
                        "id_noticia": nuevo_id,
                        "fuente": item.fuente,
                        "url": item.url_final,
                        "categoria_busqueda": item.categoria_busqueda,
                    }
                )
                urls_vistas.add(clave)
                nuevos.append(item)
                print(f"    + {nuevo_id} {item.fuente}: {item.url_final}")

        self._escribir_urls(existentes)
        return nuevos

    def reparar_urls_existentes(self) -> tuple[int, int]:
        """Reintenta resolver_url_final sobre filas ya guardadas con link roto."""

        filas = self._leer_urls()
        ok, fallos = 0, 0
        for fila in filas:
            url_actual = fila.get("url", "")
            if "news.google.com" not in url_actual:
                continue 

            try:
                fila["url"] = self.resolver_url_final(url_actual)
                ok += 1
                print(f"  [{fila['id_noticia']}] reparada → {fila['url']}")
            except Exception as exc:
                fallos += 1
                print(f"  [{fila['id_noticia']}] no se pudo reparar: {exc}")

        self._escribir_urls(filas)
        print(f"Reparación finalizada: {ok} ok, {fallos} fallos")
        return ok, fallos

