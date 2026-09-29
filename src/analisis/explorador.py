"""Data Understanding sobre el corpus estructurado.

"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # para no abrir ventanas de GUI en el laboratorio

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

from src.config import DIR_JSON, RAIZ

from matplotlib.colors import LinearSegmentedColormap
from src.conocimiento.utilidades import (categoria_delito, normalizar_entidad, categoria_objeto, categoria_organizacion, categoria_relacion, categoria_rol)

DIR_FIGURAS = RAIZ / "reportes" / "figuras"


#paleta: un solo tono para los cinco graficos
ROSA = "#c2185b"
ROSA_SUAVE = "#f3c6d8"
TINTA = "#1a1a19"
TINTA_SUAVE = "#57565a"
GRIS_GRILLA = "#e8e7e3"

class ExploradorDatos:
    """Estadísticas y gráficos mínimos del laboratorio."""

    def cargar(self) -> pd.DataFrame:
        """Carga todos los JSON en un DataFrame de pandas."""
        filas = []
        for ruta in sorted(DIR_JSON.glob("*.json")):
            try:
                data = json.loads(ruta.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                print(f"Error leyendo {ruta}: {exc}")
                continue
            fila = {
                "id_noticia": data.get("id_noticia"),
                "titulo": data.get("titulo"),
                "fecha_publicacion": data.get("fecha_publicacion"),
                "fuente": data.get("fuente"),
                "url": data.get("url"),
                "resumen": data.get("resumen"),
                "delitos": data.get("delitos") or [],
                "personas": data.get("personas") or [],
                "organizaciones": data.get("organizaciones") or [],
                "lugares": data.get("lugares") or [],
                "objetos": data.get("objetos") or [],
                "relaciones": data.get("relaciones") or [],
            }
            filas.append(fila)
        return pd.DataFrame(filas)

    def _estilo(self) -> None:
        """Ajustes de matplotlib comunes a los cinco graficos."""
        plt.rcParams.update({
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#d8d7d2",
            "axes.labelcolor": TINTA_SUAVE,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.titlecolor": TINTA,
            "xtick.color": TINTA_SUAVE,
            "ytick.color": TINTA_SUAVE,
            "font.size": 10,
        })

    def _limpiar(self, ax, eje: str = "x") -> None:
        """Saca el marco y deja una grilla tenue solo en el eje de magnitud."""
        for lado in ("top", "right", "left" if eje == "x" else "bottom"):
            ax.spines[lado].set_visible(False)
        ax.grid(axis=eje, color=GRIS_GRILLA, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)

    def _guardar(self, fig, nombre: str) -> Path:
        """Guarda el grafico en reportes/figuras/ y cierra la figura."""
        DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
        ruta = DIR_FIGURAS / nombre
        fig.savefig(ruta)
        plt.close(fig)
        print(f" Grafico guardado: {ruta}")
        return ruta

    def _barras(self, conteo, titulo: str, subtitulo: str,
                etiqueta_valor: str, nombre_archivo: str) -> Path:
        """Ranking horizontal: barra mas larga arriba, valor al final de cada barra."""
        conteo = conteo.sort_values(ascending=True)
        alto = max(3.0, 0.42 * len(conteo) + 1.8)

        self._estilo()
        fig, ax = plt.subplots(figsize=(9.5, alto))
        barras = ax.barh(list(conteo.index), conteo.to_numpy(), color=ROSA, height=0.68)

        #el numero al final de cada barra, para no perseguir la grilla con el ojo
        tope = float(conteo.max()) if len(conteo) else 1.0
        for barra, valor in zip(barras, conteo.to_numpy()):
            ax.text(barra.get_width() + tope * 0.015,
                    barra.get_y() + barra.get_height() / 2,
                    f"{valor:g}", va="center", ha="left",
                    fontsize=9, color=TINTA_SUAVE)

        ax.set_xlim(0, tope * 1.12)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
        ax.set_xlabel(etiqueta_valor)
        ax.set_title(titulo, loc="left", pad=18)
        ax.text(0, 1.015, subtitulo, transform=ax.transAxes,
                fontsize=9.5, color=TINTA_SUAVE)
        self._limpiar(ax, "x")
        return self._guardar(fig, nombre_archivo)
    
    def noticias_por_fuente(self) -> None:
        """Distribucion de noticias por medio de comunicacion."""
        df = self.cargar()
        conteo = df["fuente"].fillna("Fuente desconocida").value_counts()
        self._barras(conteo,
                     "Cobertura del corpus por medio de comunicación",
                        f"{len(df)} noticias | {conteo.size} fuentes",
                        "Noticias",
                        "01_noticias_por_fuente.png")
        
    def delitos_frecuentes(self) -> None:
        """Top 10 de delitos mencionados en el corpus."""
        df = self.cargar()
        serie = df["delitos"].explode().dropna().map(categoria_delito)
        serie = serie[serie != ""]
        conteo = serie.value_counts().head(10)
        self._barras(conteo,
                     "Top 10 de delitos mencionados",
                     f"{serie.size} menciones · {serie.nunique()} categorías",
                     "Menciones",
                     "02_delitos_frecuentes.png")
        
    def lugares_frecuentes(self) -> None:
        """Lugares más mencionados en el corpus."""
        df = self.cargar()
        serie = df["lugares"].explode().dropna().map(normalizar_entidad)
        serie = serie[serie != ""]
        conteo = serie.value_counts().head(12)
        self._barras(conteo,
                     "Lugares más mencionados",
                     f"{serie.size} menciones · {serie.nunique()} lugares distintos",
                     "Menciones",
                     "03_lugares_frecuentes.png")

    def campos_faltantes(self) -> None:
        """Porcentaje de noticias que carecen de cada campo del contrato JSON."""
        df = self.cargar()
        vacios = {}
        for campo in df.columns:
            sin_dato = 0
            for valor in df[campo]:
                if isinstance(valor, list):
                    if len(valor) == 0:
                        sin_dato += 1
                elif pd.isna(valor) or str(valor).strip() == "":
                    sin_dato += 1
            vacios[campo] = round(100 * sin_dato / len(df), 1) if len(df) else 0.0
        conteo = pd.Series(vacios)
        self._barras(conteo,
                     "Porcentaje de noticias con campos faltantes",
                     f"{len(df)} noticias | {conteo.size} campos del contrato JSON",
                     "Porcentaje de noticias sin dato (%)",
                     "04_campos_faltantes.png")
        

    def evolucion_temporal(self) -> None:
        """Cantidad de noticias por mes, para ver tendencias y estacionalidad."""
        df = self.cargar()

        fechas = pd.to_datetime(df["fecha_publicacion"], errors="coerce")
        sin_fecha = fechas.isna().sum()
        fechas = fechas.dropna()

        if fechas.empty:
            print("No hay fechas válidas en el corpus; no se puede graficar evolución temporal.")
            return

        periodos = fechas.dt.to_period("M")
        rango = pd.period_range(periodos.min(), periodos.max(), freq="M")
        conteo = periodos.value_counts().reindex(rango, fill_value=0).sort_index()
        etiquetas = [str(p) for p in conteo.index]

        self._estilo()
        fig, ax = plt.subplots(figsize=(10, 4.8))
        ax.plot(etiquetas, conteo.to_numpy(), color=ROSA,
                linewidth=2, marker="o", markersize=7)
        ax.fill_between(etiquetas, conteo.to_numpy(), color=ROSA, alpha=0.12)

        for x, y in zip(etiquetas, conteo.to_numpy()):
            ax.annotate(f"{y:g}", (x, y), textcoords="offset points",
                        xytext=(0, 9), ha="center", fontsize=9, color=TINTA_SUAVE)

        ax.set_ylim(0, max(1, int(conteo.max())) * 1.25)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        ax.set_ylabel("Noticias publicadas")
        ax.set_title("Evolución mensual de la cobertura", loc="left", pad=18)

        nota = f" · {sin_fecha} sin fecha" if sin_fecha else ""
        ax.text(0, 1.02,
                f"{int(conteo.sum())} noticias entre {etiquetas[0]} y {etiquetas[-1]}{nota}",
                transform=ax.transAxes, fontsize=9.5, color=TINTA_SUAVE)

        if len(etiquetas) > 8:
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

        self._limpiar(ax, "y")
        self._guardar(fig, "05_evolucion_temporal.png")


    

    #graficos extras porque si :p

    def organizaciones_frecuentes(self) -> None:
        """Top 10 de organizaciones mencionadas en el corpus."""
        df = self.cargar()
        serie = df["organizaciones"].explode().dropna().map(categoria_organizacion)        
        serie = serie[serie != ""]
        conteo = serie.value_counts().head(10)
        self._barras(conteo,
                     "Organizaciones más mencionadas",
                     f"{serie.size} menciones · {serie.nunique()} organizaciones distintas",
                     "Menciones",
                     "06_organizaciones_frecuentes.png")
        
    def personas_frecuentes(self) -> None:
        """Top 10 de personas mencionadas en el corpus."""
        df = self.cargar()
        personas = df["personas"].explode().dropna()
        nombres = [p.get("nombre") for p in personas if isinstance(p, dict) and "nombre" in p]
        conteo = pd.Series(nombres).value_counts().head(10)
        self._barras(conteo,
                     "Personas más frecuentes en el corpus",
                     f"{len(df)} noticias | {len(nombres)} menciones de personas",
                     "Menciones",
                     "07_personas_frecuentes.png")

    def tipos_objetos_incautados(self) -> None:
        """Tipos de objetos incautados mas frecuentes en el corpus."""
        df = self.cargar()
        objetos = df["objetos"].explode().dropna()
        tipos = [categoria_objeto(o.get("nombre") if isinstance(o, dict) else o)
                 for o in objetos]
        tipos = [t for t in tipos if t]
        if not tipos:
            print(" Sin objetos con tipo; no se genera el grafico.")
            return
        serie = pd.Series(tipos)
        conteo = serie.value_counts().head(10)
        self._barras(conteo,
                     "Tipos de objetos incautados",
                     f"{serie.size} objetos · {serie.nunique()} categorías",
                     "Objetos",
                     "08_tipos_objetos_incautados.png")
        
    def tipos_relaciones_frecuentes(self) -> None:
        """Tipos de arista del grafo, para ver su densidad semantica."""
        df = self.cargar()
        relaciones = df["relaciones"].explode().dropna()
        tipos = [categoria_relacion(r.get("tipo")) for r in relaciones
                 if isinstance(r, dict) and r.get("tipo")]
        serie = pd.Series(tipos)
        conteo = serie.value_counts().head(12)
        self._barras(conteo,
                     "Tipos de relaciones más frecuentes en el corpus",
                     f"{serie.size} relaciones · {serie.nunique()} tipos distintos",
                     "Relaciones",
                     "09_tipos_relaciones_frecuentes.png")
        
    def densidad_entidades_por_noticia(self) -> None:
        """Distribucion de cuantas entidades se extraen por noticia."""
        df = self.cargar()
        campos = ("delitos", "personas", "organizaciones", "lugares", "objetos")
 
        totales = []
        for _, fila in df.iterrows():
            total = 0
            for campo in campos:
                valor = fila.get(campo)
                if isinstance(valor, list):
                    total += len(valor)
            totales.append(total)
 
        if not totales:
            print(" Sin noticias; no se genera el grafico.")
            return
 
        serie = pd.Series(totales)
        promedio = serie.mean()
 
        self._estilo()
        fig, ax = plt.subplots(figsize=(9.5, 4.8))
 
        #un bin por valor entero, para que no invente medias entidades
        bins = range(int(serie.min()), int(serie.max()) + 2)
        ax.hist(serie, bins=bins, color=ROSA, rwidth=0.85, align="left")
 
        #la linea del promedio, con su etiqueta
        ax.axvline(promedio, color=TINTA, linewidth=1.4, linestyle="--")
        ax.text(promedio, ax.get_ylim()[1] * 0.96, f" promedio: {promedio:.1f}",
                ha="left", va="top", fontsize=9, color=TINTA)
 
        ax.set_xlabel("Entidades extraídas de la noticia")
        ax.set_ylabel("Cantidad de noticias")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_title("Densidad de extracción por noticia", loc="left", pad=18)
        ax.text(0, 1.02,
                f"{len(serie)} noticias · mínimo {serie.min()} · máximo {serie.max()} "
                f"· mediana {serie.median():.0f}",
                transform=ax.transAxes, fontsize=9.5, color=TINTA_SUAVE)
        self._limpiar(ax, "y")
        self._guardar(fig, "10_densidad_entidades.png")

    def delitos_por_zona(self) -> None:
        """Mapa de calor: coocurrencia entre los lugares y los delitos mas frecuentes."""
        df = self.cargar()
 
        pares = []
        for _, fila in df.iterrows():
            lugares = [normalizar_entidad(x) for x in (fila.get("lugares") or [])
                       if isinstance(x, str)]
            lugares = [x for x in lugares if x]
            delitos = [categoria_delito(x) for x in (fila.get("delitos") or [])
                       if isinstance(x, str)]
            delitos = [x for x in delitos if x]
            for delito in delitos:
                for lugar in lugares:
                    pares.append((lugar, delito))
 
        if not pares:
            print(" No hay lugares y delitos en la misma noticia; no se genera el grafico.")
            return
 
        cruce = pd.DataFrame(pares, columns=["lugar", "delito"])
        top_lugares = cruce["lugar"].value_counts().head(5).index
        top_delitos = cruce["delito"].value_counts().head(5).index
        tabla = pd.crosstab(cruce["lugar"], cruce["delito"])
        tabla = tabla.reindex(index=top_lugares, columns=top_delitos, fill_value=0)
 
        self._estilo()
        fig, ax = plt.subplots(figsize=(9.5, 5))
 
        #rampa secuencial del mismo rosa: blanco = nada, rosa fuerte = mucho
        rampa = LinearSegmentedColormap.from_list("rosa", ["#ffffff", ROSA])
        imagen = ax.imshow(tabla.to_numpy(), cmap=rampa, aspect="auto")
 
        ax.set_xticks(range(len(tabla.columns)))
        ax.set_xticklabels(tabla.columns, rotation=30, ha="right")
        ax.set_yticks(range(len(tabla.index)))
        ax.set_yticklabels(tabla.index)
 
        #el numero dentro de cada celda, en blanco si el fondo es oscuro
        tope = tabla.to_numpy().max() or 1
        for i in range(tabla.shape[0]):
            for j in range(tabla.shape[1]):
                valor = tabla.iat[i, j]
                color = "white" if valor > tope * 0.6 else TINTA_SUAVE
                ax.text(j, i, f"{valor:g}", ha="center", va="center",
                        fontsize=10, color=color)
 
        ax.set_title("Coocurrencia entre lugares y delitos", loc="left", pad=32)
        ax.text(0, 1.015,
                f"Top 5 de cada uno · {len(pares)} coocurrencias en {len(df)} noticias",
                transform=ax.transAxes, fontsize=9.5, color=TINTA_SUAVE)
 
        #sin marco ni grilla: el color ya lleva toda la informacion
        for lado in ("top", "right", "left", "bottom"):
            ax.spines[lado].set_visible(False)
        ax.tick_params(length=0)
        ax.grid(False)
 
        barra = fig.colorbar(imagen, ax=ax, shrink=0.8)
        barra.set_label("Noticias donde aparecen juntos", color=TINTA_SUAVE, fontsize=9)
        barra.outline.set_visible(False)
 
        self._guardar(fig, "11_delitos_por_zona.png")

    def roles_de_personas(self) -> None:
        """Roles de las personas mencionadas: de quién habla la prensa."""
        df = self.cargar()
        roles = []
        sin_rol = 0
        for personas in df["personas"]:
            if not isinstance(personas, list):
                continue
            for persona in personas:
                if not isinstance(persona, dict):
                    continue
                categoria = categoria_rol(persona.get("rol"))
                if categoria:
                    roles.append(categoria)
                else:
                    sin_rol += 1

        if not roles:
            print(" Sin roles en el corpus; no se genera el grafico.")
            return

        total = len(roles) + sin_rol
        serie = pd.Series(roles)
        conteo = serie.value_counts()
        self._barras(conteo,
                     "Roles de las personas mencionadas",
                     f"{len(roles)} personas con rol · {serie.nunique()} categorías "
                     f"agrupadas desde 36 · {sin_rol} personas "
                     f"({100 * sin_rol / total:.0f}%) sin rol declarado",
                     "Personas",
                     "12_roles_personas.png")

    def ejecutar(self) -> None:
            """Corre todas las visualizaciones pedidas en la guía."""
            graficos = (
                ("Noticias por fuente", self.noticias_por_fuente),
                ("Delitos frecuentes", self.delitos_frecuentes),
                ("Lugares frecuentes", self.lugares_frecuentes),
                ("Campos faltantes", self.campos_faltantes),
                ("Evolución temporal", self.evolucion_temporal),
                ("Organizaciones frecuentes", self.organizaciones_frecuentes),
                ("Personas frecuentes", self.personas_frecuentes),
                ("Tipos de objetos incautados", self.tipos_objetos_incautados),
                ("Tipos de relaciones frecuentes", self.tipos_relaciones_frecuentes),
                ("Densidad de entidades por noticia", self.densidad_entidades_por_noticia),
                ("Delitos por zona", self.delitos_por_zona),
                ("Roles de personas", self.roles_de_personas),
            )
            
            for nombre, metodo in graficos:
                try:
                    metodo()
                except Exception as exc:
                    print(f"Error generando {nombre}: {exc}")