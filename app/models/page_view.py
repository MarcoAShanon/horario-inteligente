"""
Model para Page Views - Analytics de Visitantes
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.sql import func
from app.models.base import Base


class PageView(Base):
    """Registro de visualizações de página para analytics"""
    __tablename__ = 'page_views'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identificação do visitante (fingerprint do navegador)
    visitor_id = Column(String(64), nullable=False, index=True)

    # Sessão do visitante (agrupa pageviews de uma mesma visita)
    session_id = Column(String(64), nullable=False, index=True)

    # Página visitada
    pagina = Column(String(50), nullable=False)  # 'landing', 'demo', 'demo_login', etc.
    url_path = Column(String(500), nullable=True)

    # Origem do tráfego
    referrer = Column(Text, nullable=True)
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)

    # Informações do dispositivo
    user_agent = Column(Text, nullable=True)
    dispositivo = Column(String(20), nullable=True)  # 'desktop', 'mobile', 'tablet'
    navegador = Column(String(50), nullable=True)
    sistema_operacional = Column(String(50), nullable=True)

    # Localização (baseada no IP)
    ip_address = Column(String(45), nullable=True)
    pais = Column(String(100), nullable=True)
    estado = Column(String(100), nullable=True)
    cidade = Column(String(100), nullable=True)

    # Interações
    evento = Column(String(50), nullable=True)  # 'pageview', 'click_demo', 'click_contato', 'tour_start', 'tour_complete'
    evento_dados = Column(Text, nullable=True)  # JSON com dados adicionais do evento

    # Métricas de engajamento
    tempo_na_pagina = Column(Integer, nullable=True)  # segundos
    scroll_depth = Column(Integer, nullable=True)  # porcentagem 0-100

    # Timestamps
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Índices para consultas de analytics
    __table_args__ = (
        Index('ix_page_views_pagina_criado', 'pagina', 'criado_em'),
        Index('ix_page_views_visitor_pagina', 'visitor_id', 'pagina'),
        Index('ix_page_views_data', 'criado_em'),
    )

    # Tipos de página
    PAGINA_LANDING = 'landing'
    PAGINA_DEMO = 'demo'
    PAGINA_DEMO_DASHBOARD = 'demo_dashboard'
    PAGINA_PRECO = 'precos'
    PAGINA_CONTATO = 'contato'

    # Tipos de evento
    EVENTO_PAGEVIEW = 'pageview'
    EVENTO_CLICK_DEMO = 'click_demo'
    EVENTO_CLICK_CONTATO = 'click_contato'
    EVENTO_CLICK_WHATSAPP = 'click_whatsapp'
    EVENTO_TOUR_START = 'tour_start'
    EVENTO_TOUR_COMPLETE = 'tour_complete'
    EVENTO_SCROLL = 'scroll'
    EVENTO_EXIT = 'exit'

    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'visitor_id': self.visitor_id,
            'session_id': self.session_id,
            'pagina': self.pagina,
            'url_path': self.url_path,
            'referrer': self.referrer,
            'utm_source': self.utm_source,
            'utm_medium': self.utm_medium,
            'utm_campaign': self.utm_campaign,
            'dispositivo': self.dispositivo,
            'navegador': self.navegador,
            'sistema_operacional': self.sistema_operacional,
            'evento': self.evento,
            'evento_dados': self.evento_dados,
            'tempo_na_pagina': self.tempo_na_pagina,
            'scroll_depth': self.scroll_depth,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None
        }

    def __repr__(self):
        return f"<PageView(id={self.id}, pagina='{self.pagina}', visitor='{self.visitor_id[:8]}...')>"
