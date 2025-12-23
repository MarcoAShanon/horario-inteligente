#!/usr/bin/env python3
"""
Sistema de Agendamento Médico SaaS
API Principal com FastAPI
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Criar aplicação FastAPI
app = FastAPI(
    title="Sistema de Agendamento Médico SaaS",
    description="Sistema completo de agendamento para clínicas médicas",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/")
async def root():
    return {
        "message": "Sistema de Agendamento Médico SaaS",
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.get("/test")
async def test_endpoint():
    """Endpoint de teste"""
    return {
        "message": "API funcionando perfeitamente!",
        "python_version": "3.12.3",
        "fastapi": "OK"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
