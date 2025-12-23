"""
API para dados do Tenant (Cliente) atual
Arquivo: app/api/tenant.py
"""
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.cliente import Cliente
from pydantic import BaseModel

router = APIRouter()

class TenantBranding(BaseModel):
    """Modelo de resposta com dados de branding do tenant"""
    nome: str
    subdomain: str | None
    logo_url: str | None
    logo_icon: str
    cor_primaria: str
    cor_secundaria: str
    favicon_url: str | None
    whatsapp_numero: str | None

    class Config:
        from_attributes = True


@router.get("/api/tenant/branding", response_model=TenantBranding, tags=["Tenant"])
async def get_tenant_branding(request: Request):
    """
    Retorna os dados de branding do tenant atual (baseado no subdomínio).

    Este endpoint é público (não requer autenticação) para permitir que a
    página de login carregue o branding antes do usuário fazer login.
    """
    # Obter cliente_id injetado pelo TenantMiddleware
    cliente_id = getattr(request.state, 'cliente_id', None)

    if not cliente_id:
        raise HTTPException(
            status_code=400,
            detail="Cliente não identificado. Verifique o subdomínio."
        )

    # Buscar dados do cliente
    db: Session = next(get_db())
    try:
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()

        if not cliente:
            raise HTTPException(
                status_code=404,
                detail="Cliente não encontrado"
            )

        return TenantBranding(
            nome=cliente.nome,
            subdomain=cliente.subdomain,
            logo_url=cliente.logo_url,
            logo_icon=cliente.logo_icon,
            cor_primaria=cliente.cor_primaria,
            cor_secundaria=cliente.cor_secundaria,
            favicon_url=cliente.favicon_url,
            whatsapp_numero=cliente.whatsapp_numero
        )
    finally:
        db.close()


@router.get("/api/tenant/info", tags=["Tenant"])
async def get_tenant_info(request: Request):
    """
    Retorna informações básicas do tenant atual.
    Endpoint público para debug e verificação.
    """
    cliente_id = getattr(request.state, 'cliente_id', None)
    tenant = getattr(request.state, 'tenant', None)

    return {
        "cliente_id": cliente_id,
        "subdomain": tenant,
        "host": request.headers.get("host", "desconhecido")
    }
