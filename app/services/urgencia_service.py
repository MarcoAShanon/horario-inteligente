"""
Serviço de Detecção e Gestão de Urgência
Horário Inteligente SaaS

Processa classificações de urgência, notifica médicos e gerencia alertas.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.conversa import Conversa, NivelUrgencia
from app.models.alerta_urgencia import AlertaUrgencia
from app.services.push_notification_service import push_service

logger = logging.getLogger(__name__)


class UrgenciaService:
    """Serviço para gerenciar detecção e resposta a urgências médicas."""

    # Resposta padrão para emergência crítica
    RESPOSTA_EMERGENCIA_CRITICA = """⚠️ *Entendi que você está passando por uma situação urgente.*

Estou notificando o Dr. {nome_medico} *AGORA MESMO* para que ele veja sua mensagem.

🚨 *Enquanto isso, se for uma emergência médica grave:*
📞 *SAMU:* 192
🚒 *Bombeiros:* 193
🏥 *Dirija-se ao pronto-socorro mais próximo*

O médico entrará em contato o mais breve possível. Por favor, não hesite em ligar para os serviços de emergência se sentir que precisa de ajuda imediata."""

    # Resposta para situação de atenção
    RESPOSTA_ATENCAO = """📋 *Entendi sua preocupação.*

Vou registrar essa informação e o Dr. {nome_medico} será informado sobre sua situação para poder avaliar.

