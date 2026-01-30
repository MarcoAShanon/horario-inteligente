"""
Middleware de Multi-Tenant
Extrai o subdomínio e resolve o cliente_id automaticamente
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
import logging
import re

logger = logging.getLogger(__name__)

# Cache simples em memória (pode usar Redis em produção)
TENANT_CACHE = {}

class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware que identifica o tenant (clínica) baseado no subdomínio

    Exemplos:
    - drmarco.horariointeligente.com.br → cliente_id = X
    - drjoao.horariointeligente.com.br → cliente_id = 11
    - localhost:8000 → cliente_id = 1 (desenvolvimento)
    """

    async def dispatch(self, request: Request, call_next):
        try:
            # Rotas que não precisam de tenant (gestão interna)
            path = request.url.path
            logger.info(f"🔍 TenantMiddleware v2: path={path}")
            # Rotas autenticadas que usam cliente_id do JWT, não do subdomain
            jwt_auth_paths = [
                '/api/billing/minha', '/api/billing/minhas',
                '/api/configuracao/', '/api/dashboard/',
                '/api/agendamentos', '/api/pacientes',
                '/api/auth/', '/api/bloqueios', '/api/medicos/',
                '/api/convenios', '/api/perfil'
            ]
            if any(path.startswith(p) for p in jwt_auth_paths):
                request.state.cliente_id = None
                request.state.subdomain = 'jwt_auth'
                request.state.is_admin = False
                response = await call_next(request)
                return response
            if path.startswith('/api/financeiro/') or path.startswith('/api/gestao-interna/') or path.startswith('/api/admin/') or path.startswith('/api/interno/') or path.startswith('/api/ativacao/') or path.startswith('/api/parceiro/'):
                request.state.cliente_id = None
                request.state.subdomain = 'admin'
                request.state.is_admin = True
                logger.debug(f"🔧 Rota de gestão interna: {path}")
                response = await call_next(request)
                return response

            # Extrair subdomínio
            subdomain = self.extract_subdomain(request)
            request.state.subdomain = subdomain

            # Exceção especial para painel administrativo
            if subdomain == 'admin':
                request.state.cliente_id = None  # Admin não tem cliente_id
                request.state.is_admin = True
                logger.debug(f"🔧 Painel Admin acessado: subdomain=admin")
                response = await call_next(request)
                return response

            # Exceção especial para ambiente demo
            if subdomain == 'demo':
                request.state.cliente_id = 3  # ID fixo do cliente demo
                request.state.is_admin = False
                request.state.is_demo = True
                logger.debug(f"🎮 Ambiente Demo acessado: subdomain=demo")
                response = await call_next(request)
                return response

            # Para clientes normais, extrair cliente_id
            cliente_id = await self.get_cliente_id(request)
            request.state.cliente_id = cliente_id
            request.state.is_admin = False

            logger.debug(f"🏢 Tenant identificado: cliente_id={cliente_id}, subdomain={subdomain}")

            response = await call_next(request)
            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro no TenantMiddleware: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erro ao identificar tenant")

    def extract_subdomain(self, request: Request) -> str:
        """
        Extrai o subdomínio do host

        Exemplos:
        - drmarco.horariointeligente.com.br → drmarco
        - drjoao.horariointeligente.com.br → drjoao
        - localhost:8000 → localhost (dev)
        - 192.168.1.100:8000 → 192.168.1.100 (dev)
        """
        host = request.headers.get('host', '').split(':')[0]  # Remove porta

        # Desenvolvimento: localhost ou IP
        if host in ['localhost', '127.0.0.1'] or re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
            return 'drjoao'  # Padrão para desenvolvimento

        # Caso especial: domínio principal sem subdomínio (verificar ANTES de extrair partes)
        if host in ['horariointeligente.com.br', 'www.horariointeligente.com.br']:
            return 'admin'  # Domínio raiz vai para painel admin

        # Produção: extrair subdomínio
        parts = host.split('.')
        if len(parts) >= 4:
            # drmarco.horariointeligente.com.br → drmarco (4 partes)
            return parts[0]

        # Fallback
        return 'drjoao'

    async def get_cliente_id(self, request: Request) -> int:
        """
        Resolve o cliente_id baseado no subdomínio
        Usa cache para performance
        """
        subdomain = self.extract_subdomain(request)

        # Verificar cache
        if subdomain in TENANT_CACHE:
            return TENANT_CACHE[subdomain]

        # Buscar no banco
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            result = db.execute(
                text("SELECT id FROM clientes WHERE subdomain = :sub AND ativo = true"),
                {"sub": subdomain}
            ).fetchone()

            if not result:
                logger.warning(f"⚠️ Tenant não encontrado: {subdomain}")
                # Fallback para cliente padrão em desenvolvimento
                import os
                default_cliente = int(os.getenv('DEFAULT_CLIENTE_ID', '3'))
                if subdomain in ['localhost', 'drjoao']:
                    cliente_id = default_cliente
                    logger.info(f"🔧 Usando cliente padrão (DEFAULT_CLIENTE_ID): {cliente_id}")
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Clínica não encontrada: {subdomain}.horariointeligente.com.br"
                    )
            else:
                cliente_id = result[0]

            # Cachear resultado
            TENANT_CACHE[subdomain] = cliente_id
            logger.info(f"✅ Tenant cacheado: {subdomain} → cliente_id={cliente_id}")

            return cliente_id

        finally:
            db.close()


def get_current_tenant(request: Request) -> int:
    """
    Dependency para obter o cliente_id da request
    Uso: cliente_id = Depends(get_current_tenant)
    """
    if not hasattr(request.state, 'cliente_id'):
        raise HTTPException(status_code=500, detail="Tenant não identificado")
    return request.state.cliente_id


def clear_tenant_cache():
    """Limpa o cache de tenants (útil após criar nova clínica)"""
    global TENANT_CACHE
    TENANT_CACHE = {}
    logger.info("🗑️ Cache de tenants limpo")
