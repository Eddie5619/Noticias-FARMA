"""
=============================================================================
analysis/intelligence.py — Motor de análisis con Claude API
Incluye templates de prompts para analista de inteligencia de mercado pharma
=============================================================================
"""

import json
import logging
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("pharma_intel.analysis")


# ════════════════════════════════════════════════════════════════════════════
#  TEMPLATES DE PROMPTS
# ════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Eres un analista senior de inteligencia de mercado farmacéutico con 20 años de experiencia 
en formulación de APIs, modelos de negocio CDMO, regulatorio FDA/EMA/COFEPRIS y estrategia de negocios pharma.

Tu función es generar reportes de inteligencia de mercado semanales para Parque Pharma® / NAVETA, 
una empresa de manufactura farmacéutica GMP en Toluca, México con hubs de Biotecnología, ATMP y Fitomedicina.

PRINCIPIOS ANALÍTICOS OBLIGATORIOS:
1. Basas TODA conclusión en las fuentes proporcionadas — no inventas datos, citas o estadísticas
2. Cuando una fuente respalda una afirmación, la mencionas explícitamente (nombre + URL)
3. Distingues entre evidencia sólida (Fase II/III, aprobación regulatoria) y señales tempranas (preclinical, research)
4. Identificas implicaciones estratégicas ESPECÍFICAS para Parque Pharma, no genéricas
5. Cuantificas cuando los datos lo permiten (%, USD, plazos, tamaños de mercado)
6. Eres honesto cuando la semana tiene pocas novedades — no rellenas con contenido genérico
7. Usas lenguaje ejecutivo técnico, no periodístico ni de marketing

FORMATO DE RESPUESTA:
Respondes ÚNICAMENTE con un objeto JSON válido según el schema especificado.
No incluyes texto antes ni después del JSON.
No incluyes bloques ```json``` — solo el JSON puro."""


def build_analysis_prompt(config, sources_text: str, week_number: int, year: int) -> str:
    """Construye el prompt de usuario para el análisis semanal."""

    sections_formatted = "\n".join(
        f"  {i+1}. {sec}" for i, sec in enumerate(config.sections)
    )

    return f"""Genera el reporte de inteligencia de mercado SEMANA {week_number} / {year} 
para el tema: "{config.title}"

CONTEXTO ESTRATÉGICO DE PARQUE PHARMA:
{config.strategic_context.strip()}

FUENTES RECOLECTADAS ESTA SEMANA:
{sources_text}

SECCIONES REQUERIDAS:
{sections_formatted}

INSTRUCCIONES DE ANÁLISIS:
- Si hay pocas fuentes nuevas esta semana, sé honesto y complementa con tendencias estructurales 
  del mercado que sean relevantes, siempre distinguiendo entre "novedad de la semana" y "tendencia de fondo"
- Para cada sección, incluye: hallazgos clave, implicación para el mercado, y relevancia específica 
  para Parque Pharma
- Las señales clave deben ser accionables: qué debe hacer o monitorear Parque Pharma en las próximas 
  2-4 semanas a raíz de lo encontrado
- El nivel de alerta puede ser: ALTA (acción inmediata), MEDIA (monitorear), BAJA (contexto)

Responde con este JSON exacto (sin texto adicional, sin ```json```):

