"""
Middleware de Bloqueio para Inadimplentes
Redireciona clientes com assinatura suspensa para tela de pagamento
"""
from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


class BillingMiddleware(BaseHTTPMiddleware):
    """
    Bloqueia acesso ao sistema para clientes inadimplentes.

    Comportamento:
    - Verifica se cliente está ativo (cliente.ativo = true)
    - Se inativo, redireciona para /static/conta-suspensa.html
    - Rotas essenciais são liberadas (login, pagamento, webhooks, etc)
    """

    # Rotas que SEMPRE são liberadas (mesmo para inadimplentes)
    ROTAS_LIBERADAS = [
        # Páginas de bloqueio e login
        '/static/conta-suspensa.html',
        '/static/login.html',
        '/static/esqueci-senha.html',

        # APIs essenciais
        '/api/auth/',
        '/api/billing/',  # Todas rotas de billing são liberadas (para inadimplentes verem faturas)

        # Webhooks (precisam funcionar sempre)
        '/api/webhooks/',
        '/webhook/',

        # Admin (gestão interna)
        '/api/admin/',
        '/api/interno/',
        '/api/financeiro/',
        '/api/gestao-interna/',
        '/static/admin/',

        # Assets estáticos
        '/static/css/',
        '/static/js/',
        '/static/images/',
        '/static/icons/',
        '/static/manifest.json',
        '/static/service-worker.js',
        '/favicon.ico',

        # Docs da API
        '/docs',
        '/redoc',
        '/openapi.json',
    ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 1. Verificar se é rota liberada
        if self._is_rota_liberada(path):
            return await call_next(request)

        # 2. Verificar se tem cliente_id no request.state (definido pelo TenantMiddleware)
        cliente_id = getattr(request.state, 'cliente_id', None)

        # Se não tem cliente_id, deixa passar (pode ser admin ou rota sem tenant)
        if not cliente_id:
            return await call_next(request)

        # 3. Verificar se cliente está ativo
        cliente_ativo = await self._verificar_cliente_ativo(cliente_id)

        if not cliente_ativo:
            logger.warning(f"[BILLING] Cliente {cliente_id} bloqueado - inadimplente")

            # Se for requisição de API, retorna JSON
            if path.startswith('/api/'):
                return JSONResponse(
                    status_code=402,  # Payment Required
                    content={
                        "detail": "Sua assinatura está suspensa por inadimplência",
                        "error": "payment_required",
                        "redirect": "/static/conta-suspensa.html"
                    }
                )

            # Se for página, redireciona
            return RedirectResponse(
                url=f"/static/conta-suspensa.html?cliente_id={cliente_id}",
                status_code=302
            )

        # 4. Cliente ativo, continua normalmente
        return await call_next(request)

    def _is_rota_liberada(self, path: str) -> bool:
        """Verifica se a rota está na lista de liberadas"""
        for rota in self.ROTAS_LIBERADAS:
            if path.startswith(rota):
                return True
        return False

    async def _verificar_cliente_ativo(self, cliente_id: int) -> bool:
        """Verifica no banco se o cliente está ativo"""
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            result = db.execute(
                text("SELECT ativo FROM clientes WHERE id = :id"),
                {"id": cliente_id}
            ).fetchone()

            if result:
                return result[0]  # True = ativo, False = inativo

            return True  # Se não encontrou, deixa passar

        except Exception as e:
            logger.error(f"Erro ao verificar cliente ativo: {e}")
            return True  # Em caso de erro, não bloqueia
        finally:
            db.close()
