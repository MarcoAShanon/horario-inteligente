"""
Serviço de Monitoramento do WhatsApp
Verifica status da conexão e envia alertas se desconectar
"""
import logging
import os
import aiohttp
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WhatsAppMonitor:
    """
    Monitora conexão do WhatsApp e envia alertas
    """

    def __init__(self):
        self.evolution_url = "http://localhost:8080"
        self.api_key = os.getenv("EVOLUTION_API_KEY", "")
        self.instances = ["HorarioInteligente"]  # Lista de instâncias para monitorar
        self.last_status = {}

    async def verificar_status_instancia(self, instance_name: str) -> Dict[str, Any]:
        """
        Verifica status de uma instância WhatsApp

        Returns:
            Dict com status: open/close/connecting e informações adicionais
        """
        try:
            url = f"{self.evolution_url}/instance/fetchInstances"
            headers = {"apikey": self.api_key}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        instances = await response.json()

                        # Buscar instância específica
                        for inst in instances:
                            if inst.get("instance", {}).get("instanceName") == instance_name:
                                status = inst.get("instance", {}).get("status", "unknown")

                                return {
                                    "instance": instance_name,
                                    "status": status,
                                    "connected": status == "open",
                                    "timestamp": datetime.now().isoformat()
                                }

                        return {
                            "instance": instance_name,
                            "status": "not_found",
                            "connected": False,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        logger.error(f"❌ Erro ao consultar Evolution API: {response.status}")
                        return {
                            "instance": instance_name,
                            "status": "error",
                            "connected": False,
                            "error": f"HTTP {response.status}",
                            "timestamp": datetime.now().isoformat()
                        }

        except Exception as e:
            logger.error(f"❌ Exceção ao verificar status: {e}")
            return {
                "instance": instance_name,
                "status": "error",
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def verificar_todas_instancias(self) -> Dict[str, Any]:
        """
        Verifica status de todas as instâncias configuradas

        Returns:
            Dict com estatísticas e lista de instâncias
        """
        resultados = []
        desconectadas = []

        for instance in self.instances:
            status = await self.verificar_status_instancia(instance)
            resultados.append(status)

            # Detectar mudança de status
            status_anterior = self.last_status.get(instance, {}).get("status")
            status_atual = status["status"]

            if status_anterior == "open" and status_atual == "close":
                logger.error(f"🚨 ALERTA: Instância {instance} DESCONECTOU!")
                desconectadas.append(instance)
            elif status_anterior == "close" and status_atual == "open":
                logger.info(f"✅ RECUPERADO: Instância {instance} reconectou")

            # Atualizar cache
            self.last_status[instance] = status

            # Log do status atual
            if status["connected"]:
                logger.info(f"✅ {instance}: Conectado")
            else:
                logger.warning(f"⚠️ {instance}: Desconectado ({status['status']})")

        return {
            "total": len(resultados),
            "conectadas": sum(1 for r in resultados if r["connected"]),
            "desconectadas": len(resultados) - sum(1 for r in resultados if r["connected"]),
            "alertas": desconectadas,
            "instancias": resultados,
            "timestamp": datetime.now().isoformat()
        }

    async def enviar_alerta_desconexao(self, instance_name: str):
        """
        Envia alerta quando detectar desconexão

        Futuramente pode enviar:
        - Email para admin
        - Notificação push
        - Telegram
        - SMS
        """
        logger.error(f"""
        ═══════════════════════════════════════
        🚨 ALERTA DE DESCONEXÃO WHATSAPP 🚨
        ═══════════════════════════════════════
        Instância: {instance_name}
        Horário: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

        ⚠️ O WhatsApp foi desconectado!

        Ações necessárias:
        1. Acesse: https://horariointeligente.com.br/static/reconectar-whatsapp.html
        2. Escaneie o novo QR Code
        3. Aguarde confirmação

        Status atual: DESCONECTADO
        ═══════════════════════════════════════
        """)

        # TODO: Implementar envio de email/telegram/sms
        # await self.enviar_email_alerta(instance_name)
        # await self.enviar_telegram_alerta(instance_name)

# Instância global
whatsapp_monitor = WhatsAppMonitor()
