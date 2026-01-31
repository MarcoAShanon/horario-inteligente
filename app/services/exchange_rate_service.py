"""
Serviço de Cotação USD→BRL
Horário Inteligente SaaS

Consulta a AwesomeAPI para obter cotação atualizada do dólar.
Cache em memória com TTL de 30 minutos. Fallback hardcoded se API falhar.
"""

import logging
import time
import httpx

logger = logging.getLogger(__name__)

# Cache em memória
_cache_rate: float = 0.0
_cache_timestamp: float = 0.0
_CACHE_TTL_SECONDS: int = 30 * 60  # 30 minutos
_FALLBACK_RATE: float = 5.50


async def get_usd_brl_rate() -> float:
    """
    Retorna cotação USD→BRL atualizada.
    Usa cache de 30 minutos para evitar chamadas excessivas.
    """
    global _cache_rate, _cache_timestamp

    now = time.time()
    if _cache_rate > 0 and (now - _cache_timestamp) < _CACHE_TTL_SECONDS:
        return _cache_rate

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://economia.awesomeapi.com.br/json/last/USD-BRL")
            if response.status_code == 200:
                data = response.json()
                bid = float(data["USDBRL"]["bid"])
                _cache_rate = bid
                _cache_timestamp = now
                logger.info(f"[Exchange Rate] USD→BRL atualizado: {bid}")
                return bid
            else:
                logger.warning(f"[Exchange Rate] API retornou status {response.status_code}")
    except Exception as e:
        logger.warning(f"[Exchange Rate] Erro ao consultar API: {e}")

    # Fallback
    if _cache_rate > 0:
        return _cache_rate
    return _FALLBACK_RATE
