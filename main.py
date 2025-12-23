import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar rotas que existem
from app.api.routes import router as main_router
from app.api.calendar.calendar_routes import router as calendar_router

# Rotas de gestão interna
from app.api.usuarios_internos import router as usuarios_internos_router
from app.api.parceiros_comerciais import router as parceiros_comerciais_router
from app.api.custos_operacionais import router as custos_operacionais_router

# Criar aplicação FastAPI
app = FastAPI(
    title="Sistema Pro-Saúde",
    description="Sistema de Agendamento Médico SaaS",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Incluir rotas
app.include_router(main_router)
app.include_router(calendar_router)

# Rotas de gestão interna (admin)
app.include_router(usuarios_internos_router)
app.include_router(parceiros_comerciais_router)
app.include_router(custos_operacionais_router)

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pro-Saúde Medical</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; background: #f0f8ff; }
            .container { background: white; padding: 40px; border-radius: 15px; max-width: 600px; margin: 0 auto; }
            h1 { color: #333; }
            .status { background: #28a745; color: white; padding: 10px 20px; border-radius: 20px; display: inline-block; }
            .link { background: #667eea; color: white; padding: 15px; border-radius: 10px; text-decoration: none; margin: 10px; display: inline-block; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Pro-Saúde Medical</h1>
            <div class="status">Sistema Online</div>
            <p>Sistema de Agendamento Médico SaaS</p>
            <br>
            <a href="/docs" class="link">API Docs</a>
            <a href="/api/v1/sistema/status" class="link">Status</a>
            <a href="/api/v1/calendar/auth/1" class="link">Google Calendar</a>
        </div>
    </body>
    </html>
    """)

if __name__ == "__main__":
    print("Sistema Pro-Saúde iniciando...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
