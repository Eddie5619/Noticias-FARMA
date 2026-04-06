#!/usr/bin/env python3
"""
=============================================================================
PARQUE PHARMA — SISTEMA DE INTELIGENCIA DE MERCADO AUTOMATIZADO
main.py — Orquestador principal del pipeline semanal

USO:
  python main.py                        # genera todos los reportes
  python main.py --report bioavailability  # solo un reporte
  python main.py --days 14              # fuentes de los últimos 14 días
  python main.py --dry-run              # sin llamar a Claude (usa JSON mock)
  python main.py --save-json            # guarda el JSON de análisis

VARIABLES DE ENTORNO REQUERIDAS:
  ANTHROPIC_API_KEY=sk-ant-...

VARIABLES OPCIONALES:
  SENDGRID_API_KEY=...    (para envío de email automático)
  REPORT_RECIPIENTS=a@b.com,c@d.com
=============================================================================
"""

import os
import sys
import json
import logging
import argparse
import time
from datetime import datetime
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import (
    ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS,
    OUTPUT_DIR, LOG_DIR, REPORTS, ORGANIZATION_NAME
)
from fetchers.sources import collect_all_sources, format_sources_for_prompt
from analysis.intelligence import run_analysis
from pdf.generator import generate_pdf


# ── Logging setup ─────────────────────────────────────────────────────────────

def setup_logging(log_dir: str) -> None:
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

logger = logging.getLogger("pharma_intel.main")


# ── Mock para dry-run ─────────────────────────────────────────────────────────

MOCK_ANALYSIS = {
    "report_metadata": {
        "week": 14,
        "year": 2026,
        "date_generated": "6 de abril de 2026",
        "total_sources": 0,
        "data_quality": "baja",
        "data_quality_note": "Modo dry-run — sin datos reales",
    },
    "executive_summary": {
        "headline": "DRY-RUN: Este es un reporte de prueba sin datos reales de Claude API.",
        "top_signals": [
            {"signal":"Señal de prueba 1","importance":"ALTA","source":"Mock","action_for_pp":"Acción de prueba"},
            {"signal":"Señal de prueba 2","importance":"MEDIA","source":"Mock","action_for_pp":"Monitorear"},
        ],
        "week_assessment": "Reporte generado en modo dry-run para validar el pipeline sin consumir tokens de API.",
    },
    "sections": [
        {
            "title": "Sección de Prueba",
            "key_findings": [
                {"finding":"Hallazgo de prueba","evidence":"Evidencia mock","source_url":"https://example.com","maturity":"investigacion"}
            ],
            "market_implication": "Implicación de mercado de prueba.",
            "parque_pharma_relevance": "Relevancia de prueba para Parque Pharma.",
            "alert_level": "BAJA",
        }
    ],
    "competitive_intelligence": {"key_players_news":[{"company":"TestCo","news":"Test","relevance":"Test"}],"market_gaps":["Gap de prueba"]},
    "regulatory_radar": {"fda_updates":["FDA update de prueba"],"ema_updates":[],"cofepris_notes":"Sin novedades","upcoming_deadlines":[]},
    "strategic_recommendations": [
        {"priority":1,"recommendation":"Validar el pipeline completo","rationale":"Dry-run exitoso","time_horizon":"inmediata","resource_implication":"Mínimo"}
    ],
    "sources_used": [{"title":"Fuente mock","source":"DryRun","url":"https://example.com","relevance":"Prueba del sistema"}],
    "next_week_watchlist": ["Verificar que el pipeline corre en producción","Configurar GitHub Actions"],
}


# ── Email distribuidor (opcional) ─────────────────────────────────────────────

