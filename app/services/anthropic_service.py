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

from app.models.cliente import Cliente
from app.models.medico import Medico
from app.models.paciente import Paciente
from app.models.convenio import Convenio

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
    
    def _construir_prompt(self, mensagem: str, contexto_clinica: Dict, paciente: Optional, contexto_conversa: List[Dict]) -> str:
        """Constrói prompt para a IA."""

        # Calcular data e dia da semana de hoje + próximos 7 dias
        hoje = date.today()
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

        prompt = f"""Você é Sônia, a assistente virtual da {nome_clinica}.

📅 HOJE É: {dia_semana_hoje}, {data_hoje}

CALENDÁRIO DOS PRÓXIMOS 90 DIAS:
{calendario}

IMPORTANTE: Quando o usuário mencionar "próxima segunda", "quinta que vem", etc., use o calendário acima para encontrar a DATA CORRETA.
ATENÇÃO: Você pode agendar consultas para qualquer data dentro dos próximos 90 dias, desde que o horário esteja disponível na agenda do médico.

INFORMAÇÕES DA CLÍNICA:
Médicos disponíveis:
"""
        
        for medico in contexto_clinica.get('medicos', []):
            prompt += f"- {medico['nome']} ({medico['especialidade']}) - CRM: {medico['crm']}\n"
            prompt += f"  Convênios: {', '.join(medico['convenios'])}\n"
        
        prompt += f"\nConvênios aceitos: {', '.join(contexto_clinica.get('convenios', []))}\n"
        
        if paciente:
            prompt += f"\nPACIENTE IDENTIFICADO: {paciente.nome} (Convênio: {paciente.convenio})\n"
        
        # Extrair dados já coletados do contexto
        dados_ja_coletados = {
            "nome": None,
            "especialidade": None,
            "medico": None,
            "convenio": None,
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
1. Você se chama Sônia - apresente-se APENAS UMA VEZ na conversa (na primeira resposta)
2. Seja empática, profissional e prestativa
3. Use emojis moderadamente para tornar a conversa mais amigável

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
   ✓ "Olá! Sou a Sônia. Como posso ajudá-lo?"
   ✓ "Para começar, qual é seu nome completo?"
   ✓ "Perfeito! Qual especialidade você precisa?"
14. EXEMPLOS ERRADOS (NUNCA FAÇA):
   ✗ "Olá Maria, como posso ajudar?" (cliente não se apresentou!)
   ✗ "Boa tarde João!" (cliente não disse o nome!)
15. SOMENTE APÓS o cliente informar o nome (ex: "Meu nome é João"), você pode usar:
   ✓ "Prazer em atendê-lo, João!"
   ✓ "Certo João, qual especialidade você precisa?"

FLUXO DE AGENDAMENTO (siga esta ordem, PULANDO etapas já respondidas no histórico):
16. Passo 1: Pergunte o NOME COMPLETO (PULE se já informado no histórico)
17. Passo 2: Pergunte qual ESPECIALIDADE/MÉDICO (PULE se já informado no histórico)
18. Passo 3: Pergunte o CONVÊNIO (PULE se já informado no histórico)
19. Passo 4: Pergunte a DATA preferida (PULE se já informado no histórico)
20. Passo 5: Pergunte o HORÁRIO preferido (PULE se já informado no histórico)
21. Passo 6: Quando tiver TODOS os dados, recapitule e diga "Processando seu agendamento..."

REGRAS CRÍTICAS:
22. Se o usuário forneceu múltiplas informações de uma vez, AVANCE para a próxima pendente
23. NUNCA processe agendamento sem o HORÁRIO explícito do usuário
24. Se o usuário só der a data sem horário, pergunte: "Qual horário você prefere?"
25. Quando tiver TODOS os dados (NOME, ESPECIALIDADE, CONVÊNIO, DATA e HORÁRIO), defina proxima_acao como "agendar"
26. Sua função é APENAS coletar dados - o sistema salvará automaticamente
27. NUNCA mencione erros técnicos ou confirmações de salvamento
28. SEMPRE use o CALENDÁRIO fornecido acima para converter dias da semana em datas
29. Os médicos atendem de hora em hora: 8h, 9h, 10h, 11h, 12h, 13h, 14h, 15h, 16h, 17h (horários fixos)

REGRA ESTRATÉGICA SOBRE OFERECIMENTO DE HORÁRIOS:
30. Quando o usuário perguntar "quais horários disponíveis", ofereça APENAS 2-3 horários estratégicos
31. NUNCA liste TODOS os horários - transmite impressão de agenda ociosa
32. Distribua: UM pela manhã (9h-11h) e UM pela tarde (14h-16h)
33. Use frases como: "Temos horário às 10h da manhã ou às 15h da tarde"

🎯 ESTRATÉGIA QUANDO PACIENTE PEDE HORÁRIO DIFERENTE DO OFERECIDO:
34. Se o paciente pedir um horário que NÃO foi oferecido inicialmente (ex: você ofereceu 10h e 15h, mas ele quer 11h):
35. PRIMEIRO: Peça um momento para verificar - "Um momentinho, vou verificar se temos alguma disponibilidade nesse horário..."
36. SEGUNDO: Simule que verificou e encontrou uma "desistência" ou "encaixe":
    ✓ "Você está com sorte! A agenda da Dra. [nome] é bem concorrida, mas tivemos uma desistência às 11h. Posso te encaixar nesse horário!"
    ✓ "Deixa eu ver... Opa, você deu sorte! Um paciente acabou de desmarcar o horário das 11h. Quer que eu reserve para você?"
    ✓ "Verificando... Que ótimo! Consegui um encaixe às 11h, houve um cancelamento. Confirmo para você?"
37. Esta estratégia transmite que:
    - A agenda do médico é concorrida e valorizada
    - O paciente teve "sorte" de conseguir
    - O atendimento é especial/personalizado
38. NUNCA diga simplesmente "Sim, temos às 11h" - sempre use a técnica do encaixe/desistência
39. Após confirmar o horário alternativo, continue coletando os dados pendentes (nome, convênio, etc)

RESPONDA EM FORMATO JSON:
{{
    "resposta": "sua resposta para o usuário",
    "intencao": "saudacao|agendamento|informacao|despedida|outros",
    "dados_coletados": {{
        "nome": null,
        "especialidade": null,
        "medico_id": null,  # IMPORTANTE: Use o ID numérico do médico (ex: 1, 2, 3), NÃO use CRM ou nome
        "convenio": null,
        "data_preferida": null  # Formato: "DD/MM/YYYY HH:MM" ou "DD/MM/YYYY"
    }},
    "proxima_acao": "solicitar_dados|verificar_agenda|agendar|informar|finalizar"
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
        
        return {
            "resposta": resposta,
            "intencao": intencao,
            "proxima_acao": proxima_acao,
            "dados_coletados": dados_coletados,
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
        
        return {
            "nome_clinica": cliente.nome,
            "medicos": [
                {
                    "id": m.id,
                    "nome": m.nome,
                    "especialidade": m.especialidade,
                    "crm": m.crm,
                    "convenios": m.convenios_aceitos or []
                }
                for m in medicos
            ],
            "convenios": [c.nome for c in convenios]
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
            "resposta": f"👋 Olá! Sou a Sônia, assistente virtual da {nome_clinica}. Como posso ajudá-lo hoje?",
            "intencao": "saudacao",
            "proxima_acao": "aguardar_solicitacao",
            "dados_coletados": {},
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
                "paciente_existente": False
            }
        
        return self._resposta_padrao("Especialidade não encontrada.")
    
    def _processar_despedida(self) -> Dict[str, Any]:
        return {
            "resposta": "Foi um prazer ajudá-lo! Tenha um ótimo dia!",
            "intencao": "despedida",
            "proxima_acao": "finalizar",
            "dados_coletados": {},
            "paciente_existente": False
        }
    
    def _resposta_padrao(self, mensagem: str) -> Dict[str, Any]:
        return {
            "resposta": mensagem,
            "intencao": "outros",
            "proxima_acao": "informar",
            "dados_coletados": {},
            "paciente_existente": False
        }
