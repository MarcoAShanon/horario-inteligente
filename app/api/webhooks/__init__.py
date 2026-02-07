"""
Webhook WhatsApp package — aggregates sub-routers
"""
from fastapi import APIRouter

from app.api.webhooks.handler import router as handler_router
from app.api.webhooks.diagnostics import router as diagnostics_router
from app.api.webhooks.qr_code import router as qr_code_router

router = APIRouter()
router.include_router(handler_router)
router.include_router(diagnostics_router)
router.include_router(qr_code_router)
