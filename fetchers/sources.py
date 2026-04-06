"""
=============================================================================
fetchers/sources.py — Recolección de fuentes: PubMed + FDA RSS + RSS feeds
=============================================================================
"""

import feedparser
import urllib.request
import urllib.parse
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger("pharma_intel.fetchers")


@dataclass
class Article:
    title:    str
    abstract: str
    source:   str
    url:      str
    date:     str
    authors:  str = ""
    doi:      str = ""


# ── PubMed ───────────────────────────────────────────────────────────────────

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_SUMMARY_URL= "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


def fetch_pubmed_articles(query: str, days_back: int = 7, max_results: int = 5) -> List[Article]:
    """Busca artículos en PubMed de los últimos N días para un query dado."""
    articles = []
    try:
        # Agregar filtro de fecha
        date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
        full_query = f'({query}) AND ("{date_from}"[PDat] : "3000"[PDat])'

        # Step 1: Search — obtener IDs
        search_params = urllib.parse.urlencode({
            "db": "pubmed",
            "term": full_query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        })
        search_url = f"{PUBMED_SEARCH_URL}?{search_params}"
        with urllib.request.urlopen(search_url, timeout=15) as resp:
            search_data = json.loads(resp.read())

        ids = search_data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            logger.info(f"PubMed: sin resultados para '{query[:50]}...'")
            return []

        time.sleep(0.34)  # rate limit — max 3 req/s sin API key

        # Step 2: Fetch summaries
        summary_params = urllib.parse.urlencode({
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "json",
        })
        summary_url = f"{PUBMED_SUMMARY_URL}?{summary_params}"
        with urllib.request.urlopen(summary_url, timeout=15) as resp:
            summary_data = json.loads(resp.read())

        uids = summary_data.get("result", {}).get("uids", [])
        for uid in uids:
            item = summary_data["result"].get(uid, {})
            title    = item.get("title", "Sin título").strip()
            source   = item.get("source", "PubMed")
            pub_date = item.get("pubdate", "")
            authors_raw = item.get("authors", [])
            authors  = ", ".join(a.get("name", "") for a in authors_raw[:3])
            if len(authors_raw) > 3:
                authors += " et al."

            articles.append(Article(
                title    = title,
                abstract = "",   # se llena abajo con efetch
                source   = f"PubMed — {source}",
                url      = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                date     = pub_date,
                authors  = authors,
                doi      = item.get("elocationid", ""),
            ))

        time.sleep(0.34)

        # Step 3: Fetch abstracts (efetch)
        fetch_params = urllib.parse.urlencode({
            "db":      "pubmed",
            "id":      ",".join(ids),
            "rettype": "abstract",
            "retmode": "text",
        })
        fetch_url = f"{PUBMED_FETCH_URL}?{fetch_params}"
        with urllib.request.urlopen(fetch_url, timeout=20) as resp:
            raw_text = resp.read().decode("utf-8", errors="replace")

        # Parsear abstracts por UID
        blocks = raw_text.split("\n\n\n")
        abstract_map = {}
        for i, (uid, block) in enumerate(zip(ids, blocks)):
            lines = block.split("\n")
            ab_lines = []
            in_abstract = False
            for line in lines:
                if line.startswith("AB  -"):
                    in_abstract = True
                    ab_lines.append(line[6:].strip())
                elif in_abstract and line.startswith("      "):
                    ab_lines.append(line.strip())
                elif in_abstract:
                    break
            abstract_map[uid] = " ".join(ab_lines)

        for i, art in enumerate(articles):
            uid = ids[i] if i < len(ids) else None
            if uid and uid in abstract_map:
                articles[i].abstract = abstract_map[uid]

        logger.info(f"PubMed: {len(articles)} artículos para '{query[:50]}'")

    except Exception as e:
        logger.warning(f"PubMed fetch error para '{query[:50]}': {e}")

    return articles


# ── FDA RSS ───────────────────────────────────────────────────────────────────

FDA_RSS_FEEDS = {
    "drugs":     "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drugs/rss.xml",
    "biologics": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/biologics/rss.xml",
    "devices":   "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/medical-devices/rss.xml",
    "approvals": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/new-drug-approvals/rss.xml",
    "safety":    "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/medwatch/rss.xml",
}


