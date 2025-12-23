"""
Serviço de Preferência de Áudio - Sistema Híbrido Inteligente
Gerencia preferências de recebimento de áudio por paciente.

Modos:
- AUTO (espelho): Paciente envia áudio → resposta com áudio
                  Paciente envia texto → resposta só texto
- SEMPRE: Sempre envia texto + áudio
- NUNCA: Apenas texto, nunca áudio
"""

import logging
import re
from typing import Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Frases que indicam preferência por NÃO receber áudio
FRASES_PREFERENCIA_TEXTO = [
    "prefiro texto",
    "prefiro só texto",
    "só texto",
    "apenas texto",
    "não precisa de áudio",
    "não precisa audio",
    "nao precisa de audio",
    "sem áudio",
    "sem audio",
    "não manda áudio",
    "nao manda audio",
    "não quero áudio",
    "nao quero audio",
    "pode ser só texto",
    "só mensagem escrita",
    "prefiro ler",
    "não gosto de áudio",
    "nao gosto de audio",
]

# Frases que indicam preferência por SEMPRE receber áudio
FRASES_PREFERENCIA_AUDIO = [
    "adorei o áudio",
    "adorei o audio",
    "gostei do áudio",
    "gostei do audio",
    "pode mandar áudio",
    "pode mandar audio",
    "quero áudio",
    "quero audio",
    "prefiro áudio",
    "prefiro audio",
    "manda áudio",
    "manda audio",
    "sempre manda áudio",
    "sempre manda audio",
    "gosto de áudio",
    "gosto de audio",
    "fica mais fácil ouvir",
    "melhor ouvir",
    "prefiro ouvir",
]


def detectar_preferencia_na_mensagem(mensagem: str) -> Optional[str]:
    """
    Detecta se a mensagem contém uma preferência explícita de áudio.

    Args:
        mensagem: Texto da mensagem do paciente

    Returns:
        'nunca' se prefere só texto
        'sempre' se prefere sempre áudio
        None se não detectou preferência
    """
    mensagem_lower = mensagem.lower().strip()

    # Verificar preferência por texto (não áudio)
    for frase in FRASES_PREFERENCIA_TEXTO:
        if frase in mensagem_lower:
            logger.info(f"🔇 Preferência detectada: TEXTO (frase: '{frase}')")
            return "nunca"

    # Verificar preferência por áudio
    for frase in FRASES_PREFERENCIA_AUDIO:
        if frase in mensagem_lower:
            logger.info(f"🔊 Preferência detectada: ÁUDIO (frase: '{frase}')")
            return "sempre"

    return None


def get_preferencia_paciente(db: Session, telefone: str) -> str:
    """
    Busca a preferência de áudio do paciente no banco.

    Args:
        db: Sessão do banco de dados
        telefone: Telefone do paciente

    Returns:
        'auto', 'sempre' ou 'nunca'
    """
    try:
        result = db.execute(
            text("SELECT preferencia_audio FROM pacientes WHERE telefone = :tel LIMIT 1"),
            {"tel": telefone}
        ).fetchone()

        if result and result[0]:
            return result[0]

        return "auto"  # Padrão: modo espelho

    except Exception as e:
        logger.error(f"Erro ao buscar preferência de áudio: {e}")
        return "auto"


def salvar_preferencia_paciente(db: Session, telefone: str, preferencia: str) -> bool:
    """
    Salva a preferência de áudio do paciente.

    Args:
        db: Sessão do banco de dados
        telefone: Telefone do paciente
        preferencia: 'auto', 'sempre' ou 'nunca'

    Returns:
        True se salvou com sucesso
    """
    try:
        if preferencia not in ["auto", "sempre", "nunca"]:
            logger.warning(f"Preferência inválida: {preferencia}")
            return False

        result = db.execute(
            text("""
                UPDATE pacientes
                SET preferencia_audio = :pref, atualizado_em = NOW()
                WHERE telefone = :tel
            """),
            {"pref": preferencia, "tel": telefone}
        )

        db.commit()

        if result.rowcount > 0:
            logger.info(f"✅ Preferência de áudio salva: {telefone} → {preferencia}")
            return True
        else:
            logger.warning(f"⚠️ Paciente não encontrado: {telefone}")
            return False

    except Exception as e:
        logger.error(f"Erro ao salvar preferência de áudio: {e}")
        db.rollback()
        return False


def deve_enviar_audio(
    db: Session,
    telefone: str,
    mensagem_foi_audio: bool,
    mensagem_texto: str = ""
) -> Tuple[bool, Optional[str]]:
    """
    Determina se deve enviar áudio na resposta.
    Implementa a lógica híbrida inteligente.

    Args:
        db: Sessão do banco de dados
        telefone: Telefone do paciente
        mensagem_foi_audio: True se o paciente enviou áudio
        mensagem_texto: Texto da mensagem (para detectar preferências)

    Returns:
        Tuple (deve_enviar_audio, mensagem_confirmacao)
        - deve_enviar_audio: True/False
        - mensagem_confirmacao: Mensagem para enviar ao usuário confirmando mudança (ou None)
    """
    mensagem_confirmacao = None

    # 1. Verificar se há preferência explícita na mensagem
    nova_preferencia = detectar_preferencia_na_mensagem(mensagem_texto)

    if nova_preferencia:
        # Salvar nova preferência
        salvar_preferencia_paciente(db, telefone, nova_preferencia)

        if nova_preferencia == "nunca":
            mensagem_confirmacao = "✅ Entendi! A partir de agora vou responder apenas por texto."
            return False, mensagem_confirmacao
        elif nova_preferencia == "sempre":
            mensagem_confirmacao = "✅ Combinado! Vou sempre enviar as respostas em áudio também."
            return True, mensagem_confirmacao

    # 2. Buscar preferência salva
    preferencia = get_preferencia_paciente(db, telefone)

    # 3. Aplicar lógica baseada na preferência
    if preferencia == "nunca":
        # Nunca envia áudio
        return False, None

    elif preferencia == "sempre":
        # Sempre envia áudio
        return True, None

    else:  # "auto" - Modo espelho
        # Espelha: se paciente mandou áudio, responde com áudio
        return mensagem_foi_audio, None


def gerar_resposta_preferencia(preferencia: str, confirmando: bool = False) -> str:
    """
    Gera resposta amigável sobre preferência de áudio.

    Args:
        preferencia: A preferência atual ('auto', 'sempre', 'nunca')
        confirmando: Se está confirmando uma mudança

    Returns:
        Mensagem formatada
    """
    if confirmando:
        if preferencia == "nunca":
            return "✅ Entendi! A partir de agora vou responder apenas por texto."
        elif preferencia == "sempre":
            return "✅ Combinado! Vou sempre enviar as respostas em áudio também."
        else:
            return "✅ Voltei ao modo automático: se você enviar áudio, respondo com áudio."

    # Informando preferência atual
    if preferencia == "nunca":
        return "📝 Suas respostas estão configuradas para *apenas texto*.\nSe quiser áudio, basta dizer 'pode mandar áudio'."
    elif preferencia == "sempre":
        return "🔊 Suas respostas estão configuradas para *texto + áudio*.\nSe preferir só texto, basta dizer 'prefiro só texto'."
    else:
        return "🔄 Estou no *modo automático*: quando você envia áudio, respondo com áudio.\nVocê pode mudar dizendo 'prefiro só texto' ou 'sempre manda áudio'."
