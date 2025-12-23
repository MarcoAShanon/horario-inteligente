"""
Serviço de Auditoria
Registra todas as ações importantes do sistema
"""
import logging
from typing import Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import Request

logger = logging.getLogger(__name__)


class AuditoriaService:
    """Serviço para registro de auditoria"""

    def __init__(self, db: Session):
        self.db = db

    def registrar(
        self,
        acao: str,
        usuario_id: Optional[int] = None,
        usuario_tipo: str = 'sistema',
        usuario_nome: Optional[str] = None,
        usuario_email: Optional[str] = None,
        cliente_id: Optional[int] = None,
        recurso: Optional[str] = None,
        recurso_id: Optional[int] = None,
        dados_anteriores: Optional[dict] = None,
        dados_novos: Optional[dict] = None,
        descricao: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        metodo_http: Optional[str] = None,
        sucesso: bool = True,
        erro_mensagem: Optional[str] = None
    ) -> int:
        """
        Registra uma ação no log de auditoria

        Args:
            acao: Ação realizada (login, criar, atualizar, etc.)
            usuario_id: ID do usuário que realizou a ação
            usuario_tipo: Tipo do usuário (admin, financeiro, suporte, medico, secretaria, sistema)
            usuario_nome: Nome do usuário
            usuario_email: Email do usuário
            cliente_id: ID do cliente afetado (se aplicável)
            recurso: Tipo de recurso afetado (cliente, agendamento, etc.)
            recurso_id: ID do recurso afetado
            dados_anteriores: Estado anterior do recurso (JSON)
            dados_novos: Novo estado do recurso (JSON)
            descricao: Descrição textual da ação
            ip_address: IP do usuário
            user_agent: User-Agent do navegador
            endpoint: Endpoint da API chamado
            metodo_http: Método HTTP (GET, POST, etc.)
            sucesso: Se a ação foi bem-sucedida
            erro_mensagem: Mensagem de erro (se aplicável)

        Returns:
            ID do registro de auditoria criado
        """
        try:
            import json

            result = self.db.execute(text("""
                INSERT INTO log_auditoria (
                    usuario_id, usuario_tipo, usuario_nome, usuario_email,
                    cliente_id, acao, recurso, recurso_id,
                    dados_anteriores, dados_novos, descricao,
                    ip_address, user_agent, endpoint, metodo_http,
                    sucesso, erro_mensagem
                ) VALUES (
                    :usuario_id, :usuario_tipo, :usuario_nome, :usuario_email,
                    :cliente_id, :acao, :recurso, :recurso_id,
                    CAST(:dados_anteriores AS jsonb), CAST(:dados_novos AS jsonb), :descricao,
                    :ip_address, :user_agent, :endpoint, :metodo_http,
                    :sucesso, :erro_mensagem
                ) RETURNING id
            """), {
                "usuario_id": usuario_id,
                "usuario_tipo": usuario_tipo,
                "usuario_nome": usuario_nome,
                "usuario_email": usuario_email,
                "cliente_id": cliente_id,
                "acao": acao,
                "recurso": recurso,
                "recurso_id": recurso_id,
                "dados_anteriores": json.dumps(dados_anteriores) if dados_anteriores else None,
                "dados_novos": json.dumps(dados_novos) if dados_novos else None,
                "descricao": descricao,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "endpoint": endpoint,
                "metodo_http": metodo_http,
                "sucesso": sucesso,
                "erro_mensagem": erro_mensagem
            })

            log_id = result.fetchone()[0]
            self.db.commit()

            logger.debug(f"Auditoria registrada: {acao} - {recurso} - ID: {log_id}")
            return log_id

        except Exception as e:
            logger.error(f"Erro ao registrar auditoria: {e}")
            # Não propaga o erro para não impactar a operação principal
            return 0

    def registrar_login(
        self,
        usuario_id: int,
        usuario_tipo: str,
        usuario_nome: str,
        usuario_email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        sucesso: bool = True,
        erro_mensagem: Optional[str] = None
    ) -> int:
        """Atalho para registrar login"""
        return self.registrar(
            acao='login',
            usuario_id=usuario_id,
            usuario_tipo=usuario_tipo,
            usuario_nome=usuario_nome,
            usuario_email=usuario_email,
            ip_address=ip_address,
            user_agent=user_agent,
            sucesso=sucesso,
            erro_mensagem=erro_mensagem,
            descricao=f"Login {'bem-sucedido' if sucesso else 'falhou'}: {usuario_email}"
        )

    def registrar_crud(
        self,
        acao: str,  # 'criar', 'atualizar', 'deletar'
        recurso: str,
        recurso_id: int,
        usuario_id: int,
        usuario_tipo: str,
        usuario_nome: str,
        dados_anteriores: Optional[dict] = None,
        dados_novos: Optional[dict] = None,
        cliente_id: Optional[int] = None,
        request: Optional[Request] = None
    ) -> int:
        """Atalho para registrar operações CRUD"""
        ip_address = None
        user_agent = None
        endpoint = None
        metodo_http = None

        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent')
            endpoint = str(request.url.path)
            metodo_http = request.method

        return self.registrar(
            acao=acao,
            usuario_id=usuario_id,
            usuario_tipo=usuario_tipo,
            usuario_nome=usuario_nome,
            cliente_id=cliente_id,
            recurso=recurso,
            recurso_id=recurso_id,
            dados_anteriores=dados_anteriores,
            dados_novos=dados_novos,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            metodo_http=metodo_http,
            descricao=f"{acao.capitalize()} {recurso} ID={recurso_id}"
        )

    def buscar_logs(
        self,
        usuario_id: Optional[int] = None,
        usuario_tipo: Optional[str] = None,
        cliente_id: Optional[int] = None,
        acao: Optional[str] = None,
        recurso: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        limite: int = 100,
        offset: int = 0
    ) -> list:
        """
        Busca logs de auditoria com filtros

        Returns:
            Lista de registros de auditoria
        """
        query = """
            SELECT
                id, usuario_id, usuario_tipo, usuario_nome, usuario_email,
                cliente_id, acao, recurso, recurso_id,
                dados_anteriores, dados_novos, descricao,
                ip_address, user_agent, endpoint, metodo_http,
                sucesso, erro_mensagem, criado_em
            FROM log_auditoria
            WHERE 1=1
        """
        params = {"limite": limite, "offset": offset}

        if usuario_id:
            query += " AND usuario_id = :usuario_id"
            params["usuario_id"] = usuario_id

        if usuario_tipo:
            query += " AND usuario_tipo = :usuario_tipo"
            params["usuario_tipo"] = usuario_tipo

        if cliente_id:
            query += " AND cliente_id = :cliente_id"
            params["cliente_id"] = cliente_id

        if acao:
            query += " AND acao = :acao"
            params["acao"] = acao

        if recurso:
            query += " AND recurso = :recurso"
            params["recurso"] = recurso

        if data_inicio:
            query += " AND criado_em >= :data_inicio"
            params["data_inicio"] = data_inicio

        if data_fim:
            query += " AND criado_em <= :data_fim"
            params["data_fim"] = data_fim

        query += " ORDER BY criado_em DESC LIMIT :limite OFFSET :offset"

        result = self.db.execute(text(query), params).fetchall()

        return [
            {
                'id': row[0],
                'usuario_id': row[1],
                'usuario_tipo': row[2],
                'usuario_nome': row[3],
                'usuario_email': row[4],
                'cliente_id': row[5],
                'acao': row[6],
                'recurso': row[7],
                'recurso_id': row[8],
                'dados_anteriores': row[9],
                'dados_novos': row[10],
                'descricao': row[11],
                'ip_address': row[12],
                'user_agent': row[13],
                'endpoint': row[14],
                'metodo_http': row[15],
                'sucesso': row[16],
                'erro_mensagem': row[17],
                'criado_em': row[18].isoformat() if row[18] else None
            }
            for row in result
        ]


def get_auditoria_service(db: Session) -> AuditoriaService:
    """Factory para obter instância do serviço"""
    return AuditoriaService(db)
