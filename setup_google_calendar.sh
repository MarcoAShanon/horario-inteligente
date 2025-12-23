#!/bin/bash

# Setup Google Calendar API - Sistema de Agendamento Médico
# Integração com Evolution API v1.7.4

echo "🚀 CONFIGURANDO GOOGLE CALENDAR API..."

# 1. Instalar dependências Google Calendar
cd /root/sistema_agendamento
source venv/bin/activate

echo "📦 Instalando bibliotecas Google Calendar..."
pip install google-auth google-auth-oauthlib google-auth-httplib2
pip install google-api-python-client
pip install python-dateutil pytz

# 2. Criar estrutura de serviços
echo "📁 Criando estrutura de serviços..."
mkdir -p app/services/calendar
mkdir -p app/api/calendar
mkdir -p credentials

# 3. Criar serviço Google Calendar
cat > app/services/calendar/google_calendar_service.py << 'EOF'
"""
Serviço de integração com Google Calendar
Sistema de Agendamento Médico Pro-Saúde
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.medico import Medico
from ...models.agendamento import Agendamento

logger = logging.getLogger(__name__)

class GoogleCalendarService:
    """
    Serviço para integração bidirecional com Google Calendar
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ]
    
    def __init__(self):
        self.credentials_file = 'credentials/credentials.json'
        self.timezone = pytz.timezone('America/Sao_Paulo')
    
    def obter_url_autorizacao(self, medico_id: int) -> str:
        """
        Gera URL de autorização OAuth2 para o médico
        """
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.SCOPES,
                redirect_uri='http://145.223.95.35:8000/api/v1/calendar/callback'
            )
            
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=str(medico_id)
            )
            
            return authorization_url
            
        except Exception as e:
            logger.error(f"Erro ao gerar URL de autorização: {e}")
            raise
    
    async def processar_callback(self, code: str, state: str) -> Dict:
        """
        Processa callback OAuth2 e salva credenciais
        """
        try:
            medico_id = int(state)
            
            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.SCOPES,
                redirect_uri='http://145.223.95.35:8000/api/v1/calendar/callback'
            )
            
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Salvar credenciais no banco
            db = next(get_db())
            medico = db.query(Medico).filter(Medico.id == medico_id).first()
            
            if medico:
                token_data = {
                    'token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'token_uri': credentials.token_uri,
                    'client_id': credentials.client_id,
                    'client_secret': credentials.client_secret,
                    'scopes': credentials.scopes
                }
                
                medico.google_calendar_token = json.dumps(token_data)
                medico.calendario_ativo = True
                db.commit()
                
                logger.info(f"Médico {medico.nome} autorizou Google Calendar")
            
            return {
                "status": "sucesso",
                "medico_id": medico_id,
                "calendario_ativo": True
            }
            
        except Exception as e:
            logger.error(f"Erro no callback OAuth: {e}")
            raise
    
    def obter_credenciais_medico(self, medico_id: int) -> Optional[Credentials]:
        """
        Obtém credenciais válidas do médico
        """
        try:
            db = next(get_db())
            medico = db.query(Medico).filter(Medico.id == medico_id).first()
            
            if not medico or not medico.google_calendar_token:
                return None
            
            token_data = json.loads(medico.google_calendar_token)
            credentials = Credentials.from_authorized_user_info(token_data, self.SCOPES)
            
            # Renovar token se necessário
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                
                # Salvar token atualizado
                medico.google_calendar_token = credentials.to_json()
                db.commit()
            
            return credentials
            
        except Exception as e:
            logger.error(f"Erro ao obter credenciais: {e}")
            return None
    
    async def verificar_disponibilidade(
        self, 
        medico_id: int, 
        data_inicio: datetime, 
        data_fim: datetime
    ) -> List[Dict]:
        """
        Verifica disponibilidade no Google Calendar
        """
        try:
            credentials = self.obter_credenciais_medico(medico_id)
            if not credentials:
                return []  # Se não tem calendário, não há conflitos
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Converter para timezone correto
            data_inicio_utc = self.timezone.localize(data_inicio).isoformat()
            data_fim_utc = self.timezone.localize(data_fim).isoformat()
            
            # Buscar eventos no período
            events_result = service.events().list(
                calendarId='primary',
                timeMin=data_inicio_utc,
                timeMax=data_fim_utc,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            eventos = events_result.get('items', [])
            conflitos = []
            
            for evento in eventos:
                start = evento['start'].get('dateTime', evento['start'].get('date'))
                end = evento['end'].get('dateTime', evento['end'].get('date'))
                
                conflitos.append({
                    'id': evento['id'],
                    'titulo': evento.get('summary', 'Evento sem título'),
                    'inicio': start,
                    'fim': end,
                    'descricao': evento.get('description', '')
                })
            
            return conflitos
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade: {e}")
            return []
    
    async def criar_evento_agendamento(self, agendamento_id: int) -> Optional[str]:
        """
        Cria evento no Google Calendar a partir de agendamento
        """
        try:
            db = next(get_db())
            agendamento = db.query(Agendamento).filter(
                Agendamento.id == agendamento_id
            ).first()
            
            if not agendamento:
                raise ValueError("Agendamento não encontrado")
            
            credentials = self.obter_credenciais_medico(agendamento.medico_id)
            if not credentials:
                logger.warning(f"Médico {agendamento.medico_id} não tem Google Calendar configurado")
                return None
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Configurar horários
            inicio = self.timezone.localize(agendamento.data_hora)
            fim = inicio + timedelta(minutes=30)  # Consulta de 30 minutos
            
            # Configurar evento
            evento = {
                'summary': f'Consulta - {agendamento.paciente_nome}',
                'description': f'''
Paciente: {agendamento.paciente_nome}
Telefone: {agendamento.paciente_telefone}
Convênio: {agendamento.convenio.nome if agendamento.convenio else 'Particular'}
Observações: {agendamento.observacoes or 'Nenhuma'}

📱 Agendado via Sistema Pro-Saúde
                '''.strip(),
                'start': {
                    'dateTime': inicio.isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                'end': {
                    'dateTime': fim.isoformat(), 
                    'timeZone': 'America/Sao_Paulo',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 60},
                        {'method': 'popup', 'minutes': 15},
                    ],
                },
                'attendees': [
                    {
                        'email': agendamento.paciente_email,
                        'displayName': agendamento.paciente_nome
                    }
                ] if agendamento.paciente_email else []
            }
            
            # Criar evento
            evento_criado = service.events().insert(
                calendarId='primary',
                body=evento
            ).execute()
            
            # Salvar ID do evento no agendamento
            agendamento.google_event_id = evento_criado['id']
            db.commit()
            
            logger.info(f"Evento criado no Google Calendar: {evento_criado['id']}")
            return evento_criado['id']
            
        except Exception as e:
            logger.error(f"Erro ao criar evento: {e}")
            return None

