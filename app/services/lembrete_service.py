"""
Serviço de Lembretes Inteligentes com IA Conversacional
Horário Inteligente - WhatsApp Business API Oficial

Gerencia o ciclo de vida de lembretes de consultas:
- Criação automática ao agendar
- Envio via templates Meta (fora da janela 24h)
- Processamento de respostas com IA
- Interpretação natural de intenções
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models import Agendamento, Paciente, Medico, Cliente
from app.models.lembrete import Lembrete, TipoLembrete, StatusLembrete
from app.services.whatsapp_official_service import WhatsAppOfficialService
from app.services.whatsapp_template_service import get_template_service
from app.services.anthropic_service import AnthropicService
from app.services.websocket_manager import websocket_manager
from app.database import SessionLocal
from app.utils.timezone_helper import now_brazil, format_brazil
import pytz

TZ_BRAZIL = pytz.timezone('America/Sao_Paulo')

logger = logging.getLogger(__name__)

# Templates aprovados na Meta (atualizados em 26/01/2026)
# lembrete_24h: 4 variáveis (paciente, medico, data, hora) + botões
# lembrete_2h: 3 variáveis (paciente, medico, hora) + botões
TEMPLATE_LEMBRETE_24H = os.getenv("WHATSAPP_TEMPLATE_LEMBRETE_24H", "lembrete_24h")
TEMPLATE_LEMBRETE_2H = os.getenv("WHATSAPP_TEMPLATE_LEMBRETE_2H", "lembrete_2h")  # Campo no BD ainda é "3h"
TEMPLATE_LEMBRETE_1H = None  # Não temos template de 1h aprovado


class LembreteService:
    """
    Serviço para gerenciamento de lembretes inteligentes.

    Funcionalidades:
    - Criar lembretes automaticamente ao agendar
    - Enviar via WhatsApp Business API Oficial
    - Usar templates Meta (obrigatório fora da janela 24h)
    - Processar respostas com IA conversacional
    - Interpretar intenções naturalmente
    """

    def __init__(self):
        self.whatsapp = WhatsAppOfficialService()
        self.template_service = get_template_service()

    # ==================== CRIAÇÃO DE LEMBRETES ====================

    def criar_lembretes_para_agendamento(
        self,
        db: Session,
        agendamento_id: int,
        tipos: List[str] = None
    ) -> List[Lembrete]:
        """
        Cria lembretes para um agendamento.

        Por padrão, cria lembrete de 24h. Outros são criados sob demanda.

        Args:
            db: Sessão do banco de dados
            agendamento_id: ID do agendamento
            tipos: Lista de tipos de lembrete (default: ["24h"])

        Returns:
            Lista de lembretes criados
        """
        if tipos is None:
            tipos = [TipoLembrete.LEMBRETE_24H.value]

        lembretes_criados = []

        for tipo in tipos:
            # Verificar se já existe
            existente = db.query(Lembrete).filter(
                Lembrete.agendamento_id == agendamento_id,
                Lembrete.tipo == tipo
            ).first()

            if existente:
                logger.info(f"Lembrete {tipo} já existe para agendamento {agendamento_id}")
                continue

            lembrete = Lembrete(
                agendamento_id=agendamento_id,
                tipo=tipo,
                status=StatusLembrete.PENDENTE.value
            )
            db.add(lembrete)
            lembretes_criados.append(lembrete)

        if lembretes_criados:
            db.commit()
            logger.info(f"✅ Criados {len(lembretes_criados)} lembretes para agendamento {agendamento_id}")

        return lembretes_criados

    def criar_lembrete_1h(self, db: Session, agendamento_id: int) -> Optional[Lembrete]:
        """
        Cria lembrete de 1h quando solicitado pelo paciente.

        Args:
            db: Sessão do banco de dados
            agendamento_id: ID do agendamento

        Returns:
            Lembrete criado ou None se já existir
        """
        lembretes = self.criar_lembretes_para_agendamento(
            db, agendamento_id, [TipoLembrete.LEMBRETE_1H.value]
        )
        return lembretes[0] if lembretes else None

    # ==================== ENVIO DE LEMBRETES ====================

    async def enviar_lembrete(
        self,
        db: Session,
        lembrete: Lembrete
    ) -> Tuple[bool, str]:
        """
        Envia um lembrete específico via WhatsApp usando templates aprovados.

        Templates disponíveis:
        - lembrete_24h: 4 variáveis (paciente, medico, data, hora)
        - lembrete_2h: 3 variáveis (paciente, medico, hora)

        Args:
            db: Sessão do banco de dados
            lembrete: Objeto Lembrete a ser enviado

        Returns:
            Tuple (sucesso, mensagem_erro_ou_id)
        """
        try:
            # Carregar dados do agendamento
            agendamento = db.query(Agendamento).filter(
                Agendamento.id == lembrete.agendamento_id
            ).first()

            if not agendamento:
                return False, "Agendamento não encontrado"

            paciente = db.query(Paciente).filter(
                Paciente.id == agendamento.paciente_id
            ).first()

            medico = db.query(Medico).filter(
                Medico.id == agendamento.medico_id
            ).first()

            if not paciente or not medico:
                return False, "Paciente ou médico não encontrado"

            # Extrair primeiro nome do paciente
            primeiro_nome = paciente.nome.split()[0] if paciente.nome else "Paciente"

            # Formatar nome do médico (não duplicar prefixo se já tiver Dr/Dra no nome)
            if medico.nome and medico.nome.lower().startswith(("dr.", "dr ", "dra.", "dra ")):
                nome_medico = medico.nome
            elif medico.nome:
                nome_medico = f"Dr(a). {medico.nome}"
            else:
                nome_medico = "Médico"

            # Formatar data e hora SEPARADAMENTE (nossos templates usam variáveis separadas)
            data_formatada = agendamento.data_hora.strftime("%d/%m/%Y")
            hora_formatada = agendamento.data_hora.strftime("%H:%M")

            # Definir contexto de billing para logging de mensagens WhatsApp
            try:
                from app.services.whatsapp_billing_service import set_billing_context
                set_billing_context(medico.cliente_id)
            except Exception:
                pass

            # Enviar baseado no tipo de lembrete
            if lembrete.tipo == TipoLembrete.LEMBRETE_24H.value:
                # Template lembrete_24h: 4 variáveis (paciente, medico, data, hora)
                result = await self.template_service.enviar_lembrete_24h(
                    telefone=paciente.telefone,
                    paciente=primeiro_nome,
                    medico=nome_medico,
                    data=data_formatada,
                    hora=hora_formatada
                )
                template_name = TEMPLATE_LEMBRETE_24H

            elif lembrete.tipo == TipoLembrete.LEMBRETE_3H.value:
                # Template lembrete_2h: 3 variáveis (paciente, medico, hora)
                # Campo no BD ainda é "3h" mas usamos template de 2h
                result = await self.template_service.enviar_lembrete_2h(
                    telefone=paciente.telefone,
                    paciente=primeiro_nome,
                    medico=nome_medico,
                    hora=hora_formatada
                )
                template_name = TEMPLATE_LEMBRETE_2H

            else:
                # Lembrete de 1h - não temos template aprovado
                # Ignora silenciosamente ou envia mensagem de texto se dentro da janela 24h
                logger.warning(
                    f"⚠️ Lembrete de 1h ignorado - template não disponível "
                    f"(agendamento {agendamento.id})"
                )
                return False, "Template de 1h não disponível"

            if result.success:
                lembrete.marcar_enviado(
                    message_id=result.message_id,
                    template=template_name
                )
                db.commit()

                logger.info(
                    f"✅ Lembrete {lembrete.tipo} enviado para {paciente.nome} "
                    f"(agendamento {agendamento.id}) via {template_name}"
                )

                # Notificar painel via WebSocket
                try:
                    from app.models.conversa import Conversa
                    from app.models.mensagem import Mensagem, DirecaoMensagem, RemetenteMensagem, TipoMensagem
                    from app.services.conversa_service import ConversaService

                    # Buscar ou criar conversa
                    conversa = db.query(Conversa).filter(
                        Conversa.paciente_telefone.like(f"%{paciente.telefone[-8:]}%"),
                        Conversa.cliente_id == medico.cliente_id
                    ).first()

                    if conversa:
                        # Montar texto do lembrete para exibição
                        if lembrete.tipo == TipoLembrete.LEMBRETE_24H.value:
                            texto_lembrete = f"🔔 Lembrete: Olá {primeiro_nome}! Sua consulta com {nome_medico} está confirmada para amanhã, {data_formatada} às {hora_formatada}."
                        else:
                            texto_lembrete = f"🔔 Lembrete: Olá {primeiro_nome}! Sua consulta com {nome_medico} é HOJE às {hora_formatada}. Estamos te aguardando!"

                        # Salvar mensagem no banco
                        mensagem_lembrete = ConversaService.adicionar_mensagem(
                            db=db,
                            conversa_id=conversa.id,
                            direcao=DirecaoMensagem.SAIDA,
                            remetente=RemetenteMensagem.SISTEMA,
                            conteudo=texto_lembrete,
                            tipo=TipoMensagem.TEXTO
                        )

                        # Notificar via WebSocket
                        timestamp_brasil = datetime.now(TZ_BRAZIL).isoformat()
                        await websocket_manager.send_nova_mensagem(
                            cliente_id=medico.cliente_id,
                            conversa_id=conversa.id,
                            mensagem={
                                "id": mensagem_lembrete.id,
                                "direcao": "saida",
                                "remetente": "sistema",
                                "tipo": "texto",
                                "conteudo": texto_lembrete,
                                "timestamp": timestamp_brasil
                            }
                        )
                        logger.info(f"📢 WebSocket: Lembrete notificado ao painel (conversa {conversa.id})")
                except Exception as ws_error:
                    logger.warning(f"⚠️ Erro ao notificar painel via WebSocket: {ws_error}")

                return True, result.message_id

            else:
                lembrete.marcar_erro(result.error)
                db.commit()

                logger.error(f"❌ Erro ao enviar lembrete: {result.error}")
                return False, result.error

        except Exception as e:
            logger.error(f"❌ Exceção ao enviar lembrete: {e}")
            lembrete.marcar_erro(str(e))
            db.commit()
            return False, str(e)

    async def enviar_mensagem_conversacional(
        self,
        db: Session,
        telefone: str,
        mensagem: str
    ) -> Tuple[bool, str]:
        """
        Envia mensagem conversacional (dentro da janela 24h).

        Usado para continuar a conversa após resposta do paciente.

        Args:
            db: Sessão do banco
            telefone: Número do paciente
            mensagem: Texto da mensagem

        Returns:
            Tuple (sucesso, message_id ou erro)
        """
        try:
            result = await self.whatsapp.send_text(
                to=telefone,
                message=mensagem
            )

            if result.success:
                logger.info(f"✅ Mensagem enviada para {telefone}")
                return True, result.message_id
            else:
                logger.error(f"❌ Erro ao enviar mensagem: {result.error}")
                return False, result.error

        except Exception as e:
            logger.error(f"❌ Exceção ao enviar mensagem: {e}")
            return False, str(e)

    # ==================== PROCESSAMENTO DE RESPOSTAS ====================

    async def processar_resposta_lembrete(
        self,
        db: Session,
        telefone: str,
        texto_resposta: str,
        cliente_id: int
    ) -> Dict[str, Any]:
        """
        Processa resposta do paciente a um lembrete.

        Usa IA para interpretar a intenção e gerar resposta apropriada.

        Args:
            db: Sessão do banco
            telefone: Telefone do paciente
            texto_resposta: Texto da mensagem do paciente
            cliente_id: ID do cliente (tenant)

        Returns:
            Dict com resposta e ações a tomar
        """
        # Buscar lembrete pendente de resposta para este telefone
        lembrete = self._buscar_lembrete_aguardando_resposta(db, telefone)

        if not lembrete:
            # Não há lembrete aguardando resposta
            return {
                "tem_lembrete_pendente": False,
                "resposta": None,
                "acao": None
            }

        # Carregar dados do agendamento
        agendamento = db.query(Agendamento).filter(
            Agendamento.id == lembrete.agendamento_id
        ).first()

        paciente = db.query(Paciente).filter(
            Paciente.id == agendamento.paciente_id
        ).first()

        medico = db.query(Medico).filter(
            Medico.id == agendamento.medico_id
        ).first()

        # Interpretar intenção com IA
        intencao, confianca = await self._interpretar_intencao(
            texto_resposta,
            cliente_id,
            db
        )

        logger.info(f"🧠 Intenção detectada: {intencao} (confiança: {confianca})")

        # Registrar resposta
        lembrete.registrar_resposta(texto_resposta, intencao)

        # Gerar resposta baseada na intenção
        resposta, acao = await self._gerar_resposta_ia(
            intencao=intencao,
            paciente=paciente,
            medico=medico,
            agendamento=agendamento,
            texto_original=texto_resposta,
            cliente_id=cliente_id,
            db=db
        )

        # Atualizar status do agendamento se necessário
        if intencao == "confirmar":
            agendamento.status = "confirmado"
            db.commit()
        elif intencao == "cancelar":
            agendamento.status = "cancelado"
            db.commit()

        # Se pediu lembrete de 1h
        if "lembrete" in texto_resposta.lower() and "1" in texto_resposta:
            lembrete.lembrete_1h_solicitado = True
            self.criar_lembrete_1h(db, agendamento.id)

        db.commit()

        return {
            "tem_lembrete_pendente": True,
            "lembrete_id": lembrete.id,
            "agendamento_id": agendamento.id,
            "intencao": intencao,
            "confianca": confianca,
            "resposta": resposta,
            "acao": acao
        }

    async def _interpretar_intencao(
        self,
        texto: str,
        cliente_id: int,
        db: Session
    ) -> Tuple[str, float]:
        """
        Usa IA para interpretar a intenção do paciente.

        Retorna: (intencao, confianca)
        Intenções possíveis: confirmar, remarcar, cancelar, duvida
        """
        prompt = f"""Analise a seguinte resposta de um paciente a um lembrete de consulta médica e determine a intenção.

Resposta do paciente: "{texto}"

Classifique a intenção em UMA das seguintes categorias:
- confirmar: paciente confirma que vai à consulta (ex: "sim", "confirmo", "vou sim", "estarei lá", "ok", "pode confirmar")
- remarcar: paciente quer mudar data/horário (ex: "preciso remarcar", "não posso nesse horário", "tem outro dia?")
- cancelar: paciente quer cancelar definitivamente (ex: "cancela", "não vou mais", "desisto", "não quero")
- duvida: paciente tem dúvida ou pergunta (ex: "qual endereço?", "quanto custa?", "precisa de jejum?")

Responda APENAS com a intenção em uma palavra (confirmar/remarcar/cancelar/duvida) seguida de um número de 0 a 1 indicando confiança.
Formato: intencao,confianca

Exemplo: confirmar,0.95"""

        try:
            anthropic = AnthropicService(db, cliente_id)
            resultado = anthropic.processar_mensagem(
                mensagem=prompt,
                telefone="sistema",
                contexto_conversa=[]
            )

            resposta_ia = resultado.get("resposta", "duvida,0.5").strip().lower()

            # Parsear resposta
            partes = resposta_ia.split(",")
            if len(partes) >= 2:
                intencao = partes[0].strip()
                try:
                    confianca = float(partes[1].strip())
                except:
                    confianca = 0.5
            else:
                intencao = partes[0].strip() if partes else "duvida"
                confianca = 0.5

            # Validar intenção
            intencoes_validas = ["confirmar", "remarcar", "cancelar", "duvida"]
            if intencao not in intencoes_validas:
                intencao = "duvida"

            return intencao, confianca

        except Exception as e:
            logger.error(f"❌ Erro ao interpretar intenção: {e}")
            return "duvida", 0.3

    async def _gerar_resposta_ia(
        self,
        intencao: str,
        paciente,
        medico,
        agendamento,
        texto_original: str,
        cliente_id: int,
        db: Session
    ) -> Tuple[str, str]:
        """
        Gera resposta conversacional baseada na intenção.

        Retorna: (texto_resposta, acao)
        """
        data_hora = format_brazil(agendamento.data_hora)
        primeiro_nome = paciente.nome.split()[0]

        # Evitar duplicação de prefixo (ex: "Dr(a). Dr. João")
        if medico.nome and medico.nome.lower().startswith(("dr.", "dr ", "dra.", "dra ")):
            nome_medico = medico.nome
        elif medico.nome:
            nome_medico = f"Dr(a). {medico.nome}"
        else:
            nome_medico = "Médico"

        if intencao == "confirmar":
            resposta = (
                f"Perfeito, {primeiro_nome}! Sua consulta com {nome_medico} "
                f"está confirmada para {data_hora}. "
                f"Qualquer coisa, é só me chamar aqui. Até lá!"
            )
            acao = "confirmar_agendamento"

        elif intencao == "remarcar":
            resposta = (
                f"Entendi, {primeiro_nome}. Vou te ajudar a remarcar sua consulta. "
                f"Qual data e horário ficaria melhor para você?"
            )
            acao = "iniciar_remarcacao"

        elif intencao == "cancelar":
            resposta = (
                f"Tudo bem, {primeiro_nome}. Sua consulta com {nome_medico} "
                f"do dia {data_hora} foi cancelada. "
                f"Se precisar agendar novamente no futuro, é só me chamar!"
            )
            acao = "cancelar_agendamento"

        else:  # duvida ou outro
            # Usar IA para responder a dúvida de forma conversacional
            prompt = f"""Você é a assistente virtual de uma clínica médica. O paciente {primeiro_nome} tem uma consulta marcada com {nome_medico} para {data_hora}.

