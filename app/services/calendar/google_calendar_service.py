# app/services/calendar/google_calendar_service.py
# VERSÃO CORRIGIDA - Resolver erro OAuth parameters
# Marco - Sistema Pro-Saúde

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
from sqlalchemy.orm import Session
from app.models.medico import Medico
from app.database import get_db

logger = logging.getLogger(__name__)

class GoogleCalendarService:
    def __init__(self):
        self.credentials_path = "/root/sistema_agendamento/credentials/credentials.json"
        self.token_dir = "/root/sistema_agendamento/credentials/tokens/"
        
        # SCOPES CORRETOS - sem problemas de encoding
        self.SCOPES = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.events'
        ]
        
        # Criar diretório de tokens se não existir
        os.makedirs(self.token_dir, exist_ok=True)
        
    def _get_flow(self) -> Flow:
        """Cria o flow OAuth2 com configurações corretas"""
        try:
            # Verificar se credentials.json existe
            if not os.path.exists(self.credentials_path):
                raise FileNotFoundError(f"Arquivo credentials.json não encontrado: {self.credentials_path}")
            
            # Criar flow com redirect URI correto
            flow = Flow.from_client_secrets_file(
                self.credentials_path,
                scopes=self.SCOPES
            )
            
            # CONFIGURAÇÃO CRÍTICA: URL de callback correta
            flow.redirect_uri = "http://prosaude.theleducacao.com.br/api/v1/calendar/callback"
            
            return flow
            
        except Exception as e:
            logger.error(f"Erro ao criar flow OAuth2: {str(e)}")
            raise
    
    def get_authorization_url(self, medico_id: int, state: str = None) -> str:
        """
        Gera URL de autorização OAuth2 CORRIGIDA
        """
        try:
            flow = self._get_flow()
            
            # Estado personalizado para identificar médico
            if not state:
                state = f"medico_{medico_id}_{int(datetime.now().timestamp())}"
            
            # PARÂMETROS CORRETOS para URL OAuth
            authorization_url, _ = flow.authorization_url(
                # CORREÇÃO CRÍTICA: parâmetros em formato correto
                access_type='offline',          # string, não boolean
                include_granted_scopes='true',  # string 'true', não boolean True
                state=state,
                prompt='consent'                # força novo consent
            )
            
            logger.info(f"URL de autorização gerada para médico {medico_id}: {authorization_url}")
            return authorization_url
            
        except Exception as e:
            logger.error(f"Erro ao gerar URL de autorização: {str(e)}")
            raise
    
    def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """
        Processa callback OAuth2 e salva token
        """
        try:
            # Extrair medico_id do state
            medico_id = int(state.split('_')[1])
            
            flow = self._get_flow()
            
            # Obter token usando código de autorização
            flow.fetch_token(code=code)
            
            # Salvar credenciais
            creds = flow.credentials
            token_path = os.path.join(self.token_dir, f"medico_{medico_id}_token.pickle")
            
            with open(token_path, 'wb') as token_file:
                pickle.dump(creds, token_file)
            
            # Atualizar banco de dados
            db = next(get_db())
            medico = db.query(Medico).filter(Medico.id == medico_id).first()
            if medico:
                medico.google_calendar_token = token_path
                medico.calendario_ativo = True
                db.commit()
            
            logger.info(f"Token OAuth2 salvo para médico {medico_id}")
            
            return {
                "success": True,
                "medico_id": medico_id,
                "message": "Autorização Google Calendar concluída com sucesso!"
            }
            
        except Exception as e:
            logger.error(f"Erro no callback OAuth2: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_credentials(self, medico_id: int) -> Optional[Credentials]:
        """Obtém credenciais salvas para um médico"""
        try:
            token_path = os.path.join(self.token_dir, f"medico_{medico_id}_token.pickle")
            
            if not os.path.exists(token_path):
                return None
            
            with open(token_path, 'rb') as token_file:
                creds = pickle.load(token_file)
            
            # Verificar se token é válido
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # Tentar renovar token
                    creds.refresh(Request())
                    # Salvar token renovado
                    with open(token_path, 'wb') as token_file:
                        pickle.dump(creds, token_file)
                else:
                    return None
            
            return creds
            
        except Exception as e:
            logger.error(f"Erro ao obter credenciais para médico {medico_id}: {str(e)}")
            return None
    
    def is_authorized(self, medico_id: int) -> bool:
        """Verifica se médico tem autorização válida"""
        creds = self._get_credentials(medico_id)
        return creds is not None and creds.valid
    
    def get_calendar_service(self, medico_id: int):
        """Obtém serviço Google Calendar para médico"""
        creds = self._get_credentials(medico_id)
        if not creds:
            raise Exception("Médico não autorizado. Execute autorização OAuth primeiro.")
        
        return build('calendar', 'v3', credentials=creds)
    
    def verificar_disponibilidade(self, medico_id: int, data_inicio: datetime, data_fim: datetime) -> bool:
        """
        Verifica se médico está disponível no período especificado
        """
        try:
            service = self.get_calendar_service(medico_id)
            
            # Buscar eventos no período
            events_result = service.events().list(
                calendarId='primary',
                timeMin=data_inicio.isoformat() + 'Z',
                timeMax=data_fim.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Se não há eventos, está disponível
            return len(events) == 0
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade: {str(e)}")
            return False
    
    def criar_agendamento(self, medico_id: int, dados_agendamento: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria evento no Google Calendar
        """
        try:
            service = self.get_calendar_service(medico_id)
            
            # Montar evento
            event = {
                'summary': f"Consulta - {dados_agendamento.get('paciente_nome', 'Paciente')}",
                'description': f"""
Consulta médica agendada via Pro-Saúde

Paciente: {dados_agendamento.get('paciente_nome', '')}
Telefone: {dados_agendamento.get('paciente_telefone', '')}
Convênio: {dados_agendamento.get('convenio', '')}
Observações: {dados_agendamento.get('observacoes', '')}
                """.strip(),
                'start': {
                    'dateTime': dados_agendamento['data_inicio'].isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                'end': {
                    'dateTime': dados_agendamento['data_fim'].isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                'attendees': [
                    {'email': dados_agendamento.get('paciente_email', '')}
                ] if dados_agendamento.get('paciente_email') else [],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 24h antes
                        {'method': 'popup', 'minutes': 60},       # 1h antes
                    ],
                },
            }
            
            # Criar evento
            created_event = service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            logger.info(f"Evento criado no Google Calendar: {created_event['id']}")
            
            return {
                "success": True,
                "event_id": created_event['id'],
                "event_url": created_event.get('htmlLink')
            }
            
        except Exception as e:
            logger.error(f"Erro ao criar agendamento no Calendar: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def listar_eventos_hoje(self, medico_id: int) -> List[Dict[str, Any]]:
        """Lista eventos do médico para hoje"""
        try:
            service = self.get_calendar_service(medico_id)
            
            # Período de hoje
            hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            amanha = hoje + timedelta(days=1)
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=hoje.isoformat() + 'Z',
                timeMax=amanha.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            eventos_formatados = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                eventos_formatados.append({
                    'id': event['id'],
                    'titulo': event.get('summary', 'Sem título'),
                    'inicio': start,
                    'descricao': event.get('description', ''),
                    'link': event.get('htmlLink', '')
                })
            
            return eventos_formatados
            
        except Exception as e:
            logger.error(f"Erro ao listar eventos: {str(e)}")
            return []

# Instância global do serviço
google_calendar_service = GoogleCalendarService()
