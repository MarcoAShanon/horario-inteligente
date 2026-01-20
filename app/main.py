"""
Sistema Horário Inteligente SaaS - API Principal
Arquivo: app/main.py
"""
# Versão dos assets estáticos - incrementar para forçar atualização do cache nos navegadores
STATIC_VERSION = "20260119"

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import sys
from pathlib import Path
import datetime
from dotenv import load_dotenv
import os

# Rate Limiting - Proteção contra brute force
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# CSRF Protection
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pydantic import BaseModel


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware para adicionar headers de segurança em todas as respostas"""

    # Content Security Policy - recursos permitidos
    CSP_POLICY = "; ".join([
        # Scripts permitidos
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
        "cdn.jsdelivr.net cdn.tailwindcss.com cdnjs.cloudflare.com unpkg.com",

        # Estilos permitidos
        "style-src 'self' 'unsafe-inline' "
        "cdn.jsdelivr.net cdnjs.cloudflare.com fonts.googleapis.com unpkg.com",

        # Fontes permitidas
        "font-src 'self' fonts.gstatic.com cdnjs.cloudflare.com data:",

        # Imagens permitidas
        "img-src 'self' data: blob: https:",

        # Conexões permitidas (APIs)
        "connect-src 'self' https://horariointeligente.com.br https://*.horariointeligente.com.br",

        # Frames (bloqueado)
        "frame-ancestors 'none'",

        # Formulários
        "form-action 'self'",

        # Base URI
        "base-uri 'self'",

        # Upgrade requisições HTTP para HTTPS
        "upgrade-insecure-requests"
    ])

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path

        # Headers de segurança básicos
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # CSP - Content Security Policy
        response.headers["Content-Security-Policy"] = self.CSP_POLICY

        # Cache-Control para dados sensíveis (APIs com dados de pacientes/agendamentos)
        if path.startswith("/api/"):
            # APIs não devem ser cacheadas - dados sensíveis de saúde (LGPD)
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif path.startswith("/static/") and not path.endswith((".html", ".htm")):
            # Arquivos estáticos (JS, CSS, imagens) podem ser cacheados
            # Exceto HTML que pode conter dados dinâmicos
            if "Cache-Control" not in response.headers:
                response.headers["Cache-Control"] = "public, max-age=86400"  # 1 dia

        # HSTS - força HTTPS (apenas em produção)
        if os.getenv("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

# Carregar variáveis de ambiente do arquivo .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Configurar logging ANTES de qualquer import
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/sistema_agendamento/logs/sistema.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Adicionar o diretório raiz ao path se necessário
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Configurar Rate Limiter (proteção contra brute force)
# Usa IP do cliente como identificador
limiter = Limiter(key_func=get_remote_address)

# Criar instância do FastAPI
app = FastAPI(
    title="Horário Inteligente SaaS",
    description="Sistema de Agendamento Médico com WhatsApp",
    version="1.0.0"
)

# Registrar rate limiter no estado da app (para uso nos routers)
app.state.limiter = limiter

# Handler customizado para rate limit exceeded
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handler para quando o rate limit é excedido"""
    logger.warning(f"⚠️ Rate limit excedido: IP={request.client.host}, path={request.url.path}")
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Muitas tentativas. Aguarde alguns minutos antes de tentar novamente.",
            "retry_after": "60 segundos"
        }
    )

# ==================== CSRF PROTECTION ====================
class CsrfSettings(BaseModel):
    secret_key: str = os.getenv("SECRET_KEY", "csrf-secret-key-change-in-production")
    cookie_name: str = "csrf_token"
    cookie_secure: bool = os.getenv("ENVIRONMENT") == "production"  # HTTPS only em produção
    cookie_samesite: str = "lax"  # Proteção contra CSRF cross-site
    header_name: str = "X-CSRF-Token"
    token_location: str = "header"  # Token deve vir no header

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()