def send_email_with_pdf(pdf_paths: list, report_configs: list) -> None:
    """Envía los PDFs por email via SendGrid (si está configurado)."""
    import os
    api_key    = os.getenv("SENDGRID_API_KEY","")
    recipients = os.getenv("REPORT_RECIPIENTS","").split(",")
    sender     = os.getenv("REPORT_SENDER","no-reply@parquepharma.mx")

    if not api_key or not recipients or not recipients[0]:
        logger.info("Email no configurado (SENDGRID_API_KEY / REPORT_RECIPIENTS no definidos) — omitiendo")
        return

    try:
        import base64
        import urllib.request, urllib.parse
        import json as _json

        now  = datetime.now()
        week = now.isocalendar()[1]
        attachments = []
        for pdf_path in pdf_paths:
            with open(pdf_path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf-8")
            attachments.append({
                "content":    content,
                "type":       "application/pdf",
                "filename":   os.path.basename(pdf_path),
                "disposition":"attachment",
            })

        payload = {
            "personalizations": [{"to":[{"email":r.strip()} for r in recipients if r.strip()]}],
            "from":    {"email": sender, "name": "Inteligencia de Mercado — Parque Pharma"},
            "subject": f"📊 Reportes IM Pharma — Semana {week} / {now.year}",
            "content": [{"type":"text/plain",
                         "value": f"Adjuntos: {len(pdf_paths)} reportes de inteligencia de mercado.\n\nParque Pharma / NAVETA"}],
            "attachments": attachments,
        }

        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data    = _json.dumps(payload).encode("utf-8"),
            headers = {"Content-Type":"application/json","Authorization":f"Bearer {api_key}"},
            method  = "POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            logger.info(f"Email enviado a {recipients} — status {resp.status}")

    except Exception as e:
        logger.warning(f"Error enviando email: {e}")


# ── Runner principal ──────────────────────────────────────────────────────────

class PipelineResult:
    def __init__(self):
        self.pdfs_generated = []
        self.errors         = []
        self.start_time     = datetime.now()

    @property
    def elapsed(self):
        return (datetime.now() - self.start_time).total_seconds()

    def summary(self):
        return (
            f"\n{'='*60}\n"
            f"PIPELINE COMPLETADO — {ORGANIZATION_NAME}\n"
            f"{'='*60}\n"
            f"PDFs generados: {len(self.pdfs_generated)}\n"
            f"Errores:        {len(self.errors)}\n"
            f"Tiempo total:   {self.elapsed:.1f}s\n"
            f"\nArchivos:\n" +
            "\n".join(f"  ✓ {p}" for p in self.pdfs_generated) +
            ("\n\nErrores:\n" + "\n".join(f"  ✗ {e}" for e in self.errors) if self.errors else "") +
            f"\n{'='*60}"
        )


def run_pipeline(
    report_ids: list = None,
    days_back: int   = 7,
    dry_run: bool    = False,
    save_json: bool  = False,
) -> PipelineResult:

    result = PipelineResult()

    # Filtrar reportes si se especificó uno
    configs = [r for r in REPORTS if not report_ids or r.report_id in report_ids]
    if not configs:
        logger.error(f"No se encontraron reportes para IDs: {report_ids}")
        result.errors.append("Sin reportes configurados")
        return result

    # Validar API key
    if not dry_run and not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY no configurada. Usar --dry-run o configurar la variable.")
        result.errors.append("API key faltante")
        return result

    logger.info(f"{'='*50}")
    logger.info(f"INICIANDO PIPELINE — {ORGANIZATION_NAME}")
    logger.info(f"Reportes: {[c.report_id for c in configs]}")
    logger.info(f"Período: últimos {days_back} días | Dry-run: {dry_run}")
    logger.info(f"{'='*50}")

    for config in configs:
        try:
            logger.info(f"\n--- PROCESANDO: {config.report_id} ---")

            # Paso 1: Recolección de fuentes
            if dry_run:
                logger.info("DRY-RUN: omitiendo fetch de fuentes")
                sources      = {"pubmed":[], "fda":[], "rss":[]}
                sources_text = "DRY-RUN: sin fuentes reales"
                sources_count = 0
            else:
                logger.info("Paso 1/3: Recolectando fuentes...")
                sources       = collect_all_sources(config, days_back=days_back)
                sources_text  = format_sources_for_prompt(sources)
                sources_count = sum(len(v) for v in sources.values())
                logger.info(f"  → {sources_count} fuentes recolectadas")

            # Paso 2: Análisis con Claude
            logger.info("Paso 2/3: Ejecutando análisis con Claude...")
            if dry_run:
                from analysis.intelligence import AnalysisResult
                now  = datetime.now()
                analysis = AnalysisResult(
                    config_id     = config.report_id,
                    raw_json      = json.dumps(MOCK_ANALYSIS),
                    parsed        = MOCK_ANALYSIS,
                    week          = now.isocalendar()[1],
                    year          = now.year,
                    sources_count = 0,
                )
            else:
                analysis = run_analysis(
                    config        = config,
                    sources_text  = sources_text,
                    sources_count = sources_count,
                    api_key       = ANTHROPIC_API_KEY,
                    model         = CLAUDE_MODEL,
                    max_tokens    = CLAUDE_MAX_TOKENS,
                )
            logger.info(f"  → Análisis completo: {len(analysis.parsed.get('sections',[]))} secciones")

            # Guardar JSON si se solicitó
            if save_json:
                json_path = os.path.join(
                    OUTPUT_DIR,
                    f"{config.filename_prefix}_Sem{analysis.week:02d}_{analysis.year}.json"
                )
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(analysis.parsed, f, ensure_ascii=False, indent=2)
                logger.info(f"  → JSON guardado: {json_path}")

            # Paso 3: Generación del PDF
            logger.info("Paso 3/3: Generando PDF...")
            pdf_path = generate_pdf(analysis, config, OUTPUT_DIR)
            result.pdfs_generated.append(pdf_path)
            logger.info(f"  → PDF: {pdf_path}")

            # Pequeña pausa entre reportes
            if len(configs) > 1:
                time.sleep(2)

        except Exception as e:
            logger.error(f"Error en [{config.report_id}]: {e}", exc_info=True)
            result.errors.append(f"{config.report_id}: {e}")

    # Envío por email (si está configurado)
    if result.pdfs_generated and not dry_run:
        send_email_with_pdf(result.pdfs_generated, configs)

    logger.info(result.summary())
    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Parque Pharma — Sistema de Inteligencia de Mercado Automatizado",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py                              # todos los reportes
  python main.py --report bioavailability     # solo biodisponibilidad
  python main.py --report cleanroom_rental    # solo cleanroom
  python main.py --days 14                    # fuentes de 14 días
  python main.py --dry-run                    # sin API, para testear PDF
  python main.py --dry-run --save-json        # también guarda el JSON
        """
    )
    parser.add_argument(
        "--report", nargs="*",
        help="IDs de reportes a generar (default: todos). Opciones: bioavailability, cleanroom_rental"
    )
    parser.add_argument("--days", type=int, default=7, help="Días hacia atrás para buscar fuentes (default: 7)")
    parser.add_argument("--dry-run", action="store_true", help="Omite Claude API y usa datos mock")
    parser.add_argument("--save-json", action="store_true", help="Guarda el JSON de análisis")
    parser.add_argument("--log-dir", default=LOG_DIR, help="Directorio de logs")

    args = parser.parse_args()

    setup_logging(args.log_dir)
    logger.info(f"Python {sys.version} | Args: {vars(args)}")

    result = run_pipeline(
        report_ids = args.report,
        days_back  = args.days,
        dry_run    = args.dry_run,
        save_json  = args.save_json,
    )

    sys.exit(0 if not result.errors else 1)


if __name__ == "__main__":
    main()
