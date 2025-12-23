"""
Helper para trabalhar com timezones de forma consistente.
Timezone padrão: America/Sao_Paulo (Brasília, UTC-3)
"""
from datetime import datetime
import pytz

# Timezone de Brasília
BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')


def now_brazil() -> datetime:
    """
    Retorna datetime atual em horário de Brasília (timezone-aware).

    Returns:
        datetime: Hora atual em Brasília com timezone

    Example:
        >>> agora = now_brazil()
        >>> print(agora)
        2025-12-01 11:30:00-03:00
    """
    return datetime.now(BRAZIL_TZ)


def make_aware_brazil(dt: datetime) -> datetime:
    """
    Converte um datetime naive (sem timezone) para timezone-aware em horário de Brasília.
    Assume que o datetime fornecido é em horário de Brasília.

    Args:
        dt: datetime sem timezone

    Returns:
        datetime: datetime com timezone de Brasília

    Example:
        >>> dt_naive = datetime(2025, 12, 1, 14, 30)
        >>> dt_aware = make_aware_brazil(dt_naive)
        >>> print(dt_aware)
        2025-12-01 14:30:00-03:00
    """
    if dt.tzinfo is not None:
        # Já tem timezone, converte para Brasília
        return dt.astimezone(BRAZIL_TZ)

    # Assume que é horário de Brasília e adiciona timezone
    return BRAZIL_TZ.localize(dt)


def parse_datetime_brazil(date_str: str, time_str: str) -> datetime:
    """
    Cria um datetime timezone-aware a partir de strings de data e hora.
    Assume que a data/hora fornecida é em horário de Brasília.

    Args:
        date_str: Data no formato YYYY-MM-DD (ex: "2025-12-01")
        time_str: Hora no formato HH:MM (ex: "14:30")

    Returns:
        datetime: datetime timezone-aware em horário de Brasília

    Example:
        >>> dt = parse_datetime_brazil("2025-12-01", "14:30")
        >>> print(dt)
        2025-12-01 14:30:00-03:00
    """
    # Parse como datetime naive
    dt_naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

    # Adiciona timezone de Brasília
    return BRAZIL_TZ.localize(dt_naive)


def to_brazil(dt_utc: datetime) -> datetime:
    """
    Converte um datetime UTC para horário de Brasília.

    Args:
        dt_utc: datetime em UTC

    Returns:
        datetime: datetime em horário de Brasília

    Example:
        >>> dt_utc = datetime(2025, 12, 1, 17, 30, tzinfo=pytz.utc)
        >>> dt_brazil = to_brazil(dt_utc)
        >>> print(dt_brazil)
        2025-12-01 14:30:00-03:00
    """
    if dt_utc.tzinfo is None:
        # Assume UTC se não tem timezone
        dt_utc = pytz.utc.localize(dt_utc)

    return dt_utc.astimezone(BRAZIL_TZ)


def format_brazil(dt: datetime, include_seconds: bool = False) -> str:
    """
    Formata um datetime para exibição em formato brasileiro.

    Args:
        dt: datetime a ser formatado (pode ser naive ou aware)
        include_seconds: Se True, inclui segundos no formato

    Returns:
        str: Data/hora formatada (ex: "01/12/2025 14:30" ou "01/12/2025 14:30:00")

    Example:
        >>> dt = parse_datetime_brazil("2025-12-01", "14:30")
        >>> print(format_brazil(dt))
        01/12/2025 às 14:30
    """
    # Se for naive, assume que é Brasília
    if dt.tzinfo is None:
        dt = make_aware_brazil(dt)
    else:
        # Converte para Brasília
        dt = dt.astimezone(BRAZIL_TZ)

    if include_seconds:
        return dt.strftime("%d/%m/%Y às %H:%M:%S")
    else:
        return dt.strftime("%d/%m/%Y às %H:%M")
