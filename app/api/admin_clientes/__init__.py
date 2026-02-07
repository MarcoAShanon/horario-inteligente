"""
API de Gestão de Clientes - Painel Admin
Endpoints para onboarding e gestão de clínicas
"""
from fastapi import APIRouter

from app.api.admin_clientes.onboarding import router as onboarding_router
from app.api.admin_clientes.crud import router as crud_router
from app.api.admin_clientes.profissionais import router as profissionais_router
from app.api.admin_clientes.configuracoes import router as configuracoes_router
from app.api.admin_clientes.sistema import router as sistema_router

router = APIRouter(prefix="/api/admin", tags=["Admin - Clientes"])

router.include_router(onboarding_router)
router.include_router(crud_router)
router.include_router(profissionais_router)
router.include_router(configuracoes_router)
router.include_router(sistema_router)
