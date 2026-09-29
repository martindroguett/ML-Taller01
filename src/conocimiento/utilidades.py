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

CATEGORIAS_ROL = [
    ("victima",     ("victima", "afectad", "damnificad")),
    ("policia",     ("policia", "carabiner", "pdi", "prefecto", "comisario",
                     "coronel")),
    ("fiscal",      ("fiscal",)),
    ("juez",        ("juez", "magistrad")),
    ("abogado",     ("abogad", "defensor")),
    ("autoridad",   ("ministr", "subsecretari", "alcalde", "delegad",
                     "presidente", "senador", "diputad", "gobernador")),
    ("condenado",   ("condenad",)),
    ("absuelto",    ("absuelt",)),
    ("imputado",    ("imputad", "acusad", "formalizad")),
    ("detenido",    ("detenid", "aprehendid", "capturad", "arrestad")),
    ("profugo",     ("profug",)),
    ("abatido",     ("abatid",)),
    ("denunciante", ("denunciante", "querellante")),
    ("testigo",     ("testigo",)),
    ("lider",       ("lider", "cabecilla")),
    ("integrante",  ("integrante", "miembro", "delincuente", "sicario",
                     "reclutador", "captor", "secuestrador")),
]


def categoria_rol(rol: str) -> str:
    """Agrupa el rol de una persona en una categoría amplia.

    Devuelve "" si la noticia no trae rol: es preferible no crear la nota
    antes que inventar un nodo 'desconocido' que conectaría entre sí a
    personas que no tienen nada que ver.
    """
    if not rol:
        return ""
    clave = slugify(rol).lower()
    if "desconocid" in clave:
        return ""
    for categoria, palabras in CATEGORIAS_ROL:
        for palabra in palabras:
            if palabra in clave:
                return categoria
    return "otro_rol"

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

#Tipos de relacion. Mismo patron que CATEGORIAS_DELITO: gana la primera
#que calce, asi que el ORDEN es una decision. Tres trampas resueltas por
#el orden: "lidera investigacion en conjunto con" tiene "lider" pero es
#una investigacion; "fiscal jefe de" tiene "jefe" pero es un cargo; y
#"condenado por" va antes que "acusado de" porque una condena no es
#una acusacion.
CATEGORIAS_RELACION = [
    ("investiga",     ("investig", "desbarat", "instruyo")),
    ("condenado_por", ("conden",)),
    ("acusado_de",    ("formaliz", "acusad", "imputad", "prision_preventiva")),
    ("detenido_en",   ("detuv", "detenid", "capturad", "recluid", "aprehend")),
    ("victima_de",    ("victima", "captor", "secuestr", "asesin", "homicidio",
                       "crimen_de")),
    ("representa_a",  ("abogad", "defensor", "patrocinante", "querell")),
    ("familiar_de",   ("primo", "prima", "hermano", "hermana", "pareja",
                       "conyuge", "hijo", "hija", "padre", "madre")),
    ("cargo_en",      ("fiscal", "alcalde", "prefecto", "comisario", "magistrad",
                       "director", "ejecutiv", "jefe", "ministr", "coronel")),
    ("lidera",        ("lider", "cabecilla")),
    ("integra",       ("miembro", "pertenece", "integra", "forma_parte", "faccion",
                       "celula", "brazo", "unidad", "socio")),
    ("ocurrio_en",    ("ocurrid", "sector", "interseccion", "provenient", "ubicad")),
    ("vinculado_a",   ("vinculad", "relacionad", "negoci", "contrat", "suscribi",
                       "participo", "denunci", "conjunt")),
]


def categoria_relacion(tipo: str) -> str:
    """Agrupa un tipo de relación en una categoría amplia.

    Con 57 noticias Gemini produjo 84 frases distintas, casi una por
    relación. Un grafo con 84 tipos de arista no se puede leer; la frase
    original se conserva como texto en la nota de la noticia.
    """
    if not tipo:
        return "se_relaciona_con"
    clave = slugify(tipo).lower()
    for categoria, palabras in CATEGORIAS_RELACION:
        for palabra in palabras:
            if palabra in clave:
                return categoria
    return "se_relaciona_con"