# Instância singleton
google_calendar_service = GoogleCalendarService()

def get_google_calendar_service() -> GoogleCalendarService:
    return google_calendar_service
EOF

echo "✅ Serviço Google Calendar criado"

# 4. Atualizar modelo Medico para incluir campos Calendar
echo "📝 Atualizando modelo Medico..."
cat >> app/models/medico.py << 'EOF'

    # Campos Google Calendar
    google_calendar_token = Column(Text, nullable=True)
    calendario_ativo = Column(Boolean, default=False)
EOF

echo "✅ Modelo Medico atualizado"

# 5. Criar rotas Calendar API
cat > app/api/calendar/__init__.py << 'EOF'
EOF

cat > app/api/calendar/calendar_routes.py << 'EOF'
"""
Rotas para integração Google Calendar
Sistema Pro-Saúde
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from ...database import get_db
from ...models.medico import Medico
from ...services.calendar.google_calendar_service import get_google_calendar_service

router = APIRouter(prefix="/api/v1/calendar", tags=["Google Calendar"])

@router.get("/auth/{medico_id}")
async def autorizar_medico_calendar(medico_id: int):
    """
    Inicia processo de autorização Google Calendar para médico
    """
    try:
        calendar_service = get_google_calendar_service()
        url_autorizacao = calendar_service.obter_url_autorizacao(medico_id)
        
        return {
            "url_autorizacao": url_autorizacao,
            "medico_id": medico_id,
            "instrucoes": "Acesse a URL para autorizar o Google Calendar"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro na autorização: {str(e)}")

@router.get("/callback")
async def callback_google_auth(
    code: str = Query(...),
    state: str = Query(...)
):
    """
    Callback do OAuth2 Google
    """
    try:
        calendar_service = get_google_calendar_service()
        resultado = await calendar_service.processar_callback(code, state)
        
        return RedirectResponse(
            url=f"http://145.223.95.35:8000/docs?auth=success&medico={state}",
            status_code=302
        )
        
    except Exception as e:
        return RedirectResponse(
            url=f"http://145.223.95.35:8000/docs?auth=error&msg={str(e)}",
            status_code=302
        )

@router.get("/disponibilidade/{medico_id}")
async def verificar_disponibilidade_medico(
    medico_id: int,
    data_inicio: str = Query(..., description="YYYY-MM-DD HH:MM"),
    data_fim: str = Query(..., description="YYYY-MM-DD HH:MM"),
    db: Session = Depends(get_db)
):
    """
    Verifica disponibilidade do médico no Google Calendar
    """
    try:
        # Converter strings para datetime
        data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d %H:%M")
        data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d %H:%M")
        
        calendar_service = get_google_calendar_service()
        conflitos = await calendar_service.verificar_disponibilidade(
            medico_id, data_inicio_dt, data_fim_dt
        )
        
        return {
            "medico_id": medico_id,
            "periodo": {
                "inicio": data_inicio,
                "fim": data_fim
            },
            "conflitos": conflitos,
            "disponivel": len(conflitos) == 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao verificar disponibilidade: {str(e)}")

@router.get("/status/{medico_id}")
async def status_calendar_medico(medico_id: int, db: Session = Depends(get_db)):
    """
    Verifica status da integração Google Calendar do médico
    """
    try:
        medico = db.query(Medico).filter(Medico.id == medico_id).first()
        
        if not medico:
            raise HTTPException(status_code=404, detail="Médico não encontrado")
        
        return {
            "medico_id": medico_id,
            "nome": medico.nome,
            "calendario_ativo": medico.calendario_ativo,
            "tem_token": bool(medico.google_calendar_token),
            "calendario_configurado": bool(medico.google_calendar_token and medico.calendario_ativo)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
EOF

echo "✅ Rotas Calendar criadas"

echo ""
echo "🎉 GOOGLE CALENDAR API CONFIGURADO!"
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo "1. Obter credenciais Google Cloud Console"
echo "2. Baixar credentials.json"
echo "3. Testar autorização de médicos"
echo "4. Integrar com IA para verificação de disponibilidade"
echo ""
echo "🔗 FastAPI Docs: http://145.223.95.35:8000/docs"
echo "📅 Nova seção: Google Calendar"
