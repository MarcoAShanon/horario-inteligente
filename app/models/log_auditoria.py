"""
Model para Log de Auditoria
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.models.base import Base


class LogAuditoria(Base):
    """Registro de auditoria de ações no sistema"""
    __tablename__ = 'log_auditoria'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Quem realizou a ação
    usuario_id = Column(Integer, nullable=True)
    usuario_tipo = Column(String(50), nullable=False)
    usuario_nome = Column(String(255), nullable=True)
    usuario_email = Column(String(255), nullable=True)

    # Cliente afetado
    cliente_id = Column(Integer, nullable=True)

    # Ação realizada
    acao = Column(String(100), nullable=False)

    # Recurso afetado
    recurso = Column(String(100), nullable=True)
    recurso_id = Column(Integer, nullable=True)

    # Detalhes da mudança
    dados_anteriores = Column(JSONB, nullable=True)
    dados_novos = Column(JSONB, nullable=True)
    descricao = Column(Text, nullable=True)

    # Contexto da requisição
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String(255), nullable=True)
    metodo_http = Column(String(10), nullable=True)

    # Resultado
    sucesso = Column(Boolean, default=True)
    erro_mensagem = Column(Text, nullable=True)

    # Timestamp
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    # Tipos de usuário
    TIPO_ADMIN = 'admin'
    TIPO_FINANCEIRO = 'financeiro'
    TIPO_SUPORTE = 'suporte'
    TIPO_MEDICO = 'medico'
    TIPO_SECRETARIA = 'secretaria'
    TIPO_SISTEMA = 'sistema'

    # Ações comuns
    ACAO_LOGIN = 'login'
    ACAO_LOGOUT = 'logout'
    ACAO_CRIAR = 'criar'
    ACAO_ATUALIZAR = 'atualizar'
    ACAO_DELETAR = 'deletar'
    ACAO_VISUALIZAR = 'visualizar'
    ACAO_EXPORTAR = 'exportar'
    ACAO_IMPORTAR = 'importar'
    ACAO_APROVAR = 'aprovar'
    ACAO_REJEITAR = 'rejeitar'
    ACAO_ENVIAR_EMAIL = 'enviar_email'
    ACAO_ENVIAR_WHATSAPP = 'enviar_whatsapp'

    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'usuario_tipo': self.usuario_tipo,
            'usuario_nome': self.usuario_nome,
            'usuario_email': self.usuario_email,
            'cliente_id': self.cliente_id,
            'acao': self.acao,
            'recurso': self.recurso,
            'recurso_id': self.recurso_id,
            'dados_anteriores': self.dados_anteriores,
            'dados_novos': self.dados_novos,
            'descricao': self.descricao,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'endpoint': self.endpoint,
            'metodo_http': self.metodo_http,
            'sucesso': self.sucesso,
            'erro_mensagem': self.erro_mensagem,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None
        }

    def __repr__(self):
        return f"<LogAuditoria(id={self.id}, acao='{self.acao}', recurso='{self.recurso}')>"