# Handler para erros CSRF
@app.exception_handler(CsrfProtectError)
async def csrf_error_handler(request: Request, exc: CsrfProtectError):
    """Handler para quando o token CSRF é inválido ou ausente"""
    logger.warning(f"⚠️ CSRF error: IP={request.client.host}, path={request.url.path}, error={exc.message}")
    return JSONResponse(
        status_code=403,
        content={
            "detail": "Token CSRF inválido ou ausente. Recarregue a página e tente novamente.",
            "error": "csrf_error"
        }
    )

# Configurar CORS - SEGURO (apenas domínios autorizados)
ALLOWED_ORIGINS = [
    "https://horariointeligente.com.br",
    "https://www.horariointeligente.com.br",
    "https://app.horariointeligente.com.br",
    "https://demo.horariointeligente.com.br",
    "https://admin.horariointeligente.com.br",
    # Desenvolvimento local
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Middleware de Headers de Segurança
app.add_middleware(SecurityHeadersMiddleware)
logger.info("🔒 SecurityHeadersMiddleware ativado")

# Multi-Tenant Middleware (NOVO)
from app.middleware.tenant_middleware import TenantMiddleware
app.add_middleware(TenantMiddleware)
logger.info("🏢 TenantMiddleware ativado - Sistema Multi-Tenant ATIVO")

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/docs-internos", StaticFiles(directory="docs"), name="docs")

# ========================================
# IMPORTAR E REGISTRAR ROUTERS
# ========================================

# 1. Importar todos os routers
try:
    from app.api.webhooks import router as webhook_router
    from app.api.auth import router as auth_router
    from app.api.user_management import router as user_management_router
    from app.api.dashboard import router as dashboard_router
    from app.api.configuracao import router as configuracao_router
    from app.api.agendamentos import router as agendamentos_router
    from app.api.reminders import router as reminders_router
    from app.api.tenant import router as tenant_router
    from app.api.admin import router as admin_router
    from app.api.financeiro import router as financeiro_router

    # Registrar webhook router (prioridade alta)
    app.include_router(
        webhook_router,
        prefix="/webhook",
        tags=["Webhook WhatsApp"]
    )
    
    # Registrar outros routers
    app.include_router(
        auth_router,
        prefix="/api/auth",
        tags=["Autenticação"]
    )

    app.include_router(
        user_management_router,
        prefix="/api",
        tags=["Gestão de Usuários"]
    )

    app.include_router(
        dashboard_router,
        prefix="/api/dashboard",
        tags=["Dashboard"]
    )

    app.include_router(
        configuracao_router,
        prefix="/api/configuracao",
        tags=["Configuração"]
    )

    app.include_router(
        reminders_router,
        tags=["Lembretes"]
    )

    app.include_router(
        tenant_router,
        tags=["Tenant"]
    )

    # Router Admin (sem prefix, já definido no arquivo)
    app.include_router(
        admin_router,
        tags=["Admin"]
    )

    # Router Financeiro (gestão interna SaaS)
    app.include_router(
        financeiro_router,
        tags=["Financeiro"]
    )

    # Rotas de Gestão Interna (novas)
    from app.api.usuarios_internos import router as usuarios_internos_router
    from app.api.parceiros_comerciais import router as parceiros_comerciais_router
    from app.api.custos_operacionais import router as custos_operacionais_router
    from app.api.planos import router as planos_router
    from app.api.analytics import router as analytics_router

    app.include_router(usuarios_internos_router, tags=["Usuarios Internos"])
    app.include_router(parceiros_comerciais_router, tags=["Parceiros Comerciais"])
    app.include_router(custos_operacionais_router, tags=["Custos Operacionais"])
    app.include_router(planos_router, tags=["Planos e Assinaturas"])
    app.include_router(analytics_router, tags=["Analytics"])

    # Router de Pré-Cadastro (leads de lançamento)
    from app.api.pre_cadastro import router as pre_cadastro_router
    app.include_router(pre_cadastro_router, tags=["Pre-Cadastro"])
    logger.info("✅ Router de pré-cadastro registrado")

    # Router de Conversas WhatsApp (painel de atendimento)
    from app.api.conversas import router as conversas_router
    app.include_router(conversas_router, tags=["Conversas WhatsApp"])
    logger.info("✅ Router de conversas WhatsApp registrado")

    # Router de Lembretes Inteligentes (IA conversacional)
    from app.api.lembretes import router as lembretes_router
    app.include_router(lembretes_router, tags=["Lembretes Inteligentes"])
    logger.info("✅ Router de lembretes inteligentes registrado")

    # Router WebSocket (notificações em tempo real)
    from app.api.websocket import router as websocket_router
    app.include_router(websocket_router, tags=["WebSocket"])
    logger.info("✅ Router WebSocket registrado")

    logger.info("✅ Routers principais registrados com sucesso (incluindo Admin, Financeiro e Gestão Interna)")
    
except Exception as e:
    logger.error(f"❌ Erro ao importar routers principais: {e}")
    
    # Criar webhook fallback se houver erro
    from fastapi import APIRouter
    webhook_router = APIRouter()
    
    @webhook_router.post("/whatsapp/{instance_name}")
    async def webhook_whatsapp_fallback(instance_name: str, request: Request):
        """Webhook fallback para WhatsApp"""
        try:
            data = await request.json()
            logger.info(f"Webhook recebido para {instance_name}: {data}")
            return {"status": "success", "message": "Webhook processado (fallback)"}
        except Exception as e:
            logger.error(f"Erro no webhook fallback: {e}")
            return {"status": "error", "message": str(e)}
    
    app.include_router(webhook_router, prefix="/webhook", tags=["Webhook WhatsApp"])
    logger.warning("⚠️ Usando webhook fallback")

# Registrar router de webhook para API Oficial (Meta Cloud API)
try:
    from app.api.webhook_official import router as webhook_official_router

    app.include_router(
        webhook_official_router,
        tags=["Webhook WhatsApp Official"]
    )
    logger.info("✅ Router de webhook API Oficial registrado")
except Exception as e:
    logger.warning(f"⚠️ Router de webhook API Oficial não carregado: {e}")

# Registrar router de agendamentos SEPARADAMENTE para garantir que funcione
try:
    # Se não foi importado acima, tentar importar agora
    try:
        agendamentos_router
    except NameError:
        from app.api.agendamentos import router as agendamentos_router

    app.include_router(
        agendamentos_router,
        prefix="/api",
        tags=["Agendamentos"]
    )
    logger.info("✅ Router de agendamentos registrado com sucesso")
except Exception as e:
    logger.error(f"❌ Router de agendamentos não pôde ser carregado: {e}")

# Registrar router de configuração de médicos
try:
    from app.api.medico_config import router as medico_config_router

    app.include_router(
        medico_config_router,
        prefix="/api",
        tags=["Configuração Médicos"]
    )
    logger.info("✅ Router de configuração de médicos registrado com sucesso")
except Exception as e:
    logger.error(f"❌ Router de configuração de médicos não pôde ser carregado: {e}")

# Registrar router de dashboard (DADOS REAIS)
try:
    from app.api.dashboard_simples import router as dashboard_simples_router

    app.include_router(
        dashboard_simples_router,
        prefix="/api/dashboard",
        tags=["Dashboard"]
    )
    logger.info("✅ Router de dashboard registrado com sucesso")
except Exception as e:
    logger.error(f"❌ Router de dashboard não pôde ser carregado: {e}")
    import traceback
    logger.error(traceback.format_exc())

# 2. Importar outras rotas existentes
try:
    from app.api.routes import router as api_router
    app.include_router(
        api_router,
        prefix="/api",
        tags=["API"]
    )
    logger.info("✅ API router registrado com sucesso")
except ImportError:
    logger.warning("⚠️ API routes não encontrado, continuando sem ele")
except Exception as e:
    logger.error(f"❌ Erro ao importar API router: {e}")

# ========================================
# CSRF TOKEN ENDPOINT
# ========================================

@app.get("/api/csrf-token", tags=["Segurança"])
async def get_csrf_token(request: Request, csrf_protect: CsrfProtect = Depends()):
    """
    Obtém um token CSRF para uso em formulários

    O token deve ser enviado no header X-CSRF-Token em todas as requisições POST/PUT/DELETE
    """
    # Gerar tokens CSRF (signed token para cookie, raw token para header)
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

    response = JSONResponse(content={
        "detail": "CSRF token gerado com sucesso",
        "csrf_token": csrf_token  # Token para enviar no header X-CSRF-Token
    })

    # Definir cookie com token assinado
    csrf_protect.set_csrf_cookie(signed_token, response)

    return response

# ========================================
# ROTAS DE STATUS E DEBUG
# ========================================

@app.get("/", tags=["Status"])
async def root(request: Request):
    """
    Rota raiz - Serve o site comercial ou redireciona para login
    - Domínio principal (horariointeligente.com.br): Site comercial
    - Subdomínios (prosaude.horariointeligente.com.br): Login do cliente
    - Admin (admin.horariointeligente.com.br): Login admin
    """
    # Verificar se é o painel admin
    subdomain = getattr(request.state, 'subdomain', None)
    is_admin = getattr(request.state, 'is_admin', False)
    is_demo = getattr(request.state, 'is_demo', False)

    # Obter o host completo
    host = request.headers.get("host", "").split(':')[0]  # Remove porta

    # Verificar se é acesso por IP
    import re
    is_ip_access = re.match(r'^\d+\.\d+\.\d+\.\d+$', host)

    # Se for o domínio principal (sem subdomínio ou www) ou IP direto, mostrar site comercial
    if not subdomain or subdomain == 'www' or host.startswith('horariointeligente.com.br') or is_ip_access:
        # Servir o site comercial (landing page)
        return FileResponse("static/index.html")
    elif is_admin or subdomain == 'admin':
        # Redirecionar para login admin (com versão para cache bust)
        return RedirectResponse(url=f"/static/admin/login.html?v={STATIC_VERSION}", status_code=302)
    elif is_demo or subdomain == 'demo':
        # Redirecionar para página de demo (com versão para cache bust)
        return RedirectResponse(url=f"/static/demo/index.html?v={STATIC_VERSION}", status_code=302)
    else:
        # Redirecionar para login do cliente (com versão para cache bust)
        return RedirectResponse(url=f"/static/login.html?v={STATIC_VERSION}", status_code=302)

@app.get("/sistema/status", tags=["Status"])
async def status_sistema():
    """Status detalhado do sistema"""
    
    # Verificar se webhook está registrado
    webhook_registrado = any('/webhook' in str(route.path) for route in app.routes)
    agendamentos_registrado = any('/api/agendamentos' in str(route.path) for route in app.routes)
    
    return {
        "status": "online",
        "timestamp": datetime.datetime.now().isoformat(),
        "webhook": {
            "enabled": webhook_registrado,
            "endpoint": "/webhook/whatsapp/{instance_name}",
            "evolution_api": "http://localhost:8080"
        },
        "agendamentos": {
            "enabled": agendamentos_registrado,
            "endpoint": "/api/agendamentos/calendario"
        },
        "servicos": {
            "fastapi": "running",
            "postgresql": "connected",
            "evolution_api": "configured"
        }
    }

@app.get("/sistema/rotas", tags=["Status"])
async def listar_rotas():
    """Lista todas as rotas registradas no sistema"""
    rotas = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            rotas.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": route.name if hasattr(route, 'name') else None
            })
    
    # Agrupar por categoria
    webhook_routes = [r for r in rotas if '/webhook' in r['path']]
    api_routes = [r for r in rotas if '/api' in r['path']]
    system_routes = [r for r in rotas if '/sistema' in r['path'] or r['path'] == '/']
    other_routes = [r for r in rotas if r not in webhook_routes + api_routes + system_routes]
    
    return {
        "total": len(rotas),
        "categorias": {
            "webhook": webhook_routes,
            "api": api_routes,
            "sistema": system_routes,
            "outras": other_routes
        }
    }

