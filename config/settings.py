"""
=============================================================================
PARQUE PHARMA — SISTEMA DE INTELIGENCIA DE MERCADO AUTOMATIZADO
config/settings.py — Configuración central
=============================================================================
"""

import os
from dataclasses import dataclass, field
from typing import List

# ── API Keys (desde variables de entorno) ────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SENDGRID_API_KEY  = os.getenv("SENDGRID_API_KEY", "")   # opcional — para email
FEEDLY_TOKEN      = os.getenv("FEEDLY_TOKEN", "")        # opcional

# ── Modelo Claude ─────────────────────────────────────────────────────────────
CLAUDE_MODEL      = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 8000

# ── Configuración del sistema de inteligencia ─────────────────────────────────
ORGANIZATION_NAME = "Parque Pharma® / NAVETA"
REPORT_LANGUAGE   = "es"          # "es" | "en"
OUTPUT_DIR        = os.path.join(os.path.dirname(__file__), "..", "output")
LOG_DIR           = os.path.join(os.path.dirname(__file__), "..", "logs")

# ── Paleta visual (RGB normalizado para ReportLab) ────────────────────────────
PALETTE = {
    "navy":  "#0B1F3A",
    "teal":  "#0D7B75",
    "amber": "#D4A017",
    "lgray": "#F4F6F8",
    "mgray": "#D1D5DB",
    "green": "#1A7A4A",
    "red":   "#C0392B",
    "purple":"#5B2D8E",
    "blue":  "#1A5276",
}

# ── Definición de reportes ─────────────────────────────────────────────────────
@dataclass
class ReportConfig:
    report_id:        str
    title:            str
    subtitle:         str
    accent_color:     str            # hex color del reporte
    pubmed_queries:   List[str]      # queries para PubMed
    fda_categories:   List[str]      # categorías FDA RSS: "drugs", "biologics", "devices"
    rss_feeds:        List[str]      # URLs de feeds RSS adicionales
    sections:         List[str]      # nombres de secciones del análisis
    strategic_context: str           # contexto específico para el prompt de Claude
    filename_prefix:  str


REPORTS = [
    ReportConfig(
        report_id        = "bioavailability",
        title            = "TECNOLOGÍAS DE VANGUARDIA PARA BIODISPONIBILIDAD",
        subtitle         = "Mejora sustancial de APIs — Análisis semanal de ciencia, mercado y regulatorio",
        accent_color     = "#0D7B75",
        pubmed_queries   = [
            "bioavailability enhancement drug delivery nanoparticles 2025 2026",
            "amorphous solid dispersion hot melt extrusion API solubility",
            "lipid nanoparticle ionizable oral drug delivery clinical",
            "nanosuspension nanocrystal BCS class II IV formulation",
            "self-emulsifying drug delivery SEDDS SNEDDS bioavailability",
            "extracellular vesicles exosomes drug delivery clinical trial",
            "co-amorphous co-crystal pharmaceutical bioavailability",
        ],
        fda_categories   = ["drugs", "biologics"],
        rss_feeds        = [
            "https://drug-dev.com/feed/",
            "https://www.pharmamanufacturing.com/rss/all",
            "https://www.fiercepharma.com/rss/xml",
        ],
        sections         = [
            "Resumen Ejecutivo y Señales Clave de la Semana",
            "Novedades en Dispersiones Sólidas Amorfas (ASD) y HME",
            "Avances en Nanopartículas Lipídicas (LNP) y Vesículas Extracelulares",
            "Nanocristales, SEDDS y Plataformas Emergentes",
            "Co-amorfos, Co-cristales y Estrategias de Lifecycle Management",
            "Movimientos Regulatorios FDA/EMA/COFEPRIS",
            "Implicaciones Estratégicas para Parque Pharma",
        ],
        strategic_context = """
Parque Pharma® es un parque de manufactura farmacéutica GMP en Toluca, México, 
con tres hubs especializados: Biotecnología GMP, ATMP (terapias avanzadas), y 
Fitomedicina. La empresa tiene particular interés en:
- Tecnologías de biodisponibilidad aplicables a fitomedicina (múltiples principios activos, 
  BCS II/IV de origen vegetal)
- LNP y plataformas de entrega avanzadas para su hub de ATMP
- Oportunidades de IP mediante co-amorfos y co-cristales para productos propios
- Tecnologías que puedan ofrecerse como servicio a clientes externos del parque
""",
        filename_prefix  = "IM_Bioavailabilidad",
    ),

    ReportConfig(
        report_id        = "cleanroom_rental",
        title            = "CUARTOS LIMPIOS EN RENTA — AMÉRICAS",
        subtitle         = "Modelos de negocio GMP Full Service · Oportunidades y benchmarking",
        accent_color     = "#D4A017",
        pubmed_queries   = [],  # no PubMed para este reporte
        fda_categories   = ["drugs"],
        rss_feeds        = [
            "https://cleanroomtechnology.com/rss",
            "https://www.pharmamanufacturing.com/rss/all",
            "https://www.contractpharma.com/rss/news",
        ],
        sections         = [
            "Resumen Ejecutivo y Señales Clave de la Semana",
            "Movimientos de Mercado — CDMOs y Cleanroom Providers en Américas",
            "Modelos de Negocio COD (Cleanrooms On Demand) — Actualizaciones",
            "Regulatorio: FDA, COFEPRIS, Annex 1 EU — Novedades",
            "Oportunidades de Nearshoring Farmacéutico hacia México",
            "Benchmarking de Precios y Modelos Comerciales",
            "Implicaciones Estratégicas para Parque Pharma como COD Hub LATAM",
        ],
        strategic_context = """
Parque Pharma® está evaluando lanzar un modelo de 'Cuartos Limpios en Renta con 
Full Service GMP' (equivalente al modelo Cleanrooms On Demand de EUA) en Toluca, México.
La empresa tiene particular interés en:
- Benchmarking de modelos COD exitosos (Chrysalis, VALogic) y sus estructuras comerciales
- Oportunidades de nearshoring farmacéutico hacia México bajo USMCA/aranceles 2025-2026
- Regulatorio COFEPRIS + FDA dual-certification para posicionamiento internacional
- Modelos de contrato y pricing (take-or-pay, SLA, servicios à la carte)
- Nuevos actores y M&A en el segmento de cleanroom rental en las Américas
""",
        filename_prefix  = "IM_Cleanroom_Renta",
    ),
]
