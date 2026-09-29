"""Nombres de archivo estables para enlaces de Obsidian."""

from __future__ import annotations

import re
import unicodedata


#entidades que no aportan al grafo: aparecen en casi todas las noticias
#y tapan a las que si distinguen un caso de otro
ENTIDADES_IGNORADAS = {
    "chile",
    "republica_de_chile",
    "pais",
    "nacional",
    "desconocido",
    "sin_nombre",
    "norte_de_chile",
    "zona_norte",
}

#LIMPIEZA: el mismo concepto escrito distinto (plurales, sinonimos, siglas).
#No pierde informacion: nadie discute que "secuestros" y "secuestro" son lo mismo.
VARIANTES = {
    #objetos
    "armas_de_fuego": "arma_de_fuego",
    "pistolas": "pistola",
    "municiones": "municion",
    "drogas": "droga",
    "sustancia_ilicita": "droga",
    "sustancias_ilicitas": "droga",
    "vehiculos": "vehiculo",
    "telefono": "telefono_celular",
    "telefonos": "telefono_celular",
    "celular": "telefono_celular",
    "celulares": "telefono_celular",
    "santiago_de_chile": "santiago",

    #delitos (canonico en singular)
    "amenazas": "amenaza",
    "extorsiones": "extorsion",
    "secuestros": "secuestro",
    "secuestros_extorsivos": "secuestro_extorsivo",
    "homicidios": "homicidio",
    "asesinato": "homicidio",
    "asesinatos": "homicidio",
    "asociaciones_ilicitas": "asociacion_ilicita",
    "trafico_de_estupefacientes": "trafico_de_drogas",
    "narcotrafico": "trafico_de_drogas",
    "lavado_de_dinero": "lavado_de_activos",
    "torturas": "tortura",
    "robos": "robo",
    "porte_de_armas": "porte_ilegal_de_arma",
    "porte_ilegal_de_armas": "porte_ilegal_de_arma",

    #organizaciones
    "tren_aragua": "tren_de_aragua",
    "el_tren_de_aragua": "tren_de_aragua",
    "policia_de_investigaciones": "pdi",
    "policia_de_investigaciones_de_chile": "pdi",
    "carabineros_de_chile": "carabineros",
    "ministerio_publico": "fiscalia",
    "fiscalia_de_chile": "fiscalia",
}

#AGRUPACION: decision nuestra. Junta conceptos que NO son lo mismo, para que
#el grafo no se fragmente. Va documentado en el informe, seccion de
#preparacion de datos, porque cambia lo que el resultado afirma.
AGRUPACIONES = {
    "conspiracion": "asociacion_ilicita",   #figuras penales distintas
    "microtrafico": "trafico_de_drogas",    #Ley 20.000 art. 4 vs art. 3
    "arma": "arma_de_fuego",                #asume que el arma es de fuego
    "armas": "arma_de_fuego",
    "auto": "vehiculo",
    "autos": "vehiculo",
    "automovil": "vehiculo",
    "automoviles": "vehiculo",
    "camioneta": "vehiculo",
}

#Categorias amplias para el ANALISIS, no para el vault.
#(categoria, palabras clave) evaluadas EN ORDEN: gana la primera que calce.
#El orden es una decision: "doble secuestro con homicidio" cae en homicidio
#porque la regla de homicidio va antes que la de secuestro.
CATEGORIAS_DELITO = [
    ("terrorismo",            ("terrorista", "terrorismo", "artefacto_explosivo")),
    ("homicidio",             ("homicidio", "asesinat", "descuartiza", "inhumacion")),
    ("secuestro",             ("secuestro", "sustraccion_de_menores")),
    ("trata_de_personas",     ("trata", "prostitucion", "trafico_de_personas",
                               "trabajos_forzados")),
    ("trafico_de_drogas",     ("droga", "narcotrafico", "estupefaciente", "precursores")),
    ("trafico_de_armas",      ("trafico_transnacional_de_armas", "trafico_de_armas",
                               "receptacion_de_armas")),
    ("porte_ilegal_de_armas", ("porte", "tenencia", "ley_de_armas", "control_de_armas")),
    ("extorsion",             ("extorsion", "amedrentamiento", "obstruccion_de_la_libertad")),
    ("asociacion_ilicita",    ("asociacion", "crimen_organizado", "conspiracion")),
    ("lavado_de_activos",     ("lavado",)),
    ("robo",                  ("robo", "hurto", "receptacion", "apropiacion")),
    ("estafa",                ("estafa", "falsificacion", "contrabando")),
    ("amenazas",              ("amenaza",)),
    ("tortura",               ("tortura",)),
    ("agresion_sexual",       ("agresion_sexual", "violencia_intrafamiliar")),
]


def slugify(text: str) -> str:
    """'Tráfico de drogas' → 'Trafico_de_drogas'. Nunca vacío."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text)
    text = text.strip("_")
    return text or "sin_nombre"


def normalizar_entidad(nombre: str) -> str:
    """Slug canónico de una entidad. Devuelve "" si hay que omitirla del grafo.

    Aplica, en este orden: slug en minúscula, limpieza de variantes y
    agrupación. El orden importa: las claves de AGRUPACIONES suponen que el
    nombre ya viene normalizado por VARIANTES.
    """
    if not nombre:
        return ""

    clave = slugify(nombre).lower()
    if clave in ENTIDADES_IGNORADAS:
        return ""

    clave = VARIANTES.get(clave, clave)
    clave = AGRUPACIONES.get(clave, clave)

    #una variante puede terminar en algo que igual queremos descartar
    if clave in ENTIDADES_IGNORADAS:
        return ""
    return clave


def categoria_delito(nombre: str) -> str:
    """Agrupa un delito en una categoría amplia, para los gráficos del EDA.

    No se usa en el vault: ahí cada delito conserva el nombre que dio la
    fuente. Devuelve 'otros' cuando ninguna regla calza.
    """
    clave = normalizar_entidad(nombre)
    if not clave:
        return ""
    for categoria, palabras in CATEGORIAS_DELITO:
        for palabra in palabras:
            if palabra in clave:
                return categoria
    return "otros"


def enlace_obsidian(nombre: str) -> str:
    """Devuelve un wiki-link [[nombre]] para el grafo de Obsidian."""
    return f"[[{nombre}]]"