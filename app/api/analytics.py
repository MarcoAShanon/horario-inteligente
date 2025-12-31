"""
API de Analytics - Rastreamento de Visitantes
Endpoints para tracking e consulta de métricas
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import text, func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
import logging
import hashlib
import json
import re

from app.database import get_db
from app.api.admin import get_current_admin

# Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== SCHEMAS ====================

class TrackingData(BaseModel):
    """Dados de tracking recebidos do frontend"""
    visitor_id: str
    session_id: str
    pagina: str
    url_path: Optional[str] = None
    referrer: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    dispositivo: Optional[str] = None
    navegador: Optional[str] = None
    sistema_operacional: Optional[str] = None
    evento: str = "pageview"
    evento_dados: Optional[str] = None
    tempo_na_pagina: Optional[int] = None
    scroll_depth: Optional[int] = None


# ==================== HELPERS ====================

def parse_user_agent(user_agent: str) -> dict:
    """Extrai informações do User-Agent"""
    result = {
        "dispositivo": "desktop",
        "navegador": "Outro",
        "sistema_operacional": "Outro"
    }

    if not user_agent:
        return result

    ua = user_agent.lower()

    # Dispositivo
    if "mobile" in ua or "android" in ua and "mobile" in ua:
        result["dispositivo"] = "mobile"
    elif "tablet" in ua or "ipad" in ua:
        result["dispositivo"] = "tablet"

    # Navegador
    if "chrome" in ua and "edg" not in ua:
        result["navegador"] = "Chrome"
    elif "firefox" in ua:
        result["navegador"] = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        result["navegador"] = "Safari"
    elif "edg" in ua:
        result["navegador"] = "Edge"
    elif "opera" in ua or "opr" in ua:
        result["navegador"] = "Opera"

    # Sistema Operacional
    if "windows" in ua:
        result["sistema_operacional"] = "Windows"
    elif "mac os" in ua or "macintosh" in ua:
        result["sistema_operacional"] = "macOS"
    elif "linux" in ua and "android" not in ua:
        result["sistema_operacional"] = "Linux"
    elif "android" in ua:
        result["sistema_operacional"] = "Android"
    elif "iphone" in ua or "ipad" in ua:
        result["sistema_operacional"] = "iOS"

    return result


def sanitize_string(s: str, max_length: int = 500) -> str:
    """Sanitiza string removendo caracteres perigosos e escapando HTML"""
    if not s:
        return None
    # Remove tags HTML
    s = re.sub(r'<[^>]+>', '', s)
    # Escapa caracteres HTML perigosos
    s = s.replace('&', '&amp;')
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    s = s.replace('"', '&quot;')
    s = s.replace("'", '&#x27;')
    # Remove caracteres de controle (exceto newline e tab)
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)
    # Limita tamanho
    return s[:max_length] if len(s) > max_length else s


# ==================== TRACKING (PÚBLICO) ====================

@router.post("/api/analytics/track", tags=["Analytics"])
@limiter.limit("60/minute")  # Max 60 eventos por minuto por IP
async def track_pageview(
    request: Request,
    data: TrackingData,
    db: Session = Depends(get_db)
):
    """
    Registra um evento de analytics (pageview, click, etc.)
    Endpoint público - não requer autenticação
    """
    try:
        # Obter IP do visitante
        ip_address = request.client.host if request.client else None

        # Obter User-Agent
        user_agent = request.headers.get("User-Agent", "")

        # Parse User-Agent se não fornecido pelo cliente
        if not data.dispositivo or not data.navegador:
            ua_info = parse_user_agent(user_agent)
            if not data.dispositivo:
                data.dispositivo = ua_info["dispositivo"]
            if not data.navegador:
                data.navegador = ua_info["navegador"]
            if not data.sistema_operacional:
                data.sistema_operacional = ua_info["sistema_operacional"]

        # Sanitizar todos os dados de entrada
        referrer = sanitize_string(data.referrer, 1000)
        url_path = sanitize_string(data.url_path, 500)
        evento_dados = sanitize_string(data.evento_dados, 2000)

        # Sanitizar campos que podem conter dados maliciosos
        visitor_id = sanitize_string(data.visitor_id, 64)
        session_id = sanitize_string(data.session_id, 64)
        pagina = sanitize_string(data.pagina, 50)
        dispositivo = sanitize_string(data.dispositivo, 20) if data.dispositivo else None
        navegador = sanitize_string(data.navegador, 50) if data.navegador else None
        sistema_operacional = sanitize_string(data.sistema_operacional, 50) if data.sistema_operacional else None
        evento = sanitize_string(data.evento, 50)
        user_agent_sanitized = sanitize_string(user_agent, 1000) if user_agent else None

        # Inserir no banco
        db.execute(
            text("""
                INSERT INTO page_views (
                    visitor_id, session_id, pagina, url_path,
                    referrer, utm_source, utm_medium, utm_campaign,
                    user_agent, dispositivo, navegador, sistema_operacional,
                    ip_address, evento, evento_dados,
                    tempo_na_pagina, scroll_depth
                ) VALUES (
                    :visitor_id, :session_id, :pagina, :url_path,
                    :referrer, :utm_source, :utm_medium, :utm_campaign,
                    :user_agent, :dispositivo, :navegador, :sistema_operacional,
                    :ip_address, :evento, :evento_dados,
                    :tempo_na_pagina, :scroll_depth
                )
            """),
            {
                "visitor_id": visitor_id,
                "session_id": session_id,
                "pagina": pagina,
                "url_path": url_path,
                "referrer": referrer,
                "utm_source": sanitize_string(data.utm_source, 100),
                "utm_medium": sanitize_string(data.utm_medium, 100),
                "utm_campaign": sanitize_string(data.utm_campaign, 100),
                "user_agent": user_agent_sanitized,
                "dispositivo": dispositivo,
                "navegador": navegador,
                "sistema_operacional": sistema_operacional,
                "ip_address": ip_address[:45] if ip_address else None,
                "evento": evento,
                "evento_dados": evento_dados,
                "tempo_na_pagina": data.tempo_na_pagina,
                "scroll_depth": data.scroll_depth
            }
        )
        db.commit()

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Erro ao registrar analytics: {e}")
        db.rollback()
        # Retorna sucesso mesmo com erro para não afetar UX
        return {"status": "ok"}


# ==================== MÉTRICAS ADMIN ====================

@router.get("/api/admin/analytics/resumo", tags=["Analytics Admin"])
async def get_analytics_resumo(
    request: Request,
    periodo: str = "7d",  # 1d, 7d, 30d, 90d
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Resumo geral de analytics
    Requer autenticação de admin
    """
    try:
        # Calcular período
        dias = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}.get(periodo, 7)
        data_inicio = datetime.now() - timedelta(days=dias)

        # Total de pageviews
        total_pageviews = db.execute(
            text("""
                SELECT COUNT(*) FROM page_views
                WHERE criado_em >= :data_inicio AND evento = 'pageview'
            """),
            {"data_inicio": data_inicio}
        ).scalar() or 0

        # Visitantes únicos
        visitantes_unicos = db.execute(
            text("""
                SELECT COUNT(DISTINCT visitor_id) FROM page_views
                WHERE criado_em >= :data_inicio
            """),
            {"data_inicio": data_inicio}
        ).scalar() or 0

        # Pageviews hoje
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        pageviews_hoje = db.execute(
            text("""
                SELECT COUNT(*) FROM page_views
                WHERE criado_em >= :hoje AND evento = 'pageview'
            """),
            {"hoje": hoje}
        ).scalar() or 0

        # Visitantes hoje
        visitantes_hoje = db.execute(
            text("""
                SELECT COUNT(DISTINCT visitor_id) FROM page_views
                WHERE criado_em >= :hoje
            """),
            {"hoje": hoje}
        ).scalar() or 0

        # Cliques no demo
        cliques_demo = db.execute(
            text("""
                SELECT COUNT(*) FROM page_views
                WHERE criado_em >= :data_inicio AND evento = 'click_demo'
            """),
            {"data_inicio": data_inicio}
        ).scalar() or 0

        # Taxa de conversão (visitantes que clicaram em demo)
        taxa_conversao = round((cliques_demo / visitantes_unicos * 100), 2) if visitantes_unicos > 0 else 0

        # Tempo médio na página (segundos)
        tempo_medio = db.execute(
            text("""
                SELECT AVG(tempo_na_pagina) FROM page_views
                WHERE criado_em >= :data_inicio AND tempo_na_pagina IS NOT NULL AND tempo_na_pagina > 0
            """),
            {"data_inicio": data_inicio}
        ).scalar() or 0

        # Distribuição por página
        distribuicao_paginas = db.execute(
            text("""
                SELECT pagina, COUNT(*) as total
                FROM page_views
                WHERE criado_em >= :data_inicio AND evento = 'pageview'
                GROUP BY pagina
                ORDER BY total DESC
            """),
            {"data_inicio": data_inicio}
        ).fetchall()

        # Distribuição por dispositivo
        distribuicao_dispositivos = db.execute(
            text("""
                SELECT dispositivo, COUNT(DISTINCT visitor_id) as total
                FROM page_views
                WHERE criado_em >= :data_inicio AND dispositivo IS NOT NULL
                GROUP BY dispositivo
                ORDER BY total DESC
            """),
            {"data_inicio": data_inicio}
        ).fetchall()

        return {
            "periodo": periodo,
            "metricas": {
                "total_pageviews": total_pageviews,
                "visitantes_unicos": visitantes_unicos,
                "pageviews_hoje": pageviews_hoje,
                "visitantes_hoje": visitantes_hoje,
                "cliques_demo": cliques_demo,
                "taxa_conversao": taxa_conversao,
                "tempo_medio_segundos": round(tempo_medio) if tempo_medio else 0
            },
            "distribuicao_paginas": [
                {"pagina": row[0], "total": row[1]} for row in distribuicao_paginas
            ],
            "distribuicao_dispositivos": [
                {"dispositivo": row[0] or "Desconhecido", "total": row[1]} for row in distribuicao_dispositivos
            ]
        }

    except Exception as e:
        logger.error(f"Erro ao buscar resumo analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar dados de analytics"
        )