# ========================================
# ROTA DE TESTE DIRETO DO WEBHOOK
# ========================================

@app.post("/test/webhook", tags=["Testes"])
async def teste_webhook_direto(request: Request):
    """Rota de teste para verificar processamento de webhook"""
    try:
        data = await request.json()
        logger.info(f"Teste webhook recebido: {data}")
        
        # Simular processamento
        return {
            "status": "success",
            "message": "Webhook de teste processado",
            "data_received": data,
            "timestamp": str(datetime.datetime.now())
        }
    except Exception as e:
        logger.error(f"Erro no teste de webhook: {e}")
        return {"status": "error", "message": str(e)}

# ========================================
# EVENTOS DE STARTUP E SHUTDOWN
# ========================================

@app.on_event("startup")
async def startup_event():
    """Evento executado ao iniciar o servidor"""
    logger.info("=" * 50)
    logger.info("🚀 Sistema Horário Inteligente SaaS iniciando...")
    logger.info("=" * 50)

    # Iniciar scheduler de lembretes
    try:
        from app.scheduler import reminder_scheduler
        reminder_scheduler.start()
        logger.info("✅ Scheduler de lembretes iniciado")
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar scheduler de lembretes: {e}")
    
    # Listar todas as rotas registradas
    rotas_registradas = []
    for route in app.routes:
        if hasattr(route, 'path'):
            rotas_registradas.append(route.path)
    
    logger.info(f"📍 Total de rotas registradas: {len(rotas_registradas)}")
    
    # Verificar rotas críticas
    webhook_ok = any('/webhook' in path for path in rotas_registradas)
    api_ok = any('/api' in path for path in rotas_registradas)
    agendamentos_ok = any('/api/agendamentos' in path for path in rotas_registradas)
    
    if webhook_ok:
        logger.info("✅ Webhook routes: REGISTRADO")
    else:
        logger.error("❌ Webhook routes: NÃO ENCONTRADO")
    
    if api_ok:
        logger.info("✅ API routes: REGISTRADO")
    else:
        logger.warning("⚠️ API routes: NÃO ENCONTRADO")
    
    if agendamentos_ok:
        logger.info("✅ Agendamentos routes: REGISTRADO")
    else:
        logger.warning("⚠️ Agendamentos routes: NÃO ENCONTRADO")
    
    logger.info("=" * 50)
    logger.info("🟢 Sistema Horário Inteligente SaaS pronto!")
    logger.info(f"📡 Acesse: http://localhost:8000/docs")
    logger.info("=" * 50)

@app.on_event("shutdown")
async def shutdown_event():
    """Evento executado ao desligar o servidor"""
    logger.info("🔴 Sistema Horário Inteligente SaaS encerrando...")

    # Parar scheduler de lembretes
    try:
        from app.scheduler import reminder_scheduler
        reminder_scheduler.stop()
        logger.info("✅ Scheduler de lembretes parado")
    except Exception as e:
        logger.error(f"❌ Erro ao parar scheduler de lembretes: {e}")

# ========================================
# EXECUÇÃO PRINCIPAL
# ========================================

if __name__ == "__main__":
    import uvicorn
    
    # Configurações do servidor
    host = "0.0.0.0"
    port = 8000
    
    logger.info(f"Iniciando servidor em {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=False  # Em produção, manter False
    )
