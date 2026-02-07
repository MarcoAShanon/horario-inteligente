"""
Endpoints de sistema: certificado SSL.
"""
from fastapi import APIRouter, Depends
from app.api.admin import get_current_admin
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/sistema/certificado-ssl")
async def get_certificado_status(admin = Depends(get_current_admin)):
    """Retorna o status do certificado SSL wildcard"""
    import json
    import os

    status_file = "/var/run/ssl-cert-status.json"

    try:
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                status = json.load(f)
            return status
        else:
            # Gerar status em tempo real se o arquivo não existir
            import subprocess
            cert_path = "/etc/letsencrypt/live/horariointeligente.com.br-0001/fullchain.pem"

            if os.path.exists(cert_path):
                result = subprocess.run(
                    ["openssl", "x509", "-enddate", "-noout", "-in", cert_path],
                    capture_output=True, text=True
                )
                expiry_str = result.stdout.strip().split("=")[1]

                from datetime import datetime
                expiry_date = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
                days_left = (expiry_date - datetime.now()).days

                return {
                    "domain": "horariointeligente.com.br",
                    "type": "wildcard",
                    "expiry_date": expiry_str,
                    "days_left": days_left,
                    "status": "critical" if days_left <= 7 else ("warning" if days_left <= 30 else "ok"),
                    "last_check": datetime.now().isoformat(),
                    "cert_path": cert_path
                }
            else:
                return {
                    "domain": "horariointeligente.com.br",
                    "status": "error",
                    "message": "Certificado não encontrado"
                }

    except Exception as e:
        logger.error(f"[Admin] Erro ao verificar certificado SSL: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
