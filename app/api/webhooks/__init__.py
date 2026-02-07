"""
Webhook WhatsApp package — diagnostics sub-router
"""
from fastapi import APIRouter

from app.api.webhooks.diagnostics import router as diagnostics_router

router = APIRouter()
router.include_router(diagnostics_router)
