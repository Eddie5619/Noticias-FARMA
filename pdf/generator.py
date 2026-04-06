"""
=============================================================================
pdf/generator.py — Generador de PDF a partir del JSON de análisis
Misma identidad visual que los reportes manuales de Parque Pharma
=============================================================================
"""

import os
import logging
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak, NextPageTemplate, KeepTogether
)

logger = logging.getLogger("pharma_intel.pdf")

W, H = A4

# ── Paleta base ───────────────────────────────────────────────────────────────
NAVY  = colors.HexColor("#0B1F3A")
TEAL  = colors.HexColor("#0D7B75")
AMBER = colors.HexColor("#D4A017")
LGRAY = colors.HexColor("#F4F6F8")
MGRAY = colors.HexColor("#D1D5DB")
WHITE = colors.white
GREEN = colors.HexColor("#1A7A4A")
RED   = colors.HexColor("#C0392B")
LRED  = colors.HexColor("#FEF2F2")
LGRN  = colors.HexColor("#EAF7EE")
LAMB  = colors.HexColor("#FFFBF0")

ALERT_COLORS = {
    "ALTA":  RED,
    "MEDIA": AMBER,
    "BAJA":  TEAL,
    "alta":  RED,
    "media": AMBER,
    "baja":  TEAL,
}

MATURITY_LABELS = {
    "comercial":    ("Comercial",   GREEN),
    "fase_III":     ("Fase III",    TEAL),
    "fase_II":      ("Fase II",     AMBER),
    "fase_I":       ("Fase I",      colors.HexColor("#E67E22")),
    "preclinical":  ("Preclinical", colors.HexColor("#8E44AD")),
    "investigacion":("Investigación",MGRAY),
}


# ── Helpers de estilo ─────────────────────────────────────────────────────────

def S(base="Normal", **kw):
    styles = getSampleStyleSheet()
    p = styles.get(base, styles["Normal"])
    return ParagraphStyle("_"+str(id(kw)), parent=p, **kw)

def hr(color=MGRAY, t=0.5):
    return HRFlowable(width="100%", thickness=t, color=color, spaceAfter=3, spaceBefore=3)

def sbar(text, bg=NAVY, txt_color=WHITE):
    t = Table([[Paragraph(text, S(fontName="Helvetica-Bold", fontSize=10,
                                   textColor=txt_color, leading=13))]],
              colWidths=[W-4*cm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),10)]))
    return t

def body(text):
    return Paragraph(text or "—", S(fontName="Helvetica", fontSize=9, textColor=NAVY,
                              leading=14, alignment=TA_JUSTIFY, spaceAfter=2))

def note(text):
    return Paragraph(text or "", S(fontName="Helvetica-Oblique", fontSize=8,
                              textColor=colors.HexColor("#555"), leading=12, spaceAfter=2))

def box(paras, bg=LGRAY, border=TEAL):
    t = Table([[paras]], colWidths=[W-4*cm-16])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),bg),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
        ("LINEBEFORE",(0,0),(0,-1),3,border),
    ]))
    return t

def badge(text, bg=TEAL):
    t = Table([[Paragraph(text, S(fontName="Helvetica-Bold", fontSize=7.5,
                                   textColor=WHITE, leading=10, alignment=TA_CENTER))]],
              colWidths=[30*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),bg),
        ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
    ]))
    return t

def tbl(headers, rows, widths, hbg=NAVY, extras=None):
    data = [[Paragraph(h, S(fontName="Helvetica-Bold", fontSize=8, textColor=WHITE, leading=11))
             for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c or "—"), S(fontName="Helvetica", fontSize=8,
                                                  textColor=NAVY, leading=11)) for c in row])
    t = Table(data, colWidths=widths)
    base = [
        ("BACKGROUND",(0,0),(-1,0),hbg),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LGRAY]),
        ("GRID",(0,0),(-1,-1),0.4,MGRAY),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
    ]
    if extras: base.extend(extras)
    t.setStyle(TableStyle(base))
    return t


# ── Cover y page callbacks ─────────────────────────────────────────────────────

