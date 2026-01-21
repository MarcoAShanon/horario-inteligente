"""
Service de Conversas WhatsApp
Horário Inteligente SaaS

Gerencia operações de CRUD e lógica de negócio para conversas e mensagens.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import Optional, List
from app.models.conversa import Conversa, StatusConversa
from app.models.mensagem import Mensagem, DirecaoMensagem, RemetenteMensagem, TipoMensagem


class ConversaService:

    @staticmethod
    def criar_ou_recuperar_conversa(
        db: Session,
        cliente_id: int,
        telefone: str,
        nome_paciente: Optional[str] = None
    ) -> Conversa:
        """Busca conversa ativa ou cria uma nova"""
        # Buscar conversa ativa (não encerrada) para este telefone
        conversa = db.query(Conversa).filter(
            Conversa.cliente_id == cliente_id,
            Conversa.paciente_telefone == telefone,
            Conversa.status != StatusConversa.ENCERRADA
        ).first()

        if not conversa:
            conversa = Conversa(
                cliente_id=cliente_id,
                paciente_telefone=telefone,
                paciente_nome=nome_paciente,
                status=StatusConversa.IA_ATIVA
            )
            db.add(conversa)
            db.commit()
            db.refresh(conversa)
        elif nome_paciente and not conversa.paciente_nome:
            conversa.paciente_nome = nome_paciente
            db.commit()

        return conversa

    @staticmethod
    def adicionar_mensagem(
        db: Session,
        conversa_id: int,
        direcao: DirecaoMensagem,
        remetente: RemetenteMensagem,
        conteudo: str,
        tipo: TipoMensagem = TipoMensagem.TEXTO,
        midia_url: Optional[str] = None
    ) -> Mensagem:
        """Adiciona uma mensagem à conversa"""
        mensagem = Mensagem(
            conversa_id=conversa_id,
            direcao=direcao,
            remetente=remetente,
            tipo=tipo,
            conteudo=conteudo,
            midia_url=midia_url
        )
        db.add(mensagem)

        # Atualizar timestamp da última mensagem na conversa
        conversa = db.query(Conversa).filter(Conversa.id == conversa_id).first()
        if conversa:
            conversa.ultima_mensagem_at = datetime.utcnow()

        db.commit()
        db.refresh(mensagem)
        return mensagem

    @staticmethod
    def assumir_conversa(db: Session, conversa_id: int, atendente_id: int, atendente_tipo: str = "medico") -> Optional[Conversa]:
        """Atendente assume a conversa (desativa IA)"""
        conversa = db.query(Conversa).filter(Conversa.id == conversa_id).first()
        if conversa and conversa.status != StatusConversa.ENCERRADA:
            conversa.status = StatusConversa.HUMANO_ASSUMIU
            conversa.atendente_id = atendente_id
            conversa.atendente_tipo = atendente_tipo
            db.commit()
            db.refresh(conversa)
        return conversa

    @staticmethod
    def devolver_para_ia(db: Session, conversa_id: int) -> Optional[Conversa]:
        """Devolve a conversa para a IA"""
        conversa = db.query(Conversa).filter(Conversa.id == conversa_id).first()
        if conversa and conversa.status == StatusConversa.HUMANO_ASSUMIU:
            conversa.status = StatusConversa.IA_ATIVA
            conversa.atendente_id = None
            conversa.atendente_tipo = None
            db.commit()
            db.refresh(conversa)
        return conversa

    @staticmethod
    def encerrar_conversa(db: Session, conversa_id: int) -> Optional[Conversa]:
        """Encerra a conversa"""
        conversa = db.query(Conversa).filter(Conversa.id == conversa_id).first()
        if conversa:
            conversa.status = StatusConversa.ENCERRADA
            conversa.closed_at = datetime.utcnow()
            db.commit()
            db.refresh(conversa)
        return conversa

    @staticmethod
    def listar_conversas(
        db: Session,
        cliente_id: int,
        status: Optional[StatusConversa] = None,
        limit: int = 50
    ) -> List[Conversa]:
        """Lista conversas do cliente, ordenadas por última mensagem"""
        query = db.query(Conversa).filter(Conversa.cliente_id == cliente_id)

        if status:
            query = query.filter(Conversa.status == status)
        else:
            # Por padrão, não mostra encerradas
            query = query.filter(Conversa.status != StatusConversa.ENCERRADA)

        return query.order_by(desc(Conversa.ultima_mensagem_at)).limit(limit).all()

    @staticmethod
    def buscar_mensagens(
        db: Session,
        conversa_id: int,
        limit: int = 100
    ) -> List[Mensagem]:
        """Busca mensagens de uma conversa"""
        return db.query(Mensagem).filter(
            Mensagem.conversa_id == conversa_id
        ).order_by(Mensagem.timestamp).limit(limit).all()

    @staticmethod
    def marcar_mensagens_como_lidas(db: Session, conversa_id: int) -> int:
        """Marca todas as mensagens de entrada como lidas"""
        result = db.query(Mensagem).filter(
            Mensagem.conversa_id == conversa_id,
            Mensagem.direcao == DirecaoMensagem.ENTRADA,
            Mensagem.lida == False
        ).update({"lida": True})
        db.commit()
        return result

    @staticmethod
    def contar_nao_lidas(db: Session, cliente_id: int) -> int:
        """Conta mensagens não lidas do cliente"""
        return db.query(Mensagem).join(Conversa).filter(
            Conversa.cliente_id == cliente_id,
            Conversa.status != StatusConversa.ENCERRADA,
            Mensagem.direcao == DirecaoMensagem.ENTRADA,
            Mensagem.lida == False
        ).count()

    @staticmethod
    def buscar_por_telefone(db: Session, cliente_id: int, telefone: str) -> Optional[Conversa]:
        """Busca conversa ativa por telefone"""
        return db.query(Conversa).filter(
            Conversa.cliente_id == cliente_id,
            Conversa.paciente_telefone == telefone,
            Conversa.status != StatusConversa.ENCERRADA
        ).first()