{{
  "report_metadata": {{
    "week": {week_number},
    "year": {year},
    "date_generated": "{datetime.now().strftime('%d de %B de %Y')}",
    "total_sources": 0,
    "data_quality": "alta|media|baja",
    "data_quality_note": "explicación breve de calidad de fuentes esta semana"
  }},
  "executive_summary": {{
    "headline": "Una oración que capture la señal más importante de la semana",
    "top_signals": [
      {{
        "signal": "Descripción de la señal",
        "importance": "ALTA|MEDIA|BAJA",
        "source": "nombre de la fuente",
        "action_for_pp": "qué debe hacer Parque Pharma"
      }}
    ],
    "week_assessment": "Evaluación de la semana en 2-3 oraciones"
  }},
  "sections": [
    {{
      "title": "título de la sección",
      "key_findings": [
        {{
          "finding": "hallazgo específico",
          "evidence": "evidencia que lo respalda",
          "source_url": "URL si disponible",
          "maturity": "comercial|fase_III|fase_II|fase_I|preclinical|investigacion"
        }}
      ],
      "market_implication": "qué significa para el mercado en general",
      "parque_pharma_relevance": "implicación específica y accionable para Parque Pharma",
      "alert_level": "ALTA|MEDIA|BAJA"
    }}
  ],
  "competitive_intelligence": {{
    "key_players_news": [
      {{
        "company": "nombre",
        "news": "qué pasó",
        "relevance": "por qué importa a PP"
      }}
    ],
    "market_gaps": ["gap o oportunidad identificada"]
  }},
  "regulatory_radar": {{
    "fda_updates": [],
    "ema_updates": [],
    "cofepris_notes": "cualquier nota relevante para México",
    "upcoming_deadlines": []
  }},
  "strategic_recommendations": [
    {{
      "priority": 1,
      "recommendation": "acción específica recomendada",
      "rationale": "por qué ahora",
      "time_horizon": "inmediata|1-4_semanas|1-3_meses|6+_meses",
      "resource_implication": "qué recursos requiere"
    }}
  ],
  "sources_used": [
    {{
      "title": "título del artículo/noticia",
      "source": "nombre de la fuente",
      "url": "URL",
      "relevance": "por qué se incluyó"
    }}
  ],
  "next_week_watchlist": [
    "tema o evento a monitorear la próxima semana"
  ]
}}"""


# ════════════════════════════════════════════════════════════════════════════
#  CLIENTE CLAUDE API
# ════════════════════════════════════════════════════════════════════════════

class ClaudeClient:
    """Cliente minimalista para la API de Anthropic (sin dependencia de SDK)."""

    BASE_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self, api_key: str, model: str, max_tokens: int = 8000):
        self.api_key    = api_key
        self.model      = model
        self.max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        """Llama a la API y retorna el texto de la respuesta."""
        payload = json.dumps({
            "model":      self.model,
            "max_tokens": self.max_tokens,
            "system":     system,
            "messages":   [{"role": "user", "content": user}],
        }).encode("utf-8")

        req = urllib.request.Request(
            self.BASE_URL,
            data    = payload,
            headers = {
                "Content-Type":      "application/json",
                "x-api-key":         self.api_key,
                "anthropic-version": self.API_VERSION,
            },
            method = "POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return data["content"][0]["text"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"Claude API HTTP error {e.code}: {error_body[:300]}")
            raise
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise


# ════════════════════════════════════════════════════════════════════════════
#  MOTOR DE ANÁLISIS
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class AnalysisResult:
    config_id:   str
    raw_json:    str
    parsed:      dict
    week:        int
    year:        int
    sources_count: int


def run_analysis(
    config,
    sources_text: str,
    sources_count: int,
    api_key: str,
    model: str,
    max_tokens: int,
) -> AnalysisResult:
    """
    Ejecuta el análisis de inteligencia de mercado para un ReportConfig.
    Retorna AnalysisResult con el JSON parseado listo para el PDF.
    """
    now  = datetime.now()
    week = now.isocalendar()[1]
    year = now.year

    logger.info(f"Iniciando análisis [{config.report_id}] con Claude ({model})...")

    client = ClaudeClient(api_key=api_key, model=model, max_tokens=max_tokens)
    user_prompt = build_analysis_prompt(config, sources_text, week, year)

    raw_response = client.complete(system=SYSTEM_PROMPT, user=user_prompt)
    logger.info(f"Claude respondió {len(raw_response)} caracteres")

    # Limpiar posibles bloques ```json``` si Claude los incluyó
    clean = raw_response.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1]
    if clean.endswith("```"):
        clean = clean.rsplit("```", 1)[0]
    clean = clean.strip()

    try:
        parsed = json.loads(clean)
        # Actualizar total_sources con el valor real
        parsed["report_metadata"]["total_sources"] = sources_count
        logger.info(f"JSON parseado correctamente — {len(parsed.get('sections',[]))} secciones")
    except json.JSONDecodeError as e:
        logger.error(f"Error parseando JSON de Claude: {e}")
        logger.debug(f"Raw response: {clean[:500]}")
        # Fallback: estructura mínima de error
        parsed = _error_fallback(config, week, year, str(e), clean)

    return AnalysisResult(
        config_id     = config.report_id,
        raw_json      = clean,
        parsed        = parsed,
        week          = week,
        year          = year,
        sources_count = sources_count,
    )


def _error_fallback(config, week: int, year: int, error: str, raw: str) -> dict:
    """Estructura mínima cuando el JSON de Claude no parsea."""
    return {
        "report_metadata": {
            "week": week,
            "year": year,
            "date_generated": datetime.now().strftime("%d de %B de %Y"),
            "total_sources": 0,
            "data_quality": "baja",
            "data_quality_note": f"Error de parseo: {error}",
        },
        "executive_summary": {
            "headline": "Error en generación automática — revisar logs",
            "top_signals": [],
            "week_assessment": raw[:500],
        },
        "sections": [],
        "competitive_intelligence": {"key_players_news": [], "market_gaps": []},
        "regulatory_radar": {"fda_updates": [], "ema_updates": [], "cofepris_notes": "", "upcoming_deadlines": []},
        "strategic_recommendations": [],
        "sources_used": [],
        "next_week_watchlist": [],
    }