#Objetos incautados. Un objeto es una CLASE de cosa, no un nombre propio,
#asi que agrupar es legitimo: "celulares iPhone" y "teléfono celular con
#SIM card" son la misma clase de evidencia.
#Trampas resueltas por el orden: "auto bomba" tiene "auto" pero es un
#explosivo, asi que explosivo va antes que vehiculo; y "dispositivos
#utilizados para procesar pagos electronicos" tiene "pago" pero es
#tecnologia, asi que tecnologia va antes que dinero.
CATEGORIAS_OBJETO = [
    ("explosivo",      ("explosiv", "bomba", "fuegos_artificiales", "plasticina",
                        "detonante", "dinamita")),
    ("droga",          ("droga", "marihuana", "ketamina", "cocaina", "mdma",
                        "metanfetamina", "estupefacient", "farmac", "clorhidrato",
                        "impregnada", "comprimidos")),
    ("arma_de_fuego",  ("arma", "pistola", "armamento", "fusil", "escopeta",
                        "revolver")),
    ("municion",       ("municion", "cargador", "calibre")),
    ("arma_blanca",    ("cuchillo", "machete", "arma_blanca")),
    ("tecnologia",     ("telefono", "celular", "iphone", "computador", "ipad",
                        "pendrive", "dispositivo", "tecnolog", "starlink",
                        "fibra_optica", "antena", "sim_card", "equipos")),
    ("documento",      ("documento", "pasaporte", "cedula", "contable",
                        "contrato", "papeles", "registro")),
    ("dinero",         ("peso", "dinero", "dolar", "millon", "criptomoneda",
                        "vale_vista", "rescate", "efectivo", "pago")),
    ("vehiculo",       ("vehiculo", "camioneta", "automovil", "motociclet",
                        "furgon", "kia", "chevrolet", "hyundai", "renault",
                        "auto")),
    ("joya",           ("cadena", "cordon", "plata", "joya", "reloj")),
    ("restos_humanos", ("restos_humanos", "cadaver", "osamenta")),
]


def categoria_objeto(nombre: str) -> str:
    """Agrupa un objeto incautado en una categoría amplia.

    Devuelve 'otros_objetos' cuando la frase no dice qué es la cosa
    ("diversas especies", "elementos que estaban en el piso").
    """
    if not nombre:
        return ""
    clave = slugify(nombre).lower()
    for categoria, palabras in CATEGORIAS_OBJETO:
        for palabra in palabras:
            if palabra in clave:
                return categoria
    return "otros_objetos"

#ORGANIZACIONES. Aca NO se agrupa por categoria: "Tren de Aragua" y
#"Los Gallegos" tienen que seguir siendo nodos distintos, o el grafo deja
#de poder responder que banda opera donde. Lo que se junta son las
#OFICINAS de una misma institucion, que venian fragmentadas por region:
#habia 20 variantes de Fiscalia y 15 de PDI, cada una como nodo suelto.
ORGS_IGNORADAS = {
    "gobierno", "tribunal", "juzgado_de_garantia", "red_de_narcotrafico",
    "tribunal_de_juicio_oral_en_lo_penal", "corte_de_apelaciones",
    "policia_nacional", "yahoo", "google", "tiktok",
}

#medios de prensa: son la FUENTE de la noticia, no un actor del caso.
#Aparecen como organizacion solo porque Gemini leyo el credito del articulo.
MEDIOS = ("bio_bio", "biobio", "bbcl", "adn_hoy", "24_horas",
          "noticias_caracol", "agenciauno")

#instituciones extranjeras que la regla chilena se llevaria por error
EXTRANJERAS = {
    "fiscalia_general_de_la_nacion": "fiscalia_general_de_colombia",
    "fuerzas_armadas_de_la_federacion_rusa": "fuerzas_armadas_de_rusia",
}

INSTITUCIONES = [
    ("ministerio_publico", ("fiscalia", "ministerio_publico", "ecoh", "eaco",
                            "sac_", "sistema_de_analisis",
                            "unidad_de_crimen_organizado",
                            "unidad_de_inteligencia", "agrupacion_investigadora")),
    ("carabineros",        ("carabiner", "os7", "os9", "comisaria")),
    ("pdi",                ("policia_de_investigaciones", "pdi", "bipe", "brigada",
                            "bicrim", "prefectura", "criminalistica",
                            "asuntos_internos", "departamento_v")),
    ("poder_judicial",     ("juzgado", "tribunal", "corte")),
    ("gendarmeria",        ("gendarmeria",)),
    ("aduanas_chile",      ("servicio_nacional_de_aduanas",)),
    ("armada_de_chile",    ("armada_de_chile", "directemar", "policia_maritima")),
    ("cancilleria",        ("cancilleria",)),
    ("interpol",           ("interpol",)),
]

VARIANTES_ORG = {
    "aduanas": "aduanas_chile",
    "mafia_hong_men": "mafia_hongmen",
    "los_piratas_de_aragua": "los_piratas",
    "epanda": "change_panda_spa",
    "policia_de_peru": "policia_nacional_peruana",
}


def categoria_organizacion(nombre: str) -> str:
    """Nombre canónico de una organización. Devuelve "" si hay que omitirla."""
    if not nombre:
        return ""
    clave = slugify(nombre).lower()
    if clave in ORGS_IGNORADAS:
        return ""
    if any(medio in clave for medio in MEDIOS):
        return ""
    if clave in EXTRANJERAS:
        return EXTRANJERAS[clave]
    for institucion, palabras in INSTITUCIONES:
        for palabra in palabras:
            if palabra in clave:
                return institucion
    return VARIANTES_ORG.get(clave, clave)