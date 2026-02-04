"""
Serviço de Integração com Anthropic IA - VERSÃO REAL
Sistema de agendamento médico SaaS - Pro-Saúde
Desenvolvido por Marco
"""

import json
import re
import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.cliente import Cliente
from app.models.medico import Medico
from app.models.paciente import Paciente
from app.models.convenio import Convenio
from app.services.agendamento_service import AgendamentoService

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AnthropicService:
    """Serviço para processamento de mensagens com IA Anthropic REAL."""
    
    def __init__(self, db: Session, cliente_id: int):
        self.db = db
        self.cliente_id = cliente_id
        
        # Configurar cliente Anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key and ANTHROPIC_AVAILABLE:
            self.anthropic = Anthropic(api_key=api_key)
            self.use_real_ai = True
        else:
            self.anthropic = None
            self.use_real_ai = False
    
    def processar_mensagem(self, mensagem: str, telefone: str, contexto_conversa: List[Dict] = None) -> Dict[str, Any]:
        """Processa uma mensagem do usuário e retorna resposta estruturada."""
        
        # Obter contexto da clínica
        contexto_clinica = self._obter_contexto_clinica()
        
        # Identificar paciente se existir
        paciente = self._obter_paciente_por_telefone(telefone)
        
        if self.use_real_ai:
            return self._processar_com_anthropic(mensagem, contexto_clinica, paciente, contexto_conversa)
        else:
            return self._processar_com_regras(mensagem, contexto_clinica, paciente)
    
    def _processar_com_anthropic(self, mensagem: str, contexto_clinica: Dict, paciente: Optional, contexto_conversa: List[Dict]) -> Dict[str, Any]:
        """Processa mensagem usando IA real da Anthropic."""
        
        try:
            # Construir prompt
            prompt = self._construir_prompt(mensagem, contexto_clinica, paciente, contexto_conversa)
            
            # Chamar Anthropic
            model = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
            response = self.anthropic.messages.create(
                model=model,
                max_tokens=1000,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            resposta_ia = response.content[0].text
            
            # Processar resposta da IA
            return self._processar_resposta_ia(resposta_ia)
            
        except Exception as e:
            print(f"Erro na Anthropic IA: {e}")
            # Fallback para regras simples
            return self._processar_com_regras(mensagem, contexto_clinica, paciente)

    def _extrair_data_e_horarios_disponiveis(self, mensagem: str, contexto_conversa: List[Dict], contexto_clinica: Dict) -> str:
        """
        Extrai datas mencionadas na conversa e busca horários disponíveis.
        Retorna string com horários disponíveis para incluir no prompt.
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Buscar data mencionada no contexto ou mensagem atual
            data_encontrada = None
            medico_id = None

            logger.info(f"[Horários] Buscando data na mensagem: {mensagem[:50]}...")

            # Padrão para datas no formato DD/MM/YYYY
            padrao_data = r'(\d{2}/\d{2}/\d{4})'

            # Verificar na mensagem atual
            match = re.search(padrao_data, mensagem)
            if match:
                logger.info(f"[Horários] Data encontrada na mensagem: {match.group(1)}")
                try:
                    data_encontrada = datetime.strptime(match.group(1), "%d/%m/%Y").date()
                except ValueError:
                    pass

            # Se não encontrou no formato completo, tentar formato curto: D/M, DD/M, D/MM, DD/MM (sem ano)
            if not data_encontrada:
                padrao_data_curta = r'(?<!\d)(\d{1,2})/(\d{1,2})(?!/|\d)'
                match_curta = re.search(padrao_data_curta, mensagem)
                if match_curta:
                    try:
                        import pytz
                        tz_brazil = pytz.timezone('America/Sao_Paulo')
                        hoje = datetime.now(tz_brazil).date()

                        dia = int(match_curta.group(1))
                        mes = int(match_curta.group(2))
                        # Inferir ano: se a data já passou neste ano, usar próximo ano
                        ano = hoje.year
                        candidata = date(ano, mes, dia)
                        if candidata < hoje:
                            candidata = date(ano + 1, mes, dia)
                        data_encontrada = candidata
                        logger.info(f"[Horários] Data curta encontrada: {match_curta.group(0)} -> {data_encontrada}")
                    except (ValueError, Exception) as e:
                        logger.warning(f"[Horários] Erro ao parsear data curta '{match_curta.group(0)}': {e}")

            # Se não encontrou data em nenhum formato numérico, tentar detectar expressões de tempo
            if not data_encontrada:
                import pytz
                mensagem_lower = mensagem.lower()
                # IMPORTANTE: Usar timezone do Brasil para calcular "hoje" corretamente
                tz_brazil = pytz.timezone('America/Sao_Paulo')
                hoje = datetime.now(tz_brazil).date()

                # Primeiro: detectar "hoje", "amanhã", "depois de amanhã"
                if 'hoje' in mensagem_lower:
                    data_encontrada = hoje
                    logger.info(f"[Horários] 'hoje' detectado -> {data_encontrada}")
                elif 'amanhã' in mensagem_lower or 'amanha' in mensagem_lower:
                    data_encontrada = hoje + timedelta(days=1)
                    logger.info(f"[Horários] 'amanhã' detectado -> {data_encontrada}")
                elif 'depois de amanhã' in mensagem_lower or 'depois de amanha' in mensagem_lower:
                    data_encontrada = hoje + timedelta(days=2)
                    logger.info(f"[Horários] 'depois de amanhã' detectado -> {data_encontrada}")

                # Segundo: detectar dias da semana
                if not data_encontrada:
                    dias_semana_map = {
                        'segunda': 0, 'segunda-feira': 0,
                        'terça': 1, 'terca': 1, 'terça-feira': 1, 'terca-feira': 1,
                        'quarta': 2, 'quarta-feira': 2,
                        'quinta': 3, 'quinta-feira': 3,
                        'sexta': 4, 'sexta-feira': 4,
                        'sábado': 5, 'sabado': 5,
                        'domingo': 6
                    }

                    for dia_nome, dia_num in dias_semana_map.items():
                        if dia_nome in mensagem_lower:
                            # Calcular a próxima ocorrência desse dia
                            dias_ate_proximo = (dia_num - hoje.weekday()) % 7
                            if dias_ate_proximo == 0:
                                dias_ate_proximo = 7  # Se for hoje, pegar a próxima semana
                            data_encontrada = hoje + timedelta(days=dias_ate_proximo)
                            logger.info(f"[Horários] Dia da semana detectado: {dia_nome} -> {data_encontrada}")
                            break

            # Se não encontrou na mensagem, verificar no histórico
            if not data_encontrada and contexto_conversa:
                import pytz
                tz_brazil = pytz.timezone('America/Sao_Paulo')
                hoje = datetime.now(tz_brazil).date()

                logger.info(f"[Horários] Buscando data no histórico ({len(contexto_conversa)} mensagens)")
                for msg in reversed(contexto_conversa[-10:]):
                    texto = msg.get('texto', '').lower()
                    dados = msg.get('dados_coletados', {})

                    # Verificar data_preferida nos dados coletados
                    if dados.get('data_preferida'):
                        logger.info(f"[Horários] data_preferida encontrada: {dados['data_preferida']}")
                        match = re.search(padrao_data, dados['data_preferida'])
                        if match:
                            try:
                                data_encontrada = datetime.strptime(match.group(1), "%d/%m/%Y").date()
                                logger.info(f"[Horários] Data parseada do contexto: {data_encontrada}")
                                break
                            except ValueError:
                                pass

                    # Buscar "hoje", "amanhã" no texto das mensagens anteriores
                    if not data_encontrada:
                        if 'hoje' in texto:
                            data_encontrada = hoje
                            logger.info(f"[Horários] 'hoje' encontrado no histórico -> {data_encontrada}")
                            break
                        elif 'amanhã' in texto or 'amanha' in texto:
                            data_encontrada = hoje + timedelta(days=1)
                            logger.info(f"[Horários] 'amanhã' encontrado no histórico -> {data_encontrada}")
                            break

                    # Verificar medico_id nos dados coletados
                    if dados.get('medico_id'):
                        medico_id = dados['medico_id']
                        logger.info(f"[Horários] medico_id encontrado: {medico_id}")

            # Se ainda não tem medico_id, pegar o primeiro médico (ou único)
            if not medico_id:
                medicos = contexto_clinica.get('medicos', [])
                if len(medicos) == 1:
                    medico_id = medicos[0].get('id')
                elif medicos:
                    # Pegar o primeiro médico como fallback
                    medico_id = medicos[0].get('id')

            # Se encontrou data e médico, buscar horários disponíveis
            logger.info(f"[Horários] Resultado: data={data_encontrada}, medico_id={medico_id}")
            if data_encontrada and medico_id:
                logger.info(f"[Horários] Buscando horários para data={data_encontrada}, medico={medico_id}")
                agendamento_service = AgendamentoService(self.db)
                horarios_livres = agendamento_service.obter_horarios_disponiveis(
                    medico_id=medico_id,
                    data_consulta=data_encontrada,
                    duracao_minutos=30
                )
                logger.info(f"[Horários] Horários livres encontrados: {horarios_livres}")

                if horarios_livres:
                    data_formatada = data_encontrada.strftime("%d/%m/%Y")
                    # Selecionar 2 horários estratégicos da lista disponível
                    horarios_manha = [h for h in horarios_livres if int(h.split(':')[0]) < 12]
                    horarios_tarde = [h for h in horarios_livres if int(h.split(':')[0]) >= 12]

                    sugestao = []
                    if horarios_manha:
                        sugestao.append(horarios_manha[len(horarios_manha)//2])  # Meio da manhã
                    if horarios_tarde:
                        sugestao.append(horarios_tarde[len(horarios_tarde)//2])  # Meio da tarde

                    # Se só tem manhã ou só tarde, pegar 2 horários diferentes
                    if len(sugestao) == 1:
                        if horarios_manha and len(horarios_manha) > 1:
                            idx = len(horarios_manha)//2
                            outro_idx = 0 if idx > 0 else min(1, len(horarios_manha)-1)
                            if horarios_manha[outro_idx] != sugestao[0]:
                                sugestao.append(horarios_manha[outro_idx])
                        elif horarios_tarde and len(horarios_tarde) > 1:
                            idx = len(horarios_tarde)//2
                            outro_idx = 0 if idx > 0 else min(1, len(horarios_tarde)-1)
                            if horarios_tarde[outro_idx] != sugestao[0]:
                                sugestao.append(horarios_tarde[outro_idx])

                    if not sugestao:
                        sugestao = horarios_livres[:2]

                    # Montar texto da sugestão
                    if len(sugestao) >= 2:
                        sugestao_texto = f'Ofereça "{sugestao[0]}" e "{sugestao[1]}"'
                    else:
                        sugestao_texto = f'Ofereça "{sugestao[0]}"'

                    return f"""
🚨🚨🚨 ATENÇÃO MÁXIMA - REGRA CRÍTICA DE HORÁRIOS 🚨🚨🚨
Para a data {data_formatada}, os ÚNICOS horários disponíveis são:
✅ HORÁRIOS LIVRES: {', '.join(horarios_livres)}

❌ HORÁRIOS INDISPONÍVEIS: Todos os outros que NÃO estão na lista acima

📋 SUGESTÃO INICIAL: {sugestao_texto}

⛔ REGRA ABSOLUTA - LEIA COM ATENÇÃO:
1. Se o paciente pedir um horário que ESTÁ na lista acima → CONFIRME que está disponível!
2. Se o paciente pedir um horário que NÃO está na lista → diga que não está disponível
3. ANTES de responder, VERIFIQUE se o horário pedido está na lista!

📌 EXEMPLOS para esta data ({data_formatada}):
- Se paciente pedir "13:00" e 13:00 ESTÁ na lista → Diga "Sim, 13:00 está disponível!"
- Se paciente pedir "12:00" e 12:00 NÃO está na lista → Diga "Esse horário não está disponível"
- NUNCA diga que um horário está ocupado se ele APARECE na lista de livres!
🚨🚨🚨 FIM DA REGRA CRÍTICA 🚨🚨🚨
"""
                else:
                    data_formatada = data_encontrada.strftime("%d/%m/%Y")
                    dias_semana_nomes = {
                        0: 'segunda-feira', 1: 'terça-feira', 2: 'quarta-feira',
                        3: 'quinta-feira', 4: 'sexta-feira', 5: 'sábado', 6: 'domingo'
                    }
                    dia_semana_pedido = dias_semana_nomes.get(data_encontrada.weekday(), '')

                    # Verificar se o médico atende neste dia da semana
                    medico_nao_atende_dia = False
                    medico_info = None
                    for m in contexto_clinica.get('medicos', []):
                        if str(m.get('id')) == str(medico_id):
                            medico_info = m
                            break
                    if medico_info:
                        disponibilidade = medico_info.get('disponibilidade', {})
                        dias_atendimento = disponibilidade.get('dias_atendimento', [])
                        if dias_atendimento:
                            # Normalizar para comparação (lowercase, sem acento)
                            dias_norm = [d.lower().replace('ç','c').replace('á','a').replace('é','e').replace('í','i') for d in dias_atendimento]
                            dia_pedido_norm = dia_semana_pedido.lower().replace('ç','c').replace('á','a').replace('é','e').replace('í','i')
                            if dia_pedido_norm not in dias_norm:
                                medico_nao_atende_dia = True

                    if medico_nao_atende_dia:
                        dias_str = ', '.join(dias_atendimento) if dias_atendimento else 'dias não configurados'
                        nome_medico = medico_info.get('nome', 'o médico') if medico_info else 'o médico'
                        return f"""
🚨🚨🚨 ATENÇÃO - DIA SEM ATENDIMENTO 🚨🚨🚨
A data {data_formatada} cai em {dia_semana_pedido}.
O(A) {nome_medico} NÃO atende neste dia da semana!

⛔ NÃO diga que a agenda está lotada — o médico simplesmente NÃO trabalha nesse dia!
⛔ Diga ao paciente: "O dia {data_formatada} é {dia_semana_pedido} e o(a) {nome_medico} não atende nesse dia."
⛔ Informe os dias de atendimento: {dias_str}
⛔ Sugira as datas mais próximas nos dias em que o médico atende
🚨🚨🚨 FIM DA REGRA CRÍTICA 🚨🚨🚨
"""
                    else:
                        return f"""
🚨🚨🚨 ATENÇÃO MÁXIMA - DIA LOTADO 🚨🚨🚨
Para a data {data_formatada} ({dia_semana_pedido}): TODOS os horários estão OCUPADOS!

⛔ NÃO há nenhum horário disponível neste dia!
⛔ Informe ao paciente que a agenda está LOTADA para esta data
⛔ Sugira que escolha outro dia
🚨🚨🚨 FIM DA REGRA CRÍTICA 🚨🚨🚨
"""

        except Exception as e:
            print(f"Erro ao extrair horários disponíveis: {e}")

        return ""

    def _construir_prompt(self, mensagem: str, contexto_clinica: Dict, paciente: Optional, contexto_conversa: List[Dict]) -> str:
        """Constrói prompt para a IA."""

        # Buscar horários disponíveis se houver data mencionada
        info_horarios_disponiveis = self._extrair_data_e_horarios_disponiveis(mensagem, contexto_conversa, contexto_clinica)

        # Calcular data e dia da semana de hoje + próximos 7 dias
        # IMPORTANTE: Usar timezone do Brasil para "hoje" correto
        import pytz
        tz_brazil = pytz.timezone('America/Sao_Paulo')
        hoje = datetime.now(tz_brazil).date()
        dias_semana = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
        dia_semana_hoje = dias_semana[hoje.weekday()]

        data_hoje = hoje.strftime("%d/%m/%Y")
        nome_clinica = contexto_clinica.get('nome_clinica', 'clínica')

        # Criar calendário dos próximos 90 dias
        calendario = ""
        for i in range(90):
            data_futuro = hoje + timedelta(days=i)
            dia_semana = dias_semana[data_futuro.weekday()]
            data_formatada = data_futuro.strftime("%d/%m/%Y")
            if i == 0:
                calendario += f"- HOJE ({dia_semana}): {data_formatada}\n"
            else:
                calendario += f"- {dia_semana}: {data_formatada}\n"

        # Colocar horários disponíveis no INÍCIO do prompt para máxima visibilidade
        prompt = ""
        if info_horarios_disponiveis:
            prompt += info_horarios_disponiveis
            prompt += "\n"

        prompt += f"""Você é Fernanda, a assistente virtual da {nome_clinica}.

📅 HOJE É: {dia_semana_hoje}, {data_hoje}

CALENDÁRIO DOS PRÓXIMOS 90 DIAS:
{calendario}

IMPORTANTE: Quando o usuário mencionar "próxima segunda", "quinta que vem", etc., use o calendário acima para encontrar a DATA CORRETA.
ATENÇÃO: Você pode agendar consultas para qualquer data dentro dos próximos 90 dias, desde que o horário esteja disponível na agenda do médico.

INFORMAÇÕES DA CLÍNICA:
"""
        endereco_clinica = contexto_clinica.get('endereco_clinica')
        if endereco_clinica:
            prompt += f"Endereço: {endereco_clinica}\n"

        # Calcular especialidades únicas
        medicos = contexto_clinica.get('medicos', [])
        especialidades_unicas = list(set(m['especialidade'] for m in medicos))
        quantidade_especialidades = len(especialidades_unicas)
        quantidade_medicos = len(medicos)

        prompt += f"📋 RESUMO: {quantidade_especialidades} especialidade(s), {quantidade_medicos} profissional(is)\n"
        prompt += f"Especialidades: {', '.join(especialidades_unicas)}\n\n"
        prompt += "Médicos disponíveis:\n"

        for medico in medicos:
            prompt += f"- [ID: {medico['id']}] {medico['nome']} ({medico['especialidade']}) - CRM: {medico['crm']}\n"
            prompt += f"  Convênios: {', '.join(medico['convenios'])}\n"
            valor_particular = medico.get('valor_particular', 150.00)
            prompt += f"  💰 Valor particular: R$ {valor_particular:.2f}\n"

            # Adicionar informações de disponibilidade do médico
            disponibilidade = medico.get('disponibilidade', {})
            dias_atendimento = disponibilidade.get('dias_atendimento', [])
            horarios_por_dia = disponibilidade.get('horarios_por_dia', {})

            if dias_atendimento:
                prompt += f"  📅 Dias de atendimento: {', '.join(dias_atendimento)}\n"
                prompt += f"  ⏰ Horários:\n"
                for dia, horario in horarios_por_dia.items():
                    prompt += f"     - {dia}: {horario}\n"
            else:
                prompt += f"  📅 Dias de atendimento: Não configurado (verificar com a clínica)\n"

        # Adicionar informação sobre médico único ou múltiplos
        medico_unico = contexto_clinica.get('medico_unico', False)

        if medico_unico and quantidade_medicos == 1:
            medico = medicos[0] if medicos else {}
            prompt += f"""
🏥 CLÍNICA COM MÉDICO ÚNICO:
Esta clínica possui apenas 1 médico: {medico.get('nome', '')} ({medico.get('especialidade', '')})
➡️ NÃO pergunte qual especialidade ou médico - use automaticamente o ID {medico.get('id', '')}
➡️ Já defina medico_id = {medico.get('id', '')} nos dados_coletados desde o início
➡️ Vá direto para perguntar: nome do paciente, data, horário e forma de pagamento
"""
        else:
            prompt += f"""
🏥 CLÍNICA COM MÚLTIPLOS PROFISSIONAIS:
- Total de especialidades: {quantidade_especialidades}
- Total de profissionais: {quantidade_medicos}
⚠️ ATENÇÃO: Diga "{quantidade_especialidades} especialidades" (não {quantidade_medicos}). Exemplo correto:
   "Temos {quantidade_especialidades} especialidades: {', '.join(especialidades_unicas)}"
➡️ Pergunte para qual especialidade o paciente deseja agendar
➡️ Se houver mais de um médico na mesma especialidade, pergunte qual médico prefere
➡️ Só defina medico_id após o paciente escolher
"""

        prompt += f"\nConvênios aceitos: {', '.join(contexto_clinica.get('convenios', []))}\n"

        # Horários disponíveis já foram adicionados no INÍCIO do prompt

        if paciente:
            prompt += f"\nPACIENTE IDENTIFICADO: {paciente.nome}\n"
            prompt += f"⚠️ Convênio no cadastro anterior: {paciente.convenio or 'Não informado'}\n"
            prompt += f"⚠️ IMPORTANTE: PERGUNTE NOVAMENTE sobre convênio - paciente pode ter mudado de plano!\n"
            # Verificar se tem agendamentos anteriores
            from app.models import Agendamento
            qtd_agendamentos = self.db.query(Agendamento).filter(
                Agendamento.paciente_id == paciente.id
            ).count()
            if qtd_agendamentos > 0:
                prompt += f"📋 Este paciente já tem {qtd_agendamentos} consulta(s) registrada(s) no sistema.\n"
                prompt += f"   → Provavelmente é um RETORNO. Pergunte: 'Qual o motivo desta consulta? Rotina, levar exames ou algum sintoma?'\n"
            else:
                prompt += f"📋 Este paciente NÃO tem consultas anteriores registradas no sistema.\n"
                prompt += f"   → Pode ser PRIMEIRA CONSULTA ou paciente antigo (antes do sistema).\n"
                prompt += f"   → Pergunte: 'É sua primeira consulta com o Dr. [nome]? Qual o motivo da visita?'\n"
        else:
            prompt += "\n📋 PACIENTE NOVO (não encontrado no sistema)\n"
            prompt += "   → Pergunte nome completo e se é primeira consulta com o médico\n"
        
        # Extrair dados já coletados do contexto
        dados_ja_coletados = {
            "nome": None,
            "especialidade": None,
            "medico": None,
            "convenio": None,
            "motivo_consulta": None,
            "data": None,
            "horario": None
        }

        if contexto_conversa:
            prompt += "\n" + "="*50 + "\n"
            prompt += "⚠️ HISTÓRICO DA CONVERSA (LEIA COM ATENÇÃO!):\n"
            prompt += "="*50 + "\n"

            for msg in contexto_conversa[-10:]:
                tipo = msg.get('tipo', 'user')
                texto = msg.get('texto', '')
                intencao = msg.get('intencao', '')
                dados = msg.get('dados_coletados', {})

                prompt += f"[{tipo.upper()}]: {texto}\n"

                # Acumular dados coletados
                if dados:
                    for k, v in dados.items():
                        if v and k in dados_ja_coletados:
                            dados_ja_coletados[k] = v

            prompt += "="*50 + "\n"

            # Mostrar resumo do que já foi coletado
            coletados = [f"{k}={v}" for k, v in dados_ja_coletados.items() if v]
            if coletados:
                prompt += f"\n📋 DADOS JÁ COLETADOS NESTA CONVERSA: {', '.join(coletados)}\n"
                prompt += "⚠️ NÃO PERGUNTE NOVAMENTE SOBRE ESSES DADOS!\n"
        
        prompt += f"""
MENSAGEM DO USUÁRIO: "{mensagem}"

INSTRUÇÕES IMPORTANTES:
1. Você se chama Fernanda - apresente-se APENAS UMA VEZ na conversa (na primeira resposta)
   Na apresentação, informe que o paciente pode conversar por áudio ou texto, como preferir.
2. Seja empática, profissional e prestativa
3. Use emojis moderadamente para tornar a conversa mais amigável

💙 REGRAS DE EMPATIA (MUITO IMPORTANTE!):
- DETECTE palavras que indicam DOR ou DESCONFORTO: dor, doendo, machucado, mal, ruim, piorando, inchado, febre, vômito, náusea, tontura, etc.
- DETECTE palavras que indicam URGÊNCIA: urgente, urgência, emergência, grave, sério, preocupado, assustado, medo, não aguento, etc.
- Quando detectar DOR ou URGÊNCIA:
  ✓ NÃO use emojis sorridentes (😊 🙂 😃 😄)
  ✓ USE emojis de empatia e cuidado: 💙 🤗 😔
  ✓ Demonstre COMPREENSÃO genuína: "Entendo que deve ser desconfortável...", "Sinto muito que esteja passando por isso..."
  ✓ Priorize AGILIDADE: "Vou verificar o mais rápido possível...", "Deixa eu encontrar o primeiro horário disponível..."
- Em situações NORMAIS (rotina, retorno, exames): pode usar 😊 normalmente
- EXEMPLOS de tom empático:
  ✗ ERRADO: "Entendo sua situação! 😊 Vou verificar..."
  ✓ CERTO: "Entendo sua situação, deve ser bem desconfortável 😔 Vou verificar imediatamente..."
  ✗ ERRADO: "Que bom que você quer agendar! 😊" (quando paciente relata dor)
  ✓ CERTO: "Sinto muito que esteja com dor 💙 Vamos encontrar um horário o mais rápido possível..."

⚠️ REGRAS CRÍTICAS DE CONTEXTO (OBRIGATÓRIO SEGUIR):
4. LEIA O HISTÓRICO COMPLETO DA CONVERSA ANTES DE RESPONDER
5. NUNCA REPITA PERGUNTAS sobre informações já fornecidas
6. Se o usuário já disse o NOME dele, NÃO pergunte de novo - USE o nome que ele informou
7. Se o usuário já disse a ESPECIALIDADE/MÉDICO, NÃO pergunte de novo - PROSSIGA para próxima etapa
8. Se uma informação já está no histórico, AVANCE para a próxima pergunta do fluxo
9. NÃO se apresente novamente se já fez isso no histórico
10. Analise o texto literal do histórico - os dados estão nas mensagens do usuário

REGRA CRÍTICA SOBRE NOMES:
11. NUNCA chame o cliente por NENHUM nome até ele se apresentar
12. ATÉ o cliente informar o nome dele, use apenas "você" ou trate sem nome
13. EXEMPLOS CORRETOS ANTES DA APRESENTAÇÃO:
   ✓ "Olá! Sou a Fernanda, assistente virtual da clínica. Você pode falar comigo por áudio ou texto, como preferir 😊 Como posso ajudá-lo?"
   ✓ "Para começar, qual é seu nome completo?"
   ✓ "Perfeito! Qual especialidade você precisa?"
14. EXEMPLOS ERRADOS (NUNCA FAÇA):
   ✗ "Olá Maria, como posso ajudar?" (cliente não se apresentou!)
   ✗ "Boa tarde João!" (cliente não disse o nome!)
15. SOMENTE APÓS o cliente informar o nome (ex: "Meu nome é João"), você pode usar:
   ✓ "Prazer em atendê-lo, João!"
   ✓ "Certo João, qual especialidade você precisa?"

📱 REGRA IMPORTANTE SOBRE TELEFONE:
- NUNCA pergunte o telefone do paciente - você JÁ ESTÁ conversando com ele pelo WhatsApp!
- O número de telefone já é conhecido automaticamente pela conversa
- Não inclua "telefone" no fluxo de coleta de dados

🔢 FLUXO DE AGENDAMENTO (SIGA ESTA ORDEM EXATA!):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Passo 1: NOME - Pergunte o nome completo do paciente
Passo 2: MÉDICO - Pergunte qual médico/especialidade (PULE se médico único)
Passo 3: MOTIVO - Pergunte o motivo da consulta (veja regras abaixo)
Passo 4: DATA - Pergunte qual data prefere
Passo 5: HORÁRIO - Ofereça 2 horários disponíveis para escolha
Passo 6: CONVÊNIO - Pergunte "Você tem convênio ou prefere consulta particular?"
Passo 7: CONFIRMAR - Somente após ter TODOS os 6 dados acima
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 REGRAS SOBRE MOTIVO DA CONSULTA:
- Se o paciente é NOVO (sem cadastro anterior), pergunte de forma acolhedora:
  "É sua primeira consulta com o Dr. [nome]? Qual o motivo da visita?"
- Se o paciente JÁ TEM cadastro, pergunte diretamente o motivo
- Ofereça opções simples para facilitar:
  • 🔄 Rotina/Retorno
  • 📋 Levar resultados de exames
  • 🩺 Algum sintoma específico
- Se for sintoma, pergunte brevemente qual (ex: "dor de cabeça", "febre", etc.)
- Salve de forma SINTÉTICA no campo motivo_consulta:
  ✓ "Rotina" / "Retorno"
  ✓ "Resultado de exames"
  ✓ "Sintoma: dor abdominal" / "Sintoma: febre há 3 dias"
  ✓ "Primeira consulta - avaliação geral"

🚨 CHECKLIST OBRIGATÓRIO ANTES DE CONFIRMAR:
Antes de definir proxima_acao="agendar", VERIFIQUE se você tem:
[ ] Nome do paciente? Se NÃO → pergunte o nome
[ ] Médico definido? Se NÃO → pergunte (a menos que seja único)
[ ] Motivo da consulta? Se NÃO → pergunte com as opções
[ ] Data definida? Se NÃO → pergunte a data
[ ] Horário escolhido? Se NÃO → ofereça opções
[ ] Convênio/Particular? Se NÃO → PERGUNTE "Você tem convênio ou particular?"

⛔ Se QUALQUER item acima estiver faltando, NÃO CONFIRME o agendamento!
⛔ NUNCA assuma "particular" - sempre pergunte explicitamente!

REGRAS DO FLUXO:
22. Se o usuário forneceu múltiplas informações de uma vez, AVANCE para a próxima pendente
23. NUNCA processe agendamento sem o HORÁRIO explícito do usuário
24. NUNCA processe agendamento sem perguntar CONVÊNIO ou PARTICULAR
25. Quando tiver TODOS os 6 dados (nome, médico, motivo, data, horário, convênio), defina proxima_acao como "agendar"
26. Sua função é APENAS coletar dados - o sistema salvará automaticamente
27. NUNCA mencione erros técnicos ou confirmações de salvamento
28. SEMPRE use o CALENDÁRIO fornecido acima para converter dias da semana em datas
29. CONSULTE OS HORÁRIOS REAIS DE CADA MÉDICO listados acima em "Dias de atendimento" e "Horários"
30. NUNCA ofereça horários fora do expediente configurado do médico
31. Se o paciente pedir um dia em que o médico NÃO atende, informe educadamente os dias disponíveis
32. Os agendamentos são de hora em hora (ex: 08:00, 09:00, 10:00) respeitando o horário de cada médico

✅ REGRAS DE CONFIRMAÇÃO DO AGENDAMENTO:
- Quando tiver TODOS os dados, CONFIRME IMEDIATAMENTE o agendamento de forma clara e completa
- Mostre TODOS os dados coletados de forma organizada (nome, médico, data, horário, motivo, convênio)
- Diga "✅ Agendamento confirmado!" ou "✅ Sua consulta está agendada!"
- NÃO espere o paciente perguntar se está confirmado - confirme proativamente
- NUNCA mencione SMS - toda comunicação é via WhatsApp
- SEMPRE inclua o ENDEREÇO da clínica na confirmação (consulte "Endereço:" nas INFORMAÇÕES DA CLÍNICA acima)
- SEMPRE inclua as orientações abaixo ao final da confirmação:
  📍 Nosso endereço: [endereço da clínica]
  🪪 Traga documento com foto (obrigatório para convênio)
  📎 Se tiver exames recentes, traga no dia da consulta!

🔔 REGRA SOBRE LEMBRETES:
- SOMENTE mencione lembretes ao CRIAR UM NOVO agendamento, NUNCA ao confirmar presença!
- Se o paciente está CONFIRMANDO PRESENÇA (respondendo "confirmar", "confirmo", "vou sim", etc.): NÃO mencione lembretes de 24h pois ele JÁ recebeu esse lembrete. Se faltar mais de 2h para a consulta, diga apenas "Você receberá um lembrete 2h antes". Se faltar menos de 2h, NÃO mencione lembretes.
- Se está CRIANDO NOVO agendamento e a consulta é para MAIS de 24h: "Você receberá um lembrete 24h antes e outro 2h antes da consulta"
- Se está CRIANDO NOVO agendamento e a consulta é para HOJE ou menos de 24h: "Como sua consulta é em breve, você receberá um lembrete 2h antes"
- ADAPTE a mensagem de lembrete baseado no contexto da conversa!

💰 INFORMAÇÕES SOBRE CONVÊNIOS E VALORES:
- CONSULTE OS CONVÊNIOS DE CADA MÉDICO listados acima em "Convênios:" após o nome do médico
- NÃO USE convênios genéricos - cada médico tem seus próprios convênios aceitos
- O VALOR da consulta particular está indicado em cada médico como "Valor particular: R$ X"
- SEMPRE pergunte: "Você tem convênio ou prefere consulta particular?"
- Se tiver convênio, liste APENAS os convênios que o médico escolhido aceita
- SOMENTE informe o valor da consulta particular APÓS o paciente escolher PARTICULAR
- USE O VALOR CORRETO DO MÉDICO (não invente valores!)
- NÃO mencione o valor da consulta particular antes do paciente escolher essa modalidade

🚨🚨🚨 REGRA CRÍTICA - FORMA DE PAGAMENTO 🚨🚨🚨
⛔ SEMPRE pergunte: "Você tem convênio ou prefere consulta particular?"
⛔ NUNCA assuma baseado em cadastro anterior - paciente pode ter mudado de convênio!
⛔ NUNCA pule esta pergunta - ela é OBRIGATÓRIA EM TODO AGENDAMENTO!
⛔ Mesmo que o paciente seja conhecido, PERGUNTE - ele pode ter perdido o plano!
⛔ Se o paciente informou data e horário mas NÃO informou convênio NESTA CONVERSA → PERGUNTE!
✅ Pergunte DEPOIS do horário e ANTES de confirmar
✅ Exemplo: "Ótimo! Última pergunta: você tem convênio ou prefere consulta particular?"
🚨🚨🚨 FIM DA REGRA CRÍTICA 🚨🚨🚨

REGRA ESTRATÉGICA SOBRE OFERECIMENTO DE HORÁRIOS:
⚠️ PRIORIDADE MÁXIMA: Se houver uma seção "HORÁRIOS DISPONÍVEIS" ou "HORÁRIOS LIVRES" acima, USE APENAS OS HORÁRIOS DESSA LISTA!
30. Quando o usuário escolher uma DATA, ofereça os 2 horários SUGERIDOS na seção de horários disponíveis
31. NUNCA ofereça horários que NÃO estão na lista de HORÁRIOS LIVRES - esses horários estão OCUPADOS
32. Se o paciente pedir um horário OCUPADO, diga: "Infelizmente esse horário já está reservado. Temos disponível às [horário da lista]"
33. NUNCA liste TODOS os horários - ofereça apenas 2 opções da lista disponível
34. NUNCA confirme agendamento sem o paciente ESCOLHER um horário específico

🚨🚨🚨 REGRA CRÍTICA - NUNCA INVENTE DISPONIBILIDADE 🚨🚨🚨
⛔ VOCÊ DEVE VERIFICAR A LISTA "HORÁRIOS LIVRES" ANTES DE RESPONDER SOBRE DISPONIBILIDADE
⛔ Se o horário pedido pelo paciente ESTÁ na lista de HORÁRIOS LIVRES → ESTÁ DISPONÍVEL, OFEREÇA!
⛔ SOMENTE diga "ocupado/reservado" se o horário NÃO ESTÁ na lista de HORÁRIOS LIVRES
⛔ EXEMPLO: Se a lista diz "✅ HORÁRIOS LIVRES: 08:00, 09:00, 13:00, 14:00" e o paciente pedir 13:00:
   → 13:00 ESTÁ na lista → RESPONDA: "Sim, 13:00 está disponível! Posso agendar?"
   → NÃO diga que 13:00 está ocupado - isso seria MENTIRA!
⛔ NUNCA MINTA para o paciente dizendo que um horário está ocupado quando ele está livre!
✅ CONSULTE a lista de HORÁRIOS LIVRES no INÍCIO deste prompt antes de responder!
🚨🚨🚨 FIM DA REGRA CRÍTICA 🚨🚨🚨

🎯 ESTRATÉGIA QUANDO PACIENTE PEDE HORÁRIO OCUPADO:
35. Se o paciente pedir um horário que NÃO está na lista de HORÁRIOS LIVRES:
36. PRIMEIRO: Informe que o horário está OCUPADO
37. SEGUNDO: Ofereça alternativas DA LISTA de horários disponíveis:
    ✓ "Esse horário já está reservado 😔 Mas temos disponível às [horário da lista]. O que acha?"
    ✓ "Infelizmente às [horário pedido] já temos paciente. Posso te encaixar às [horário da lista]?"
38. NUNCA use a técnica do "encaixe/desistência" para horários ocupados - seja direto que está ocupado
39. Após o paciente escolher um horário DA LISTA, continue coletando os dados pendentes

⏳ MARCADOR DE PAUSA PARA SIMULAÇÃO DE ESPERA:
40. Quando usar a técnica do encaixe/desistência, SEMPRE use o marcador ⏳ para separar as duas partes:
41. FORMATO OBRIGATÓRIO: "Primeira mensagem...⏳Segunda mensagem..."
42. EXEMPLO CORRETO: "Um momentinho, vou verificar na agenda...⏳Você está com sorte! Tivemos uma desistência às 11h. Posso te encaixar?"
43. O marcador ⏳ faz o sistema exibir a primeira parte, aguardar 2-3 segundos, e depois mostrar a segunda parte
44. Isso cria a impressão realista de que você está consultando o sistema

🚨 SISTEMA DE DETECÇÃO DE URGÊNCIA MÉDICA:
VOCÊ DEVE CLASSIFICAR CADA MENSAGEM QUANTO À URGÊNCIA. ISSO É CRÍTICO PARA A SEGURANÇA DO PACIENTE.

NÍVEIS DE URGÊNCIA:
- "critica": Emergência médica com risco imediato à saúde/vida. Exemplos:
  * Sintomas de infarto (dor no peito, braço esquerdo, falta de ar intensa)
  * Sintomas de AVC (paralisia, fala enrolada, confusão súbita)
  * Dificuldade respiratória grave, engasgo
  * Sangramento intenso que não para
  * Reação alérgica grave (anafilaxia)
  * Ideação suicida ou autolesão ("quero morrer", "não aguento mais viver")
  * Dor insuportável, perda de consciência
  * Pedidos de socorro/ajuda urgente ("me ajuda, estou passando mal")
  * Convulsões em andamento

- "atencao": Situações preocupantes que merecem atenção, mas sem risco imediato:
  * Piora significativa de sintomas ("está muito pior que ontem")
  * Efeitos colaterais de medicamentos
  * Febre alta persistente (acima de 39°C)
  * Sintomas novos preocupantes
  * Paciente muito ansioso ou assustado com seu quadro
  * Dor que não passa com medicação comum

- "normal": Conversas rotineiras de agendamento, dúvidas gerais, remarcações

⚠️ REGRAS CRÍTICAS DE CONTEXTO PARA URGÊNCIA:
45. ANALISE O CONTEXTO, não apenas palavras isoladas:
   - "Meu pai teve infarto ano passado" → NORMAL (referência histórica)
   - "Acho que estou tendo um infarto agora" → CRÍTICA (situação atual)
   - "Não é urgente, só quero remarcar" → NORMAL (negação presente)
   - "É urgente, preciso falar com o doutor" → CRÍTICA

46. Se detectar URGÊNCIA CRÍTICA, sua resposta DEVE:
   - Reconhecer a gravidade da situação
   - Informar que o médico está sendo notificado IMEDIATAMENTE
   - Incluir os números de emergência (SAMU 192, Bombeiros 193)
   - Orientar a ir ao pronto-socorro mais próximo se necessário
   - NÃO continuar o fluxo normal de agendamento

47. Se detectar URGÊNCIA ATENÇÃO, continue o atendimento normalmente, mas registre no JSON

48. Em caso de dúvida sobre o nível, prefira classificar como mais urgente (melhor alarme falso que perder emergência)

RESPONDA EM FORMATO JSON:
{{
    "resposta": "sua resposta para o usuário",
    "intencao": "saudacao|agendamento|informacao|despedida|urgencia|outros",
    "urgencia": {{
        "nivel": "normal|atencao|critica",
        "motivo": null  # Se nivel != normal, descreva brevemente o motivo (ex: "Paciente relata dor no peito intensa")
    }},
    "dados_coletados": {{
        "nome": null,
        "especialidade": null,
        "medico_id": null,  # IMPORTANTE: Use o [ID: X] que aparece antes do nome do médico na lista acima. Ex: se for "[ID: 31] Dr. João", use 31
        "convenio": null,
        "motivo_consulta": null,  # Ex: "Rotina", "Resultado de exames", "Sintoma: dor de cabeça", "Primeira consulta"
        "data_preferida": null  # Formato: "DD/MM/YYYY HH:MM" ou "DD/MM/YYYY"
    }},
    "proxima_acao": "solicitar_dados|verificar_agenda|agendar|informar|finalizar|notificar_urgencia"
}}

IMPORTANTE SOBRE medico_id:
- Se o usuário escolheu um médico da lista, use o ID numérico (1, 2, 3, etc)
- NÃO coloque CRM, nome ou especialidade no campo medico_id
- Use o campo "especialidade" para a especialidade/motivo da consulta
"""
        return prompt
    
    def _processar_resposta_ia(self, resposta_ia: str) -> Dict[str, Any]:
        """Processa a resposta da IA e executa ações necessárias."""

        try:
            # Extrair JSON da resposta
            json_match = re.search(r'\{.*\}', resposta_ia, re.DOTALL)
            if json_match:
                dados = json.loads(json_match.group())
            else:
                raise ValueError("JSON não encontrado na resposta")

        except (json.JSONDecodeError, ValueError):
            return self._resposta_padrao("Como posso ajudá-lo hoje?")

        resposta = dados.get("resposta", "Como posso ajudá-lo?")
        intencao = dados.get("intencao", "outros")
        proxima_acao = dados.get("proxima_acao", "informar")
        dados_coletados = dados.get("dados_coletados", {})

        # Extrair informações de urgência
        urgencia_data = dados.get("urgencia", {})
        urgencia_nivel = urgencia_data.get("nivel", "normal") if isinstance(urgencia_data, dict) else "normal"
        urgencia_motivo = urgencia_data.get("motivo") if isinstance(urgencia_data, dict) else None

        # Validar nível de urgência
        if urgencia_nivel not in ["normal", "atencao", "critica"]:
            urgencia_nivel = "normal"

        return {
            "resposta": resposta,
            "intencao": intencao,
            "proxima_acao": proxima_acao,
            "dados_coletados": dados_coletados,
            "urgencia": {
                "nivel": urgencia_nivel,
                "motivo": urgencia_motivo
            },
            "paciente_existente": False
        }
    
    def _processar_com_regras(self, mensagem: str, contexto_clinica: Dict, paciente: Optional) -> Dict[str, Any]:
        """Fallback: processa com regras simples se IA não estiver disponível."""
        mensagem_lower = mensagem.lower().strip()
        
        if any(saudacao in mensagem_lower for saudacao in ["oi", "olá", "bom dia", "boa tarde"]):
            return self._processar_saudacao(contexto_clinica)
        elif any(palavra in mensagem_lower for palavra in ["marcar", "agendar", "consulta"]):
            return self._processar_agendamento(contexto_clinica)
        elif "cardio" in mensagem_lower:
            return self._processar_especialidade("cardiologista", contexto_clinica)
        elif "alergi" in mensagem_lower:
            return self._processar_especialidade("alergista", contexto_clinica)
        elif any(desp in mensagem_lower for desp in ["tchau", "obrigado", "valeu"]):
            return self._processar_despedida()
        else:
            return self._resposta_padrao(f"Como posso ajudá-lo na {contexto_clinica.get('nome_clinica', 'clínica')}?")
    
    def _obter_contexto_clinica(self) -> Dict[str, Any]:
        """Obtém informações da clínica para contexto."""
        cliente = self.db.query(Cliente).filter(Cliente.id == self.cliente_id).first()

        if not cliente:
            return {}

        medicos = self.db.query(Medico).filter(
            Medico.cliente_id == self.cliente_id,
            Medico.ativo == True
        ).all()

        convenios = self.db.query(Convenio).filter(
            Convenio.cliente_id == self.cliente_id,
            Convenio.ativo == True
        ).all()

        # Buscar configurações de horário de cada médico
        medicos_com_config = []
        dias_semana_nomes = {
            0: 'Domingo', 1: 'Segunda', 2: 'Terça',
            3: 'Quarta', 4: 'Quinta', 5: 'Sexta', 6: 'Sábado'
        }

        for m in medicos:
            # Pular secretárias - não são médicos para agendamento
            if hasattr(m, 'is_secretaria') and m.is_secretaria:
                continue

            # Buscar configuração do médico
            config_result = self.db.execute(text("""
                SELECT horarios_por_dia, dias_atendimento, horario_inicio, horario_fim,
                       intervalo_almoco_inicio, intervalo_almoco_fim
                FROM configuracoes_medico
                WHERE medico_id = :medico_id
            """), {"medico_id": m.id}).fetchone()

            # Montar informações de disponibilidade
            disponibilidade = {
                "dias_atendimento": [],
                "horarios_por_dia": {}
            }

            if config_result:
                horarios_por_dia = config_result[0]
                dias_atendimento = config_result[1]
                horario_inicio_padrao = config_result[2] or "08:00"
                horario_fim_padrao = config_result[3] or "18:00"
                almoco_inicio = config_result[4]
                almoco_fim = config_result[5]

                # Processar horarios_por_dia (JSON detalhado)
                if horarios_por_dia:
                    if isinstance(horarios_por_dia, str):
                        horarios_por_dia = json.loads(horarios_por_dia)

                    for dia_num_str, config_dia in horarios_por_dia.items():
                        dia_num = int(dia_num_str)
                        if config_dia.get('ativo', False):
                            dia_nome = dias_semana_nomes.get(dia_num, f'Dia {dia_num}')
                            disponibilidade["dias_atendimento"].append(dia_nome)

                            inicio = config_dia.get('inicio', horario_inicio_padrao)
                            fim = config_dia.get('fim', horario_fim_padrao)
                            sem_almoco = config_dia.get('sem_almoco', False)
                            almoco_i = config_dia.get('almoco_inicio', almoco_inicio)
                            almoco_f = config_dia.get('almoco_fim', almoco_fim)

                            horario_info = f"{inicio} às {fim}"
                            if not sem_almoco and almoco_i and almoco_f:
                                horario_info += f" (almoço {almoco_i}-{almoco_f})"

                            disponibilidade["horarios_por_dia"][dia_nome] = horario_info

                # Fallback: usar dias_atendimento se horarios_por_dia não tiver dados
                elif dias_atendimento:
                    if isinstance(dias_atendimento, str):
                        dias_atendimento = json.loads(dias_atendimento)

                    for dia_num in dias_atendimento:
                        dia_nome = dias_semana_nomes.get(dia_num, f'Dia {dia_num}')
                        disponibilidade["dias_atendimento"].append(dia_nome)

                        horario_info = f"{horario_inicio_padrao} às {horario_fim_padrao}"
                        if almoco_inicio and almoco_fim:
                            horario_info += f" (almoço {almoco_inicio}-{almoco_fim})"

                        disponibilidade["horarios_por_dia"][dia_nome] = horario_info

            medicos_com_config.append({
                "id": m.id,
                "nome": m.nome,
                "especialidade": m.especialidade,
                "crm": m.crm,
                "convenios": [
                    c['nome'] if isinstance(c, dict) else c
                    for c in (m.convenios_aceitos or [])
                ],
                "disponibilidade": disponibilidade,
                "valor_particular": float(m.valor_consulta_particular) if m.valor_consulta_particular else 150.00
            })

        # Determinar se é clínica com médico único
        medico_unico = len(medicos_com_config) == 1

        return {
            "nome_clinica": cliente.nome,
            "endereco_clinica": cliente.endereco,
            "medicos": medicos_com_config,
            "convenios": [c.nome for c in convenios],
            "medico_unico": medico_unico,
            "quantidade_medicos": len(medicos_com_config)
        }
    
    def _obter_paciente_por_telefone(self, telefone: str) -> Optional:
        """Busca paciente pelo telefone."""
        telefone_limpo = re.sub(r'[^\d]', '', telefone)
        return self.db.query(Paciente).filter(
            Paciente.cliente_id == self.cliente_id,
            Paciente.telefone.like(f"%{telefone_limpo[-8:]}%")
        ).first()
    
    # Métodos de fallback (regras simples)
    def _processar_saudacao(self, contexto: Dict) -> Dict[str, Any]:
        nome_clinica = contexto.get("nome_clinica", "clínica")
        return {
            "resposta": f"👋 Olá! Sou a Fernanda, assistente virtual da {nome_clinica}. Você pode falar comigo por áudio ou texto, como preferir 😊 Como posso ajudá-lo hoje?",
            "intencao": "saudacao",
            "proxima_acao": "aguardar_solicitacao",
            "dados_coletados": {},
            "urgencia": {"nivel": "normal", "motivo": None},
            "paciente_existente": False
        }

    def _processar_agendamento(self, contexto: Dict) -> Dict[str, Any]:
        medicos = contexto.get("medicos", [])
        opcoes_medicos = ""
        for i, medico in enumerate(medicos, 1):
            opcoes_medicos += f"{i}️⃣ {medico['especialidade']} - {medico['nome']}\n"

        return {
            "resposta": f"Para qual especialidade você gostaria de agendar?\n\n{opcoes_medicos}",
            "intencao": "agendamento",
            "proxima_acao": "escolher_especialidade",
            "dados_coletados": {"solicitou_agendamento": True},
            "urgencia": {"nivel": "normal", "motivo": None},
            "paciente_existente": False
        }

    def _processar_especialidade(self, tipo: str, contexto: Dict) -> Dict[str, Any]:
        medicos = contexto.get("medicos", [])
        medico = next((m for m in medicos if tipo.lower() in m["especialidade"].lower()), None)

        if medico:
            convenios_str = ", ".join(medico["convenios"])
            resposta = f"**{medico['nome']}** - {medico['especialidade']}\n"
            resposta += f"CRM: {medico['crm']}\nConvênios: {convenios_str}\n"
            resposta += "Seu atendimento será pelo convênio ou particular?"

            return {
                "resposta": resposta,
                "intencao": "agendamento",
                "proxima_acao": "escolher_convenio",
                "dados_coletados": {"medico_id": medico["id"], "especialidade": medico["especialidade"]},
                "urgencia": {"nivel": "normal", "motivo": None},
                "paciente_existente": False
            }

        return self._resposta_padrao("Especialidade não encontrada.")

    def _processar_despedida(self) -> Dict[str, Any]:
        return {
            "resposta": "Foi um prazer ajudá-lo! Tenha um ótimo dia!",
            "intencao": "despedida",
            "proxima_acao": "finalizar",
            "dados_coletados": {},
            "urgencia": {"nivel": "normal", "motivo": None},
            "paciente_existente": False
        }

    def _resposta_padrao(self, mensagem: str) -> Dict[str, Any]:
        return {
            "resposta": mensagem,
            "intencao": "outros",
            "proxima_acao": "informar",
            "dados_coletados": {},
            "urgencia": {"nivel": "normal", "motivo": None},
            "paciente_existente": False
        }