Enquanto isso, {continuacao}"""

    def __init__(self, db: Session):
        self.db = db

    async def processar_urgencia(
        self,
        conversa_id: int,
        cliente_id: int,
        nivel: str,
        motivo: Optional[str],
        mensagem_paciente: str,
        paciente_telefone: str,
        paciente_nome: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processa uma classificação de urgência detectada pela IA.

        Args:
            conversa_id: ID da conversa
            cliente_id: ID do cliente (clínica)
            nivel: Nível de urgência (normal, atencao, critica)
            motivo: Motivo/descrição da urgência
            mensagem_paciente: Mensagem original do paciente
            paciente_telefone: Telefone do paciente
            paciente_nome: Nome do paciente (opcional)

        Returns:
            Dict com resultado do processamento e resposta modificada se necessário
        """
        result = {
            "urgencia_processada": False,
            "alerta_criado": False,
            "notificacao_enviada": False,
            "resposta_emergencia": None,
            "nivel": nivel
        }

        # Se for normal, não precisa fazer nada especial
        if nivel == "normal":
            return result

        try:
            # Buscar médico responsável para a conversa
            medico_info = self._buscar_medico_responsavel(cliente_id)

            # Atualizar conversa com flag de urgência
            self._atualizar_conversa_urgencia(conversa_id, nivel, motivo)

            # Criar alerta de urgência
            alerta = self._criar_alerta(
                conversa_id=conversa_id,
                cliente_id=cliente_id,
                medico_id=medico_info.get("id") if medico_info else None,
                nivel=nivel,
                motivo=motivo or f"Urgência detectada: {nivel}",
                mensagem_gatilho=mensagem_paciente[:500] if mensagem_paciente else None,
                paciente_telefone=paciente_telefone,
                paciente_nome=paciente_nome
            )
            result["alerta_criado"] = True
            result["alerta_id"] = alerta.id if alerta else None

            # Enviar notificação push para o médico
            if medico_info and medico_info.get("id"):
                notif_result = await self._enviar_notificacao_urgencia(
                    medico_id=medico_info["id"],
                    nivel=nivel,
                    paciente_nome=paciente_nome or "Paciente",
                    motivo=motivo
                )
                result["notificacao_enviada"] = notif_result.get("sent", 0) > 0

            # Se for crítica, gerar resposta de emergência
            if nivel == "critica":
                nome_medico = medico_info.get("nome", "responsável") if medico_info else "responsável"
                result["resposta_emergencia"] = self.RESPOSTA_EMERGENCIA_CRITICA.format(
                    nome_medico=nome_medico
                )

            result["urgencia_processada"] = True
            logger.info(f"🚨 Urgência processada: nivel={nivel}, conversa_id={conversa_id}")

        except Exception as e:
            logger.error(f"Erro ao processar urgência: {e}", exc_info=True)
            # Não falhar silenciosamente em urgências - logar mas não quebrar

        return result

    def _buscar_medico_responsavel(self, cliente_id: int) -> Optional[Dict]:
        """Busca o médico responsável para notificação."""
        try:
            # Por enquanto, busca o primeiro médico ativo do cliente
            # Futuramente pode ter lógica mais sofisticada (médico de plantão, etc)
            result = self.db.execute(text("""
                SELECT id, nome, telefone, email
                FROM medicos
                WHERE cliente_id = :cliente_id AND ativo = TRUE
                ORDER BY id
                LIMIT 1
            """), {"cliente_id": cliente_id}).fetchone()

            if result:
                return {
                    "id": result.id,
                    "nome": result.nome,
                    "telefone": result.telefone,
                    "email": result.email
                }
            return None

        except Exception as e:
            logger.error(f"Erro ao buscar médico responsável: {e}")
            return None

    def _atualizar_conversa_urgencia(self, conversa_id: int, nivel: str, motivo: Optional[str]):
        """Atualiza a conversa com flags de urgência."""
        try:
            nivel_enum = NivelUrgencia(nivel)
            self.db.execute(text("""
                UPDATE conversas
                SET urgencia_nivel = :nivel,
                    urgencia_detectada_em = NOW(),
                    urgencia_resolvida = FALSE,
                    urgencia_motivo = :motivo,
                    atualizado_em = NOW()
                WHERE id = :conversa_id
            """), {
                "nivel": nivel_enum.value,
                "motivo": motivo,
                "conversa_id": conversa_id
            })
            self.db.commit()
            logger.info(f"Conversa {conversa_id} atualizada com urgência: {nivel}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar conversa com urgência: {e}")

    def _criar_alerta(
        self,
        conversa_id: int,
        cliente_id: int,
        medico_id: Optional[int],
        nivel: str,
        motivo: str,
        mensagem_gatilho: Optional[str],
        paciente_telefone: str,
        paciente_nome: Optional[str]
    ) -> Optional[AlertaUrgencia]:
        """Cria um registro de alerta de urgência."""
        try:
            nivel_enum = NivelUrgencia(nivel)

            result = self.db.execute(text("""
                INSERT INTO alertas_urgencia
                (conversa_id, cliente_id, medico_id, nivel, motivo, mensagem_gatilho,
                 paciente_telefone, paciente_nome, notificacao_enviada, criado_em, atualizado_em)
                VALUES
                (:conversa_id, :cliente_id, :medico_id, :nivel, :motivo, :mensagem_gatilho,
                 :paciente_telefone, :paciente_nome, FALSE, NOW(), NOW())
                RETURNING id
            """), {
                "conversa_id": conversa_id,
                "cliente_id": cliente_id,
                "medico_id": medico_id,
                "nivel": nivel_enum.value,
                "motivo": motivo,
                "mensagem_gatilho": mensagem_gatilho,
                "paciente_telefone": paciente_telefone,
                "paciente_nome": paciente_nome
            })

            alerta_id = result.scalar()
            self.db.commit()

            logger.info(f"Alerta de urgência criado: id={alerta_id}, nivel={nivel}")

            # Retornar objeto simplificado
            alerta = type('AlertaUrgencia', (), {'id': alerta_id})()
            return alerta

        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar alerta de urgência: {e}")
            return None

    async def _enviar_notificacao_urgencia(
        self,
        medico_id: int,
        nivel: str,
        paciente_nome: str,
        motivo: Optional[str]
    ) -> Dict:
        """Envia notificação push de urgência para o médico."""
        try:
            # Títulos e ícones diferenciados por nível
            if nivel == "critica":
                titulo = "🚨 URGÊNCIA MÉDICA"
                corpo = f"{paciente_nome} precisa de atenção IMEDIATA!"
                if motivo:
                    corpo += f"\n{motivo[:100]}"
                tag = "urgencia-critica"
            else:  # atencao
                titulo = "⚠️ Atenção Necessária"
                corpo = f"{paciente_nome} relatou situação que merece sua atenção"
                if motivo:
                    corpo += f"\n{motivo[:100]}"
                tag = "urgencia-atencao"

            result = await push_service.send_notification(
                db=self.db,
                medico_id=medico_id,
                title=titulo,
                body=corpo,
                url="/static/conversas.html",
                tag=tag
            )

            if result.get("sent", 0) > 0:
                # Atualizar alerta para indicar que notificação foi enviada
                # (feito no método principal após criar alerta)
                logger.info(f"📱 Push de urgência enviado para médico {medico_id}")

            return result

        except Exception as e:
            logger.error(f"Erro ao enviar push de urgência: {e}")
            return {"sent": 0, "error": str(e)}

    def resolver_urgencia(
        self,
        conversa_id: int,
        resolvido_por: int,
        nota: Optional[str] = None
    ) -> bool:
        """
        Marca a urgência de uma conversa como resolvida.

        Args:
            conversa_id: ID da conversa
            resolvido_por: ID do usuário que resolveu
            nota: Nota opcional sobre a resolução

        Returns:
            True se atualizado com sucesso
        """
        try:
            # Atualizar conversa
            self.db.execute(text("""
                UPDATE conversas
                SET urgencia_resolvida = TRUE,
                    atualizado_em = NOW()
                WHERE id = :conversa_id
            """), {"conversa_id": conversa_id})

            # Atualizar alertas pendentes
            self.db.execute(text("""
                UPDATE alertas_urgencia
                SET resolvido = TRUE,
                    resolvido_em = NOW(),
                    resolvido_por = :resolvido_por,
                    resolucao_nota = :nota,
                    atualizado_em = NOW()
                WHERE conversa_id = :conversa_id AND resolvido = FALSE
            """), {
                "conversa_id": conversa_id,
                "resolvido_por": resolvido_por,
                "nota": nota
            })

            self.db.commit()
            logger.info(f"Urgência resolvida: conversa_id={conversa_id}, por={resolvido_por}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao resolver urgência: {e}")
            return False

    def listar_alertas_pendentes(self, cliente_id: int, limit: int = 50) -> list:
        """Lista alertas de urgência não resolvidos."""
        try:
            result = self.db.execute(text("""
                SELECT
                    au.id,
                    au.conversa_id,
                    au.nivel,
                    au.motivo,
                    au.mensagem_gatilho,
                    au.paciente_telefone,
                    au.paciente_nome,
                    au.criado_em,
                    au.visualizado,
                    c.status as conversa_status
                FROM alertas_urgencia au
                JOIN conversas c ON c.id = au.conversa_id
                WHERE au.cliente_id = :cliente_id
                  AND au.resolvido = FALSE
                ORDER BY
                    CASE au.nivel
                        WHEN 'critica' THEN 1
                        WHEN 'atencao' THEN 2
                        ELSE 3
                    END,
                    au.criado_em DESC
                LIMIT :limit
            """), {"cliente_id": cliente_id, "limit": limit})

            alertas = []
            for row in result:
                alertas.append({
                    "id": row.id,
                    "conversa_id": row.conversa_id,
                    "nivel": row.nivel,
                    "motivo": row.motivo,
                    "mensagem_gatilho": row.mensagem_gatilho,
                    "paciente_telefone": row.paciente_telefone,
                    "paciente_nome": row.paciente_nome,
                    "criado_em": row.criado_em.isoformat() if row.criado_em else None,
                    "visualizado": row.visualizado,
                    "conversa_status": row.conversa_status
                })

            return alertas

        except Exception as e:
            logger.error(f"Erro ao listar alertas pendentes: {e}")
            return []

    def marcar_alerta_visualizado(self, alerta_id: int, visualizado_por: int) -> bool:
        """Marca um alerta como visualizado."""
        try:
            self.db.execute(text("""
                UPDATE alertas_urgencia
                SET visualizado = TRUE,
                    visualizado_em = NOW(),
                    visualizado_por = :visualizado_por,
                    atualizado_em = NOW()
                WHERE id = :alerta_id
            """), {
                "alerta_id": alerta_id,
                "visualizado_por": visualizado_por
            })
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao marcar alerta como visualizado: {e}")
            return False

    def contar_alertas_pendentes(self, cliente_id: int) -> Dict[str, int]:
        """Conta alertas pendentes por nível."""
        try:
            result = self.db.execute(text("""
                SELECT
                    nivel,
                    COUNT(*) as total
                FROM alertas_urgencia
                WHERE cliente_id = :cliente_id
                  AND resolvido = FALSE
                GROUP BY nivel
            """), {"cliente_id": cliente_id})

            contagem = {"critica": 0, "atencao": 0, "total": 0}
            for row in result:
                contagem[row.nivel] = row.total
                contagem["total"] += row.total

            return contagem

        except Exception as e:
            logger.error(f"Erro ao contar alertas: {e}")
            return {"critica": 0, "atencao": 0, "total": 0}


# Factory function
def get_urgencia_service(db: Session) -> UrgenciaService:
    """Factory para obter instância do serviço."""
    return UrgenciaService(db)