def make_cover_callback(analysis, config):
    """Genera la función de callback de la portada."""
    accent = colors.HexColor(config.accent_color)

    def draw_cover(canvas, doc):
        c = canvas; c.saveState()
        c.setFillColor(NAVY); c.rect(0,0,W,H,fill=1,stroke=0)
        c.setFillColor(accent); c.rect(0,H-16*mm,W,16*mm,fill=1,stroke=0)
        c.setFillColor(AMBER); c.rect(0,H-18.5*mm,W,2.5*mm,fill=1,stroke=0)
        c.setFillColor(accent); c.rect(0,0,W,10*mm,fill=1,stroke=0)

        # Círculos decorativos
        c.setFillColor(colors.HexColor("#0F2C50"))
        c.circle(W-35*mm,H*0.5,60*mm,fill=1,stroke=0)
        c.setFillColor(colors.HexColor("#0D3560"))
        c.circle(W-18*mm,H*0.3,30*mm,fill=1,stroke=0)

        # Semana badge
        c.setFillColor(AMBER)
        c.roundRect(20*mm,H-58*mm,95*mm,10*mm,2*mm,fill=1,stroke=0)
        c.setFillColor(NAVY); c.setFont("Helvetica-Bold",8)
        meta = analysis.parsed.get("report_metadata", {})
        week = meta.get("week", analysis.week)
        year = meta.get("year", analysis.year)
        date_gen = meta.get("date_generated", "")
        c.drawString(24*mm,H-52*mm,
            f"INTELIGENCIA DE MERCADO PHARMA  ·  SEMANA {week}  ·  {str(year).upper()}")

        # Auto-generated badge
        c.setFillColor(accent); c.roundRect(20*mm,H-72*mm,55*mm,10*mm,2*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
        c.drawString(23*mm,H-65.5*mm,"⚡ GENERADO AUTOMÁTICAMENTE")

        # Título
        c.setFillColor(colors.HexColor("#A8C4D4")); c.setFont("Helvetica",9)
        c.drawString(20*mm,H-84*mm,"Parque Pharma® / NAVETA  ·  Sistema de Inteligencia de Mercado")

        title_words = config.title.split(" — ")
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",21)
        y_title = H-112*mm
        for word in title_words:
            c.drawString(20*mm, y_title, word)
            y_title -= 26*mm

        c.setStrokeColor(accent); c.setLineWidth(2)
        c.line(20*mm, y_title+10*mm, 130*mm, y_title+10*mm)
        c.setFillColor(colors.HexColor("#A8C4D4")); c.setFont("Helvetica",10)
        c.drawString(20*mm, y_title, config.subtitle)

        # KPIs desde el executive summary
        exec_sum = analysis.parsed.get("executive_summary", {})
        signals  = exec_sum.get("top_signals", [])
        headline = exec_sum.get("headline", "")

        # Headline box
        y_hl = H-230*mm
        c.setFillColor(colors.HexColor("#0F2C50"))
        c.roundRect(20*mm,y_hl,155*mm,22*mm,3*mm,fill=1,stroke=0)
        c.setFillColor(AMBER); c.setFont("Helvetica-Bold",8)
        c.drawString(26*mm,y_hl+14,"SEÑAL PRINCIPAL DE LA SEMANA")
        c.setFillColor(WHITE); c.setFont("Helvetica",8.5)
        # Truncar headline si es muy largo
        hl_text = headline[:120] + ("..." if len(headline) > 120 else "")
        c.drawString(26*mm,y_hl+4,hl_text)

        # Señales
        y_sig = H-268*mm
        c.setFillColor(colors.HexColor("#0F2C50"))
        c.roundRect(20*mm,y_sig,155*mm,28*mm,3*mm,fill=1,stroke=0)
        c.setFillColor(AMBER); c.setFont("Helvetica-Bold",8)
        c.drawString(26*mm,y_sig+20,"TOP SEÑALES")
        y_s = y_sig+10
        for s in signals[:3]:
            level = s.get("importance","MEDIA")
            color_map = {"ALTA":RED,"MEDIA":AMBER,"BAJA":TEAL}
            c.setFillColor(color_map.get(level,TEAL))
            c.setFont("Helvetica-Bold",7)
            c.drawString(26*mm,y_s,f"[{level}]")
            c.setFillColor(WHITE); c.setFont("Helvetica",7)
            signal_text = s.get("signal","")[:90]
            c.drawString(46*mm,y_s,signal_text)
            y_s -= 9

        # Métricas de calidad del reporte
        quality     = meta.get("data_quality","?")
        src_count   = meta.get("total_sources",0)
        sections_n  = len(analysis.parsed.get("sections",[]))
        recs_n      = len(analysis.parsed.get("strategic_recommendations",[]))

        y_m = H-318*mm
        metrics = [(str(src_count),"Fuentes","analizadas"),(str(sections_n),"Secciones","del análisis"),
                   (quality.upper(),"Calidad","de datos"),(str(recs_n),"Recomendaciones","estratégicas")]
        xp = [20*mm,60*mm,100*mm,140*mm]
        for i,(val,lab,sub) in enumerate(metrics):
            c.setFillColor(colors.HexColor("#0F2C50"))
            c.roundRect(xp[i],y_m,34*mm,24*mm,2*mm,fill=1,stroke=0)
            c.setFillColor(AMBER); c.setFont("Helvetica-Bold",14)
            c.drawString(xp[i]+4*mm,y_m+13,val)
            c.setFillColor(colors.HexColor("#A8C4D4")); c.setFont("Helvetica",7)
            c.drawString(xp[i]+4*mm,y_m+5,f"{lab}")
            c.drawString(xp[i]+4*mm,y_m-2,sub)

        c.setFillColor(colors.HexColor("#A8C4D4")); c.setFont("Helvetica",7)
        c.drawCentredString(W/2,4*mm,
            f"Generado automáticamente el {date_gen} · Sistema IM Parque Pharma / NAVETA · Confidencial")
        c.restoreState()

    return draw_cover


def make_content_callback(analysis, config):
    """Genera la función de callback para páginas de contenido."""
    PAGE_NUM = [0]
    accent = colors.HexColor(config.accent_color)

    def draw_content(canvas, doc):
        PAGE_NUM[0] += 1
        c = canvas; c.saveState()
        c.setFillColor(NAVY); c.rect(0,H-13*mm,W,13*mm,fill=1,stroke=0)
        c.setFillColor(accent); c.rect(0,H-14.5*mm,W,1.5*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7.5)
        week = analysis.parsed.get("report_metadata",{}).get("week", analysis.week)
        year = analysis.parsed.get("report_metadata",{}).get("year", analysis.year)
        c.drawString(2*cm,H-9*mm,
            f"IM PHARMA · {config.title[:50]} · SEMANA {week}/{year}")
        c.setFont("Helvetica",7.5)
        c.drawRightString(W-2*cm,H-9*mm,f"Parque Pharma / NAVETA · Pág. {PAGE_NUM[0]}")
        c.setFillColor(NAVY); c.rect(0,0,W,9*mm,fill=1,stroke=0)
        c.setFillColor(colors.HexColor("#A8C4D4")); c.setFont("Helvetica",6.5)
        c.drawCentredString(W/2,3.5*mm,
            "⚡ Generado automáticamente · Confidencial · Uso interno Parque Pharma / NAVETA")
        c.restoreState()

    return draw_content


# ── Builders de secciones ─────────────────────────────────────────────────────

def build_executive_summary(parsed: dict, accent) -> list:
    story = []
    story.append(Spacer(1,2*mm))
    story.append(sbar("1.  Resumen Ejecutivo y Señales Clave de la Semana", bg=NAVY))
    story.append(Spacer(1,3*mm))

    exec_sum = parsed.get("executive_summary", {})
    headline = exec_sum.get("headline", "")
    assessment = exec_sum.get("week_assessment", "")
    signals = exec_sum.get("top_signals", [])

    meta = parsed.get("report_metadata", {})
    q_note = meta.get("data_quality_note","")

    if headline:
        story.append(box([
            Paragraph("📡  Señal principal", S(fontName="Helvetica-Bold",
                fontSize=8.5, textColor=accent, leading=12)),
            Paragraph(headline, S(fontName="Helvetica-Bold", fontSize=10,
                textColor=NAVY, leading=14)),
        ], bg=LGRAY, border=accent))
        story.append(Spacer(1,3*mm))

    if assessment:
        story.append(body(assessment))
        story.append(Spacer(1,3*mm))

    if signals:
        story.append(Paragraph("Señales de la semana por nivel de importancia:",
            S(fontName="Helvetica-Bold", fontSize=9, textColor=NAVY, leading=13, spaceAfter=4)))
        for sig in signals:
            level  = sig.get("importance", "MEDIA").upper()
            color  = ALERT_COLORS.get(level, TEAL)
            action = sig.get("action_for_pp","")
            source = sig.get("source","")
            signal_text = sig.get("signal","")
            story.append(box([
                Paragraph(f"[{level}]  {signal_text}",
                    S(fontName="Helvetica-Bold", fontSize=8.5, textColor=color, leading=12)),
                Paragraph(f"<b>Acción Parque Pharma:</b> {action}",
                    S(fontName="Helvetica", fontSize=8.5, textColor=NAVY, leading=12)),
                Paragraph(f"Fuente: {source}",
                    S(fontName="Helvetica-Oblique", fontSize=8, textColor=colors.HexColor("#555"), leading=11)),
            ], bg=LRED if level=="ALTA" else (LAMB if level=="MEDIA" else LGRAY), border=color))
            story.append(Spacer(1,2*mm))

    if q_note:
        story.append(note(f"ℹ️  Nota de calidad de datos esta semana: {q_note}"))

    return story


def build_sections(parsed: dict, config, accent) -> list:
    story = []
    sections = parsed.get("sections", [])

    for i, sec in enumerate(sections, 2):
        title  = sec.get("title", f"Sección {i}")
        level  = sec.get("alert_level","BAJA").upper()
        color  = ALERT_COLORS.get(level, TEAL)
        market = sec.get("market_implication","")
        pp_rel = sec.get("parque_pharma_relevance","")
        findings = sec.get("key_findings", [])

        story.append(Spacer(1,4*mm))
        # Header de sección con nivel de alerta
        sec_header = f"{i}.  {title}  [Alerta: {level}]"
        story.append(sbar(sec_header, bg=color))
        story.append(Spacer(1,3*mm))

        if findings:
            for f in findings:
                finding_text = f.get("finding","")
                evidence     = f.get("evidence","")
                src_url      = f.get("source_url","")
                maturity_key = f.get("maturity","investigacion")
                mat_label, mat_color = MATURITY_LABELS.get(maturity_key, ("?", MGRAY))

                inner = [
                    Paragraph(f"• {finding_text}",
                        S(fontName="Helvetica-Bold", fontSize=8.5, textColor=NAVY, leading=13)),
                ]
                if evidence:
                    inner.append(Paragraph(f"  Evidencia: {evidence}",
                        S(fontName="Helvetica", fontSize=8, textColor=NAVY, leading=12)))
                if src_url:
                    inner.append(Paragraph(f"  🔗 {src_url[:90]}",
                        S(fontName="Helvetica-Oblique", fontSize=7.5,
                          textColor=colors.HexColor("#1A5276"), leading=11)))

                story.append(KeepTogether([
                    box(inner, bg=LGRAY, border=mat_color),
                    Spacer(1,1*mm),
                ]))

        if market:
            story.append(Spacer(1,2*mm))
            story.append(box([
                Paragraph("🌐  Implicación de mercado",
                    S(fontName="Helvetica-Bold", fontSize=8.5, textColor=TEAL, leading=12)),
                Paragraph(market, S(fontName="Helvetica", fontSize=8.5, textColor=NAVY,
                    leading=13, alignment=TA_JUSTIFY)),
            ], bg=colors.HexColor("#EFF7F6"), border=TEAL))

        if pp_rel:
            story.append(Spacer(1,2*mm))
            story.append(box([
                Paragraph("💡  Relevancia para Parque Pharma",
                    S(fontName="Helvetica-Bold", fontSize=8.5, textColor=AMBER, leading=12)),
                Paragraph(pp_rel, S(fontName="Helvetica", fontSize=8.5, textColor=NAVY,
                    leading=13, alignment=TA_JUSTIFY)),
            ], bg=LAMB, border=AMBER))

    return story


def build_competitive_intel(parsed: dict, accent) -> list:
    story = []
    ci = parsed.get("competitive_intelligence", {})
    players = ci.get("key_players_news", [])
    gaps    = ci.get("market_gaps", [])

    if not players and not gaps:
        return story

    story.append(Spacer(1,4*mm))
    story.append(sbar("📊  Inteligencia Competitiva", bg=NAVY))
    story.append(Spacer(1,3*mm))

    if players:
        story.append(tbl(
            ["Empresa", "Novedad", "Relevancia para Parque Pharma"],
            [[p.get("company",""), p.get("news",""), p.get("relevance","")] for p in players],
            [35*mm, 80*mm, 52*mm],
        ))
        story.append(Spacer(1,3*mm))

    if gaps:
        story.append(Paragraph("Gaps y oportunidades identificadas:",
            S(fontName="Helvetica-Bold", fontSize=9, textColor=NAVY, leading=13, spaceAfter=3)))
        for gap in gaps:
            story.append(Paragraph(f"→ {gap}",
                S(fontName="Helvetica", fontSize=8.5, textColor=NAVY, leading=13,
                  leftIndent=10, spaceAfter=2)))

    return story


def build_regulatory_radar(parsed: dict, accent) -> list:
    story = []
    reg = parsed.get("regulatory_radar", {})
    fda_items = reg.get("fda_updates", [])
    ema_items = reg.get("ema_updates", [])
    cofepris  = reg.get("cofepris_notes", "")
    deadlines = reg.get("upcoming_deadlines", [])

    if not any([fda_items, ema_items, cofepris, deadlines]):
        return story

    story.append(Spacer(1,4*mm))
    story.append(sbar("⚖️  Radar Regulatorio — FDA / EMA / COFEPRIS", bg=colors.HexColor("#1A5276")))
    story.append(Spacer(1,3*mm))

    rows = []
    for item in fda_items:
        rows.append(["FDA", str(item)])
    for item in ema_items:
        rows.append(["EMA", str(item)])
    if cofepris:
        rows.append(["COFEPRIS", cofepris])
    for item in deadlines:
        rows.append(["⏰ Deadline", str(item)])

    if rows:
        story.append(tbl(["Agencia", "Novedad"], rows, [30*mm, 137*mm],
                         hbg=colors.HexColor("#1A5276")))

    return story


def build_recommendations(parsed: dict, accent) -> list:
    story = []
    recs = parsed.get("strategic_recommendations", [])
    if not recs:
        return story

    story.append(Spacer(1,4*mm))
    story.append(sbar("🎯  Recomendaciones Estratégicas para Parque Pharma", bg=AMBER,
                       txt_color=NAVY))
    story.append(Spacer(1,3*mm))

    for rec in recs:
        priority  = rec.get("priority", "?")
        recom     = rec.get("recommendation","")
        rationale = rec.get("rationale","")
        horizon   = rec.get("time_horizon","")
        resources = rec.get("resource_implication","")

        horizon_colors = {
            "inmediata":   RED,
            "1-4_semanas": AMBER,
            "1-3_meses":   TEAL,
            "6+_meses":    colors.HexColor("#1A5276"),
        }
        h_color = horizon_colors.get(horizon, TEAL)

        story.append(box([
            Paragraph(f"#{priority}  {recom}",
                S(fontName="Helvetica-Bold", fontSize=9, textColor=NAVY, leading=13)),
            Paragraph(f"<b>Justificación:</b> {rationale}",
                S(fontName="Helvetica", fontSize=8.5, textColor=NAVY, leading=13)),
            Paragraph(f"<b>Horizonte:</b> {horizon.replace('_',' ')}  ·  "
                      f"<b>Recursos:</b> {resources}",
                S(fontName="Helvetica-Oblique", fontSize=8, textColor=colors.HexColor("#555"),
                  leading=12)),
        ], bg=LGRAY, border=h_color))
        story.append(Spacer(1,2*mm))

    return story


def build_watchlist_and_sources(parsed: dict, accent) -> list:
    story = []
    watchlist = parsed.get("next_week_watchlist", [])
    sources   = parsed.get("sources_used", [])

    story.append(PageBreak())
    story.append(sbar("👁  Watchlist Semana Próxima", bg=TEAL))
    story.append(Spacer(1,3*mm))

    if watchlist:
        for i, item in enumerate(watchlist, 1):
            story.append(Paragraph(f"{i}. {item}",
                S(fontName="Helvetica", fontSize=9, textColor=NAVY, leading=14,
                  leftIndent=10, spaceAfter=3)))
    else:
        story.append(body("Sin ítems específicos para la siguiente semana."))

    story.append(Spacer(1,5*mm))
    story.append(sbar("📚  Fuentes Utilizadas en Este Reporte", bg=NAVY))
    story.append(Spacer(1,3*mm))

    if sources:
        rows = []
        for s in sources:
            rows.append([
                s.get("source",""),
                s.get("title","")[:70],
                s.get("relevance","")[:60],
                s.get("url","")[:50],
            ])
        story.append(tbl(
            ["Fuente","Título","Relevancia","URL"],
            rows,
            [28*mm, 65*mm, 52*mm, 45*mm],
        ))
    else:
        story.append(body("No se registraron fuentes específicas."))

    # Footer
    story.append(Spacer(1,6*mm))
    story.append(hr(TEAL, 1))
    story.append(Spacer(1,3*mm))
    meta = parsed.get("report_metadata", {})
    story.append(Paragraph(
        f"Reporte generado automáticamente el {meta.get('date_generated','')} · "
        f"Sistema de Inteligencia de Mercado · Parque Pharma® / NAVETA · "
        f"Semana {meta.get('week','?')} · {meta.get('year','')} · Confidencial",
        S(fontName="Helvetica-Oblique", fontSize=7.5,
          textColor=colors.HexColor("#888"), alignment=TA_CENTER)))

    return story


# ── Generador principal ────────────────────────────────────────────────────────

def generate_pdf(analysis, config, output_dir: str) -> str:
    """
    Genera el PDF completo a partir del AnalysisResult.
    Retorna la ruta al archivo generado.
    """
    os.makedirs(output_dir, exist_ok=True)
    week = analysis.week
    year = analysis.year
    fname = f"{config.filename_prefix}_Sem{week:02d}_{year}.pdf"
    fpath = os.path.join(output_dir, fname)

    accent = colors.HexColor(config.accent_color)

    # Callbacks
    cover_cb   = make_cover_callback(analysis, config)
    content_cb = make_content_callback(analysis, config)

    # Page templates
    cover_frame   = Frame(0,0,W,H,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0,id="cover")
    content_frame = Frame(2*cm,2.2*cm,W-4*cm,H-5.2*cm,id="normal")

    doc = BaseDocTemplate(
        fpath,
        pagesize=A4,
        pageTemplates=[
            PageTemplate(id="Cover",   frames=[cover_frame],  onPage=cover_cb),
            PageTemplate(id="Content", frames=[content_frame], onPage=content_cb),
        ],
    )

    # Construir story
    parsed = analysis.parsed
    story  = [NextPageTemplate("Content"), PageBreak()]
    story += build_executive_summary(parsed, accent)
    story += build_sections(parsed, config, accent)
    story += build_competitive_intel(parsed, accent)
    story += build_regulatory_radar(parsed, accent)
    story += build_recommendations(parsed, accent)
    story += build_watchlist_and_sources(parsed, accent)

    doc.build(story)
    logger.info(f"PDF generado: {fpath}")
    return fpath