@router.get("/api/admin/analytics/grafico", tags=["Analytics Admin"])
async def get_analytics_grafico(
    request: Request,
    periodo: str = "30d",
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Dados para gráfico de evolução temporal
    """
    try:
        dias = {"7d": 7, "30d": 30, "90d": 90}.get(periodo, 30)
        data_inicio = datetime.now() - timedelta(days=dias)

        # Pageviews por dia
        pageviews_por_dia = db.execute(
            text("""
                SELECT DATE(criado_em) as dia, COUNT(*) as pageviews, COUNT(DISTINCT visitor_id) as visitantes
                FROM page_views
                WHERE criado_em >= :data_inicio AND evento = 'pageview'
                GROUP BY DATE(criado_em)
                ORDER BY dia
            """),
            {"data_inicio": data_inicio}
        ).fetchall()

        return {
            "periodo": periodo,
            "dados": [
                {
                    "dia": row[0].isoformat() if row[0] else None,
                    "pageviews": row[1],
                    "visitantes": row[2]
                } for row in pageviews_por_dia
            ]
        }

    except Exception as e:
        logger.error(f"Erro ao buscar gráfico analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar dados do gráfico"
        )


@router.get("/api/admin/analytics/origens", tags=["Analytics Admin"])
async def get_analytics_origens(
    request: Request,
    periodo: str = "30d",
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Top origens de tráfego (referrers)
    """
    try:
        dias = {"7d": 7, "30d": 30, "90d": 90}.get(periodo, 30)
        data_inicio = datetime.now() - timedelta(days=dias)

        # Top referrers
        referrers = db.execute(
            text("""
                SELECT
                    CASE
                        WHEN referrer IS NULL OR referrer = '' THEN 'Direto'
                        WHEN referrer LIKE '%google%' THEN 'Google'
                        WHEN referrer LIKE '%facebook%' OR referrer LIKE '%fb.%' THEN 'Facebook'
                        WHEN referrer LIKE '%instagram%' THEN 'Instagram'
                        WHEN referrer LIKE '%linkedin%' THEN 'LinkedIn'
                        WHEN referrer LIKE '%twitter%' OR referrer LIKE '%t.co%' THEN 'Twitter/X'
                        WHEN referrer LIKE '%youtube%' THEN 'YouTube'
                        ELSE 'Outros'
                    END as origem,
                    COUNT(DISTINCT visitor_id) as visitantes,
                    COUNT(*) as pageviews
                FROM page_views
                WHERE criado_em >= :data_inicio
                GROUP BY origem
                ORDER BY visitantes DESC
                LIMIT 10
            """),
            {"data_inicio": data_inicio}
        ).fetchall()

        # UTM Sources
        utm_sources = db.execute(
            text("""
                SELECT utm_source, utm_medium, COUNT(DISTINCT visitor_id) as visitantes
                FROM page_views
                WHERE criado_em >= :data_inicio AND utm_source IS NOT NULL
                GROUP BY utm_source, utm_medium
                ORDER BY visitantes DESC
                LIMIT 10
            """),
            {"data_inicio": data_inicio}
        ).fetchall()

        return {
            "periodo": periodo,
            "referrers": [
                {"origem": row[0], "visitantes": row[1], "pageviews": row[2]}
                for row in referrers
            ],
            "utm_sources": [
                {"source": row[0], "medium": row[1], "visitantes": row[2]}
                for row in utm_sources
            ]
        }

    except Exception as e:
        logger.error(f"Erro ao buscar origens: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar origens de tráfego"
        )


@router.get("/api/admin/analytics/eventos", tags=["Analytics Admin"])
async def get_analytics_eventos(
    request: Request,
    periodo: str = "30d",
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Eventos de conversão (cliques, interações)
    """
    try:
        dias = {"7d": 7, "30d": 30, "90d": 90}.get(periodo, 30)
        data_inicio = datetime.now() - timedelta(days=dias)

        # Contagem de eventos
        eventos = db.execute(
            text("""
                SELECT evento, COUNT(*) as total, COUNT(DISTINCT visitor_id) as visitantes_unicos
                FROM page_views
                WHERE criado_em >= :data_inicio
                GROUP BY evento
                ORDER BY total DESC
            """),
            {"data_inicio": data_inicio}
        ).fetchall()

        # Funil de conversão
        total_visitantes = db.execute(
            text("SELECT COUNT(DISTINCT visitor_id) FROM page_views WHERE criado_em >= :data_inicio"),
            {"data_inicio": data_inicio}
        ).scalar() or 0

        visitantes_demo = db.execute(
            text("SELECT COUNT(DISTINCT visitor_id) FROM page_views WHERE criado_em >= :data_inicio AND pagina = 'demo'"),
            {"data_inicio": data_inicio}
        ).scalar() or 0

        cliques_demo = db.execute(
            text("SELECT COUNT(DISTINCT visitor_id) FROM page_views WHERE criado_em >= :data_inicio AND evento = 'click_demo'"),
            {"data_inicio": data_inicio}
        ).scalar() or 0

        cliques_contato = db.execute(
            text("SELECT COUNT(DISTINCT visitor_id) FROM page_views WHERE criado_em >= :data_inicio AND evento = 'click_contato'"),
            {"data_inicio": data_inicio}
        ).scalar() or 0

        return {
            "periodo": periodo,
            "eventos": [
                {"evento": row[0], "total": row[1], "visitantes_unicos": row[2]}
                for row in eventos
            ],
            "funil": {
                "landing_page": total_visitantes,
                "pagina_demo": visitantes_demo,
                "click_demo": cliques_demo,
                "click_contato": cliques_contato
            }
        }

    except Exception as e:
        logger.error(f"Erro ao buscar eventos: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar eventos"
        )


@router.get("/api/admin/analytics/visitantes", tags=["Analytics Admin"])
async def get_analytics_visitantes(
    request: Request,
    periodo: str = "7d",
    pagina: int = 1,
    limite: int = 50,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Lista de visitantes recentes com suas interações
    """
    try:
        dias = {"1d": 1, "7d": 7, "30d": 30}.get(periodo, 7)
        data_inicio = datetime.now() - timedelta(days=dias)
        offset = (pagina - 1) * limite

        # Visitantes únicos com resumo
        visitantes = db.execute(
            text("""
                SELECT
                    visitor_id,
                    MIN(criado_em) as primeira_visita,
                    MAX(criado_em) as ultima_visita,
                    COUNT(*) as total_pageviews,
                    COUNT(DISTINCT session_id) as sessoes,
                    MAX(dispositivo) as dispositivo,
                    MAX(navegador) as navegador,
                    MAX(sistema_operacional) as so,
                    ARRAY_AGG(DISTINCT pagina) as paginas_visitadas,
                    BOOL_OR(evento = 'click_demo') as clicou_demo,
                    BOOL_OR(evento = 'click_contato') as clicou_contato
                FROM page_views
                WHERE criado_em >= :data_inicio
                GROUP BY visitor_id
                ORDER BY ultima_visita DESC
                LIMIT :limite OFFSET :offset
            """),
            {"data_inicio": data_inicio, "limite": limite, "offset": offset}
        ).fetchall()

        # Total de visitantes
        total = db.execute(
            text("""
                SELECT COUNT(DISTINCT visitor_id) FROM page_views
                WHERE criado_em >= :data_inicio
            """),
            {"data_inicio": data_inicio}
        ).scalar() or 0

        return {
            "periodo": periodo,
            "pagina": pagina,
            "limite": limite,
            "total": total,
            "visitantes": [
                {
                    "visitor_id": row[0][:12] + "...",  # Trunca para privacidade
                    "primeira_visita": row[1].isoformat() if row[1] else None,
                    "ultima_visita": row[2].isoformat() if row[2] else None,
                    "total_pageviews": row[3],
                    "sessoes": row[4],
                    "dispositivo": row[5],
                    "navegador": row[6],
                    "sistema_operacional": row[7],
                    "paginas_visitadas": row[8] if row[8] else [],
                    "clicou_demo": row[9],
                    "clicou_contato": row[10]
                } for row in visitantes
            ]
        }

    except Exception as e:
        logger.error(f"Erro ao buscar visitantes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar visitantes"
        )