O paciente enviou a seguinte mensagem em resposta ao lembrete: "{texto_original}"

Responda de forma amigável, breve e direta. Se for uma dúvida que você não sabe responder, diga que vai verificar e retornar.

Sempre termine perguntando se confirma a presença na consulta."""

            try:
                anthropic = AnthropicService(db, cliente_id)
                resultado = anthropic.processar_mensagem(
                    mensagem=prompt,
                    telefone="sistema",
                    contexto_conversa=[]
                )
                resposta = resultado.get("resposta", "")
            except:
                resposta = (
                    f"Olá, {primeiro_nome}! Vi sua mensagem. "
                    f"Deixa eu verificar isso para você. "
                    f"Enquanto isso, pode confirmar sua presença na consulta de {data_hora}?"
                )
            acao = "aguardar_resposta"

        return resposta, acao

    def _buscar_lembrete_aguardando_resposta(
        self,
        db: Session,
        telefone: str
    ) -> Optional[Lembrete]:
        """
        Busca lembrete aguardando resposta para um telefone.
        """
        # Buscar paciente pelo telefone
        telefone_limpo = ''.join(filter(str.isdigit, telefone))

        paciente = db.query(Paciente).filter(
            Paciente.telefone.like(f"%{telefone_limpo[-8:]}%")
        ).first()

        if not paciente:
            return None

        # Buscar agendamentos do paciente
        agendamentos = db.query(Agendamento).filter(
            Agendamento.paciente_id == paciente.id,
            Agendamento.status.in_(["agendado", "confirmado"])
        ).all()

        if not agendamentos:
            return None

        agendamento_ids = [a.id for a in agendamentos]

        # Buscar lembrete aguardando resposta
        lembrete = db.query(Lembrete).filter(
            Lembrete.agendamento_id.in_(agendamento_ids),
            Lembrete.status == StatusLembrete.ENVIADO.value
        ).order_by(Lembrete.enviado_em.desc()).first()

        return lembrete

    # ==================== PROCESSAMENTO EM LOTE ====================

    async def processar_lembretes_pendentes(self) -> Dict[str, Any]:
        """
        Processa todos os lembretes pendentes de envio.

        Chamado pelo scheduler periodicamente.

        Returns:
            Estatísticas de processamento
        """
        stats = {
            "24h": {"enviados": 0, "erros": 0},
            "3h": {"enviados": 0, "erros": 0},
            "1h": {"enviados": 0, "erros": 0},
            "timestamp": datetime.now().isoformat()
        }

        db = SessionLocal()
        try:
            now = now_brazil()

            # Processar lembretes de 24h
            stats["24h"] = await self._processar_tipo_lembrete(
                db, TipoLembrete.LEMBRETE_24H.value,
                now + timedelta(hours=23, minutes=50),
                now + timedelta(hours=24, minutes=10)
            )

            # Processar lembretes de 2h (campo no BD ainda é "3h" por compatibilidade)
            # Janela: consultas entre 1h50 e 2h10 a partir de agora
            stats["3h"] = await self._processar_tipo_lembrete(
                db, TipoLembrete.LEMBRETE_3H.value,
                now + timedelta(hours=1, minutes=50),
                now + timedelta(hours=2, minutes=10)
            )

            # Lembrete de 1h desativado - não temos template aprovado
            # stats["1h"] permanece zerado
            logger.debug("⚠️ Lembrete de 1h desativado - template não disponível")

            logger.info(f"✅ Processamento de lembretes concluído: {stats}")

        except Exception as e:
            logger.error(f"❌ Erro ao processar lembretes: {e}")

        finally:
            db.close()

        return stats

    async def _processar_tipo_lembrete(
        self,
        db: Session,
        tipo: str,
        janela_inicio: datetime,
        janela_fim: datetime
    ) -> Dict[str, int]:
        """
        Processa lembretes de um tipo específico.
        Usa SELECT FOR UPDATE para evitar envios duplicados em caso de race condition.
        """
        enviados = 0
        erros = 0

        # Buscar agendamentos na janela de tempo
        agendamentos = db.query(Agendamento).filter(
            and_(
                Agendamento.data_hora >= janela_inicio,
                Agendamento.data_hora <= janela_fim,
                Agendamento.status.in_(["agendado", "confirmado"])
            )
        ).all()

        for agendamento in agendamentos:
            try:
                # Usar with_for_update para lock de linha — evita race condition
                lembrete = db.query(Lembrete).filter(
                    Lembrete.agendamento_id == agendamento.id,
                    Lembrete.tipo == tipo
                ).with_for_update(skip_locked=True).first()

                # Criar lembrete se não existir
                if not lembrete:
                    lembrete = Lembrete(
                        agendamento_id=agendamento.id,
                        tipo=tipo,
                        status=StatusLembrete.PENDENTE.value
                    )
                    db.add(lembrete)
                    db.flush()  # flush para obter o ID sem commit

                # Enviar apenas se pendente (double-check após lock)
                if lembrete.status == StatusLembrete.PENDENTE.value:
                    sucesso, _ = await self.enviar_lembrete(db, lembrete)
                    if sucesso:
                        enviados += 1
                    else:
                        erros += 1

                db.commit()

            except Exception as e:
                db.rollback()
                logger.error(f"❌ Erro ao processar lembrete {tipo} para agendamento {agendamento.id}: {e}")
                erros += 1

        return {"enviados": enviados, "erros": erros}

    # ==================== CONSULTAS ====================

    def get_lembretes_agendamento(
        self,
        db: Session,
        agendamento_id: int
    ) -> List[Lembrete]:
        """
        Retorna todos os lembretes de um agendamento.
        """
        return db.query(Lembrete).filter(
            Lembrete.agendamento_id == agendamento_id
        ).order_by(Lembrete.tipo).all()

    def get_estatisticas(self, db: Session) -> Dict[str, Any]:
        """
        Retorna estatísticas de lembretes.
        """
        total = db.query(Lembrete).count()
        pendentes = db.query(Lembrete).filter(
            Lembrete.status == StatusLembrete.PENDENTE.value
        ).count()
        enviados = db.query(Lembrete).filter(
            Lembrete.status == StatusLembrete.ENVIADO.value
        ).count()
        confirmados = db.query(Lembrete).filter(
            Lembrete.status == StatusLembrete.CONFIRMADO.value
        ).count()
        remarcados = db.query(Lembrete).filter(
            Lembrete.status == StatusLembrete.REMARCAR.value
        ).count()
        cancelados = db.query(Lembrete).filter(
            Lembrete.status == StatusLembrete.CANCELAR.value
        ).count()

        return {
            "total": total,
            "pendentes": pendentes,
            "enviados_aguardando": enviados,
            "confirmados": confirmados,
            "remarcados": remarcados,
            "cancelados": cancelados,
            "timestamp": datetime.now().isoformat()
        }


# Instância global do serviço
lembrete_service = LembreteService()