def fetch_fda_news(categories: List[str], days_back: int = 7, max_per_feed: int = 5) -> List[Article]:
    """Obtiene noticias recientes de FDA RSS por categoría."""
    articles = []
    cutoff = datetime.now() - timedelta(days=days_back)

    for cat in categories:
        feed_url = FDA_RSS_FEEDS.get(cat)
        if not feed_url:
            continue
        try:
            feed = feedparser.parse(feed_url)
            count = 0
            for entry in feed.entries:
                if count >= max_per_feed:
                    break
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub:
                    pub_dt = datetime(*pub[:6])
                    if pub_dt < cutoff:
                        continue
                articles.append(Article(
                    title    = entry.get("title", "Sin título"),
                    abstract = entry.get("summary", ""),
                    source   = f"FDA — {cat.capitalize()}",
                    url      = entry.get("link", ""),
                    date     = entry.get("published", ""),
                ))
                count += 1
            logger.info(f"FDA RSS [{cat}]: {count} items")
        except Exception as e:
            logger.warning(f"FDA RSS error [{cat}]: {e}")

    return articles


# ── Feeds RSS generales ───────────────────────────────────────────────────────

def fetch_rss_feed(url: str, days_back: int = 7, max_items: int = 5) -> List[Article]:
    """Parsea un feed RSS genérico."""
    articles = []
    cutoff   = datetime.now() - timedelta(days=days_back)
    try:
        feed = feedparser.parse(url)
        source = feed.feed.get("title", url)
        count  = 0
        for entry in feed.entries:
            if count >= max_items:
                break
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub:
                pub_dt = datetime(*pub[:6])
                if pub_dt < cutoff:
                    continue
            summary = entry.get("summary", entry.get("description", ""))
            # Limpiar HTML básico
            import re
            summary = re.sub(r"<[^>]+>", "", summary)[:800]
            articles.append(Article(
                title    = entry.get("title", "Sin título"),
                abstract = summary,
                source   = source,
                url      = entry.get("link", ""),
                date     = entry.get("published", ""),
            ))
            count += 1
        logger.info(f"RSS [{source[:40]}]: {count} items")
    except Exception as e:
        logger.warning(f"RSS error [{url[:60]}]: {e}")
    return articles


# ── Orquestador de fuentes ────────────────────────────────────────────────────

def collect_all_sources(config, days_back: int = 7) -> Dict[str, List[Article]]:
    """
    Recolecta todas las fuentes para un ReportConfig dado.
    Retorna dict con claves: 'pubmed', 'fda', 'rss'
    """
    results = {"pubmed": [], "fda": [], "rss": []}

    # PubMed — máximo 3 artículos por query para no sobrecargar el prompt
    seen_urls = set()
    for q in config.pubmed_queries:
        arts = fetch_pubmed_articles(q, days_back=days_back, max_results=3)
        for a in arts:
            if a.url not in seen_urls:
                results["pubmed"].append(a)
                seen_urls.add(a.url)
        time.sleep(0.5)  # cortesía

    # FDA RSS
    results["fda"] = fetch_fda_news(config.fda_categories, days_back=days_back)

    # RSS feeds adicionales
    for url in config.rss_feeds:
        arts = fetch_rss_feed(url, days_back=days_back, max_items=4)
        results["rss"].extend(arts)
        time.sleep(0.3)

    total = sum(len(v) for v in results.values())
    logger.info(f"Total fuentes recolectadas: {total} "
                f"(PubMed: {len(results['pubmed'])}, FDA: {len(results['fda'])}, RSS: {len(results['rss'])})")

    return results


def format_sources_for_prompt(sources: Dict[str, List[Article]]) -> str:
    """Convierte las fuentes recolectadas en texto estructurado para el prompt."""
    lines = []
    all_articles = (
        [("PUBMED", a) for a in sources["pubmed"]] +
        [("FDA",    a) for a in sources["fda"]]    +
        [("RSS",    a) for a in sources["rss"]]
    )

    if not all_articles:
        return "No se encontraron fuentes nuevas esta semana para las queries configuradas."

    for i, (src_type, art) in enumerate(all_articles, 1):
        lines.append(f"--- FUENTE {i} [{src_type}] ---")
        lines.append(f"Título: {art.title}")
        if art.authors:
            lines.append(f"Autores: {art.authors}")
        lines.append(f"Fuente: {art.source}")
        lines.append(f"Fecha: {art.date}")
        lines.append(f"URL: {art.url}")
        if art.abstract:
            lines.append(f"Resumen: {art.abstract[:600]}{'...' if len(art.abstract) > 600 else ''}")
        lines.append("")

    return "\n".join(lines)
