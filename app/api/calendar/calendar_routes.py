# app/api/calendar/calendar_routes.py
# VERSÃO CORRIGIDA - Importação ajustada
# Marco - Sistema Pro-Saúde

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging
from datetime import datetime

from ...database import get_db
from ...models.medico import Medico
from ...services.calendar.google_calendar_service import google_calendar_service  # CORREÇÃO AQUI

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/calendar",
    tags=["Google Calendar"]
)

@router.get("/auth/{medico_id}")
async def autorizar_google_calendar(
    medico_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Gera URL de autorização OAuth2 para Google Calendar
    """
    try:
        # Verificar se médico existe
        medico = db.query(Medico).filter(Medico.id == medico_id).first()
        if not medico:
            raise HTTPException(status_code=404, detail="Médico não encontrado")
        
        # Gerar URL de autorização
        url_autorizacao = google_calendar_service.get_authorization_url(medico_id)
        
        logger.info(f"URL de autorização gerada para Dr(a). {medico.nome} (ID: {medico_id})")
        
        return {
            "success": True,
            "medico_id": medico_id,
            "medico_nome": medico.nome,
            "url_autorizacao": url_autorizacao,
            "instrucoes": "Acesse a URL para autorizar o acesso ao Google Calendar"
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar autorização para médico {medico_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/callback")
async def callback_google_calendar(
    request: Request,
    code: str = Query(..., description="Código de autorização do Google"),
    state: str = Query(..., description="Estado da requisição"),
    error: str = Query(None, description="Erro retornado pelo Google"),
    db: Session = Depends(get_db)
):
    """
    Callback OAuth2 do Google Calendar
    """
    try:
        # Verificar se houve erro
        if error:
            logger.error(f"Erro no OAuth2: {error}")
            return {
                "success": False,
                "error": f"Erro na autorização: {error}"
            }
        
        # Processar callback
        resultado = google_calendar_service.handle_oauth_callback(code, state)
        
        if resultado["success"]:
            medico_id = resultado["medico_id"]
            medico = db.query(Medico).filter(Medico.id == medico_id).first()
            
            logger.info(f"Autorização Google Calendar concluída para Dr(a). {medico.nome if medico else 'Desconhecido'}")
            
            # Retornar página de sucesso simples
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Autorização Concluída - Pro-Saúde</title>
                <meta charset="utf-8">
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        text-align: center; 
                        padding: 50px;
                        background-color: #f0f8ff;
                    }}
                    .success {{ 
                        color: #28a745; 
                        font-size: 24px; 
                        margin-bottom: 20px;
                    }}
                    .info {{ 
                        color: #6c757d; 
                        font-size: 16px;
                        margin-bottom: 30px;
                    }}
                    .button {{
                        background-color: #007bff;
                        color: white;
                        padding: 12px 24px;
                        text-decoration: none;
                        border-radius: 5px;
                        font-size: 16px;
                    }}
                </style>
            </head>
            <body>
                <h1>🎉 Autorização Concluída!</h1>
                <p class="success">✅ Google Calendar integrado com sucesso!</p>
                <p class="info">
                    Dr(a). {medico.nome if medico else 'Médico'} agora pode receber agendamentos 
                    que serão sincronizados automaticamente com o Google Calendar.
                </p>
                <p class="info">
                    <strong>Próximos passos:</strong><br>
                    • Os agendamentos via WhatsApp serão criados automaticamente no seu calendar<br>
                    • Você receberá lembretes 24h e 1h antes das consultas<br>
                    • Bloqueios no calendar impedirão novos agendamentos no mesmo horário
                </p>
                <a href="http://prosaude.theleducacao.com.br" class="button">
                    🏥 Voltar ao Sistema Pro-Saúde
                </a>
            </body>
            </html>
            """
            
            return HTMLResponse(content=html_content)
        
        else:
            raise HTTPException(status_code=400, detail=resultado["error"])
            
    except Exception as e:
        logger.error(f"Erro no callback OAuth2: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro no callback: {str(e)}")

@router.get("/status/{medico_id}")
async def status_google_calendar(
    medico_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Verifica status da integração Google Calendar
    """
    try:
        # Verificar se médico existe
        medico = db.query(Medico).filter(Medico.id == medico_id).first()
        if not medico:
            raise HTTPException(status_code=404, detail="Médico não encontrado")
        
        # Verificar autorização
        is_authorized = google_calendar_service.is_authorized(medico_id)
        
        return {
            "medico_id": medico_id,
            "medico_nome": medico.nome,
            "google_calendar_autorizado": is_authorized,
            "calendario_ativo": medico.calendario_ativo if medico else False,
            "token_path": medico.google_calendar_token if medico else None,
            "status": "Autorizado e funcionando" if is_authorized else "Aguardando autorização"
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar status para médico {medico_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/disponibilidade/{medico_id}")
async def verificar_disponibilidade(
    medico_id: int,
    data_inicio: str = Query(..., description="Data/hora início (ISO format)"),
    data_fim: str = Query(..., description="Data/hora fim (ISO format)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Verifica disponibilidade do médico no Google Calendar
    """
    try:
        # Verificar se médico existe e está autorizado
        medico = db.query(Medico).filter(Medico.id == medico_id).first()
        if not medico:
            raise HTTPException(status_code=404, detail="Médico não encontrado")
        
        if not google_calendar_service.is_authorized(medico_id):
            raise HTTPException(status_code=401, detail="Médico não autorizou Google Calendar")
        
        # Converter strings para datetime
        dt_inicio = datetime.fromisoformat(data_inicio.replace('Z', '+00:00'))
        dt_fim = datetime.fromisoformat(data_fim.replace('Z', '+00:00'))
        
        # Verificar disponibilidade
        disponivel = google_calendar_service.verificar_disponibilidade(
            medico_id, dt_inicio, dt_fim
        )
        
        return {
            "medico_id": medico_id,
            "medico_nome": medico.nome,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "disponivel": disponivel,
            "message": "Horário disponível" if disponivel else "Horário ocupado"
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar disponibilidade: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/eventos-hoje/{medico_id}")
async def eventos_hoje(
    medico_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Lista eventos do médico para hoje
    """
    try:
        # Verificar autorização
        if not google_calendar_service.is_authorized(medico_id):
            raise HTTPException(status_code=401, detail="Médico não autorizou Google Calendar")
        
        # Obter eventos
        eventos = google_calendar_service.listar_eventos_hoje(medico_id)
        
        medico = db.query(Medico).filter(Medico.id == medico_id).first()
        
        return {
            "medico_id": medico_id,
            "medico_nome": medico.nome if medico else "Desconhecido",
            "data": datetime.now().strftime("%d/%m/%Y"),
            "total_eventos": len(eventos),
            "eventos": eventos
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar eventos hoje: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# Importação adicional necessária para HTMLResponse
from fastapi.responses import HTMLResponse
