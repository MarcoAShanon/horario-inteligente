"""
Serviço de Push Notifications
Horário Inteligente SaaS

Gerencia envio de notificações push para médicos via Web Push API.
Gratuito e instantâneo - substitui notificações via WhatsApp (R$0,04/msg).
"""

import json
import os
import time
from typing import Optional, List
import logging

from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Serviço para gerenciar Push Notifications via Web Push API"""

    def __init__(self):
        self.vapid_private_key = os.getenv("VAPID_PRIVATE_KEY")
        self.vapid_public_key = os.getenv("VAPID_PUBLIC_KEY")
        self.vapid_claims = {
            "sub": f"mailto:{os.getenv('VAPID_CLAIM_EMAIL', 'contato@horariointeligente.com.br')}"
        }

        if not self.vapid_private_key or not self.vapid_public_key:
            logger.warning("⚠️ VAPID keys não configuradas. Push notifications desabilitadas.")

    def get_public_key(self) -> str:
        """Retorna a chave pública VAPID para o frontend"""
        return self.vapid_public_key or ""

    async def save_subscription(
        self,
        db: Session,
        medico_id: int,
        subscription_info: dict,
        user_agent: Optional[str] = None
    ) -> dict:
        """
        Salva ou atualiza subscription do médico.

        Args:
            db: Sessão do banco de dados
            medico_id: ID do médico
            subscription_info: Dados da subscription (endpoint, keys)
            user_agent: User-Agent do navegador (opcional)

        Returns:
            dict com status da operação
        """
        endpoint = subscription_info.get("endpoint")
        keys = subscription_info.get("keys", {})
        p256dh = keys.get("p256dh")
        auth = keys.get("auth")

        if not endpoint or not p256dh or not auth:
            logger.error("Dados de subscription incompletos")
            return {"success": False, "error": "Dados incompletos"}

        try:
            # Verificar se já existe subscription com este endpoint
            existing = db.execute(text("""
                SELECT id FROM push_subscriptions WHERE endpoint = :endpoint
            """), {"endpoint": endpoint}).fetchone()

            if existing:
                # Atualizar subscription existente
                db.execute(text("""
                    UPDATE push_subscriptions
                    SET medico_id = :medico_id,
                        p256dh_key = :p256dh,
                        auth_key = :auth,
                        user_agent = :user_agent,
                        ativo = TRUE,
                        atualizado_em = NOW()
                    WHERE endpoint = :endpoint
                """), {
                    "medico_id": medico_id,
                    "p256dh": p256dh,
                    "auth": auth,
                    "user_agent": user_agent,
                    "endpoint": endpoint
                })
                logger.info(f"✅ Subscription atualizada para médico {medico_id}")
            else:
                # Criar nova subscription
                db.execute(text("""
                    INSERT INTO push_subscriptions
                    (medico_id, endpoint, p256dh_key, auth_key, user_agent, ativo, criado_em, atualizado_em)
                    VALUES
                    (:medico_id, :endpoint, :p256dh, :auth, :user_agent, TRUE, NOW(), NOW())
                """), {
                    "medico_id": medico_id,
                    "endpoint": endpoint,
                    "p256dh": p256dh,
                    "auth": auth,
                    "user_agent": user_agent
                })
                logger.info(f"✅ Nova subscription criada para médico {medico_id}")

            db.commit()
            return {"success": True, "message": "Notificações ativadas com sucesso!"}

        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao salvar subscription: {e}")
            return {"success": False, "error": str(e)}

    async def remove_subscription(self, db: Session, endpoint: str) -> bool:
        """
        Remove/desativa subscription.

        Args:
            db: Sessão do banco de dados
            endpoint: Endpoint da subscription

        Returns:
            True se removida com sucesso
        """
        try:
            result = db.execute(text("""
                UPDATE push_subscriptions
                SET ativo = FALSE, atualizado_em = NOW()
                WHERE endpoint = :endpoint
            """), {"endpoint": endpoint})
            db.commit()

            if result.rowcount > 0:
                logger.info(f"🔕 Subscription desativada: {endpoint[:50]}...")
                return True
            return False

        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao remover subscription: {e}")
            return False

    async def send_notification(
        self,
        db: Session,
        medico_id: int,
        title: str,
        body: str,
        url: Optional[str] = None,
        icon: Optional[str] = None,
        tag: Optional[str] = None
    ) -> dict:
        """
        Envia push notification para todas as subscriptions ativas do médico.

        Args:
            db: Sessão do banco de dados
            medico_id: ID do médico
            title: Título da notificação
            body: Corpo da notificação
            url: URL para abrir ao clicar (opcional)
            icon: URL do ícone (opcional)
            tag: Tag para agrupar notificações (opcional)

        Returns:
            dict com resultado do envio
        """
        if not self.vapid_private_key:
            logger.warning("VAPID keys não configuradas")
            return {"success": False, "reason": "vapid_not_configured", "sent": 0}

        # Buscar subscriptions ativas do médico
        subscriptions = db.execute(text("""
            SELECT id, endpoint, p256dh_key, auth_key
            FROM push_subscriptions
            WHERE medico_id = :medico_id AND ativo = TRUE
        """), {"medico_id": medico_id}).fetchall()

        if not subscriptions:
            logger.debug(f"Nenhuma subscription ativa para médico {medico_id}")
            return {"success": False, "reason": "no_subscriptions", "sent": 0}

        # Montar payload
        payload = json.dumps({
            "title": title,
            "body": body,
            "url": url or "/static/dashboard.html",
            "icon": icon or "/static/icons/icon-192x192.png",
            "badge": "/static/icons/badge-72x72.png",
            "tag": tag or f"hi-{int(time.time())}",
            "timestamp": int(time.time() * 1000)
        })

        sent_count = 0
        failed_endpoints = []

        for sub in subscriptions:
            subscription_info = {
                "endpoint": sub.endpoint,
                "keys": {
                    "p256dh": sub.p256dh_key,
                    "auth": sub.auth_key
                }
            }

            try:
                webpush(
                    subscription_info=subscription_info,
                    data=payload,
                    vapid_private_key=self.vapid_private_key,
                    vapid_claims=self.vapid_claims
                )
                sent_count += 1
                logger.info(f"📱 Push enviado para médico {medico_id}")

            except WebPushException as e:
                logger.error(f"Erro ao enviar push: {e}")

                # Se endpoint expirou ou é inválido, desativar
                if e.response and e.response.status_code in [404, 410]:
                    try:
                        db.execute(text("""
                            UPDATE push_subscriptions
                            SET ativo = FALSE, atualizado_em = NOW()
                            WHERE id = :sub_id
                        """), {"sub_id": sub.id})
                        db.commit()
                        logger.info(f"🗑️ Subscription expirada removida: {sub.id}")
                    except Exception:
                        pass
                    failed_endpoints.append(sub.endpoint)

            except Exception as e:
                logger.error(f"Erro inesperado ao enviar push: {e}")
                failed_endpoints.append(sub.endpoint)

        return {
            "success": sent_count > 0,
            "sent": sent_count,
            "failed": len(failed_endpoints),
            "total": len(subscriptions)
        }

    async def send_to_all_active(
        self,
        db: Session,
        cliente_id: int,
        title: str,
        body: str,
        url: Optional[str] = None
    ) -> dict:
        """
        Envia push notification para todos os médicos ativos de um cliente.

        Útil para notificações broadcast (ex: manutenção do sistema).
        """
        # Buscar todos os médicos do cliente que têm subscriptions ativas
        medicos = db.execute(text("""
            SELECT DISTINCT ps.medico_id
            FROM push_subscriptions ps
            JOIN medicos m ON m.id = ps.medico_id
            WHERE m.cliente_id = :cliente_id
              AND m.ativo = TRUE
              AND ps.ativo = TRUE
        """), {"cliente_id": cliente_id}).fetchall()

        total_sent = 0
        for med in medicos:
            result = await self.send_notification(
                db=db,
                medico_id=med.medico_id,
                title=title,
                body=body,
                url=url
            )
            total_sent += result.get("sent", 0)

        return {"success": total_sent > 0, "total_sent": total_sent}

    def get_subscription_count(self, db: Session, medico_id: int) -> int:
        """Retorna quantidade de subscriptions ativas do médico"""
        result = db.execute(text("""
            SELECT COUNT(*) FROM push_subscriptions
            WHERE medico_id = :medico_id AND ativo = TRUE
        """), {"medico_id": medico_id}).scalar()
        return result or 0


# Instância singleton
push_service = PushNotificationService()
