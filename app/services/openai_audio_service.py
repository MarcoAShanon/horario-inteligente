"""
Serviço de Áudio OpenAI - Whisper + TTS
Arquivo: app/services/openai_audio_service.py
Sistema Horário Inteligente - Integração de áudio WhatsApp
"""
from openai import OpenAI
import tempfile
import os
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class OpenAIAudioService:
    """
    Serviço completo de áudio usando OpenAI
    - Whisper: Speech-to-Text (receber áudios)
    - TTS: Text-to-Speech (enviar áudios)
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY não configurada no .env")

        self.client = OpenAI(api_key=api_key)

        # Configurações Whisper (Speech-to-Text)
        self.whisper_model = os.getenv("WHISPER_MODEL", "whisper-1")

        # Configurações TTS (Text-to-Speech)
        self.tts_model = os.getenv("TTS_MODEL", "tts-1")
        self.tts_voice = os.getenv("TTS_VOICE", "nova")
        self.tts_speed = float(os.getenv("TTS_SPEED", "0.9"))

        logger.info(f"✅ OpenAI Audio Service inicializado")
        logger.info(f"   📝 Whisper: {self.whisper_model}")
        logger.info(f"   🔊 TTS: {self.tts_model} | Voz: {self.tts_voice} | Velocidade: {self.tts_speed}")

    async def transcrever_audio(self, audio_path: str, language: str = "pt") -> str:
        """
        Transcreve áudio para texto usando Whisper

        Args:
            audio_path: Caminho do arquivo de áudio
            language: Código do idioma (padrão: "pt" para português)

        Returns:
            Texto transcrito em português

        Raises:
            Exception: Se houver erro na transcrição
        """
        try:
            logger.info(f"🎤 Transcrevendo áudio: {audio_path}")

            # Verificar se arquivo existe
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_path}")

            # Abrir arquivo de áudio
            with open(audio_path, "rb") as audio_file:
                # Chamar Whisper API
                transcript = self.client.audio.transcriptions.create(
                    model=self.whisper_model,
                    file=audio_file,
                    language=language,  # Força português para melhor precisão
                    response_format="text"
                )

            logger.info(f"✅ Áudio transcrito com sucesso")
            logger.info(f"   📝 Texto: {transcript[:100]}...")

            return transcript

        except Exception as e:
            logger.error(f"❌ Erro ao transcrever áudio: {e}")
            raise

    def _normalizar_texto_para_tts(self, texto: str) -> str:
        """
        Normaliza texto para melhorar a qualidade do TTS

        Remove emojis e formata texto para leitura natural

        Args:
            texto: Texto original com emojis e formatação

        Returns:
            Texto normalizado para TTS
        """
        # Remover emojis (range completo Unicode)
        # Remove emoticons, símbolos, pictogramas, etc.
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # símbolos & pictogramas
            "\U0001F680-\U0001F6FF"  # transporte & mapas
            "\U0001F1E0-\U0001F1FF"  # bandeiras
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"  # outros
            "\U0001F900-\U0001F9FF"  # símbolos suplementares
            "\U0001FA70-\U0001FAFF"  # símbolos extensão
            "]+",
            flags=re.UNICODE
        )
        texto = emoji_pattern.sub('', texto)

        # Expandir abreviações médicas para pronúncia correta
        texto = re.sub(r'\bDra\.\s+', 'Doutora ', texto)  # Dra. → Doutora
        texto = re.sub(r'\bDr\.\s+', 'Doutor ', texto)    # Dr. → Doutor

        # Converter horários para pronúncia correta
        # "11h" → "11 horas", "9h30" → "9 horas e 30", "14h" → "14 horas"
        texto = re.sub(r'\b(\d{1,2})h(\d{2})\b', r'\1 horas e \2', texto)  # 9h30 → 9 horas e 30
        texto = re.sub(r'\b(\d{1,2})h\b', r'\1 horas', texto)  # 11h → 11 horas
        texto = re.sub(r'\b(\d{1,2}):(\d{2})\b', r'\1 horas e \2', texto)  # 11:30 → 11 horas e 30

        # Converter parênteses em vírgulas para manter informação
        # "Dr. João (Cardiologista)" → "Dr. João, Cardiologista"
        texto = re.sub(r'\(([^)]+)\)', r', \1', texto)

        # Remover formatação markdown
        texto = re.sub(r'\*\*([^*]+)\*\*', r'\1', texto)  # **negrito**
        texto = re.sub(r'\*([^*]+)\*', r'\1', texto)      # *itálico*
        texto = re.sub(r'`([^`]+)`', r'\1', texto)        # `código`

        # Remover múltiplos espaços e quebras de linha
        texto = re.sub(r'\s+', ' ', texto)
        texto = texto.strip()

        return texto

    async def texto_para_audio(
        self,
        texto: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None
    ) -> str:
        """
        Converte texto em áudio usando TTS

        Args:
            texto: Texto a ser convertido em áudio
            voice: Voz (opcional, usa padrão do .env)
                  Opções: alloy, echo, fable, onyx, nova, shimmer
            speed: Velocidade 0.25-4.0 (opcional, usa padrão do .env)

        Returns:
            Caminho do arquivo de áudio MP3 gerado

        Raises:
            Exception: Se houver erro na geração do áudio
        """
        try:
            logger.info(f"🔊 Gerando áudio TTS...")
            logger.info(f"   📝 Texto original ({len(texto)} chars): {texto[:50]}...")

            # Normalizar texto para TTS (remover emojis, ajustar parênteses)
            texto_normalizado = self._normalizar_texto_para_tts(texto)
            logger.info(f"   📝 Texto normalizado: {texto_normalizado[:50]}...")

            # Usar configurações padrão se não especificado
            voice = voice or self.tts_voice
            speed = speed or self.tts_speed

            # Validar velocidade
            if not (0.25 <= speed <= 4.0):
                logger.warning(f"Velocidade {speed} fora do range, usando padrão {self.tts_speed}")
                speed = self.tts_speed

            # Gerar áudio
            response = self.client.audio.speech.create(
                model=self.tts_model,
                voice=voice,
                input=texto_normalizado,  # Usar texto normalizado
                speed=speed,
                response_format="mp3"  # WhatsApp suporta MP3
            )

            # Salvar em arquivo temporário
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".mp3",
                delete=False,
                prefix="tts_"
            )

            # Escrever dados de áudio
            response.stream_to_file(temp_file.name)

            logger.info(f"✅ Áudio gerado com sucesso")
            logger.info(f"   📁 Arquivo: {temp_file.name}")
            logger.info(f"   🎙️ Voz: {voice} | Velocidade: {speed}x")

            return temp_file.name

        except Exception as e:
            logger.error(f"❌ Erro ao gerar áudio: {e}")
            raise

    def limpar_audio(self, audio_path: str):
        """
        Remove arquivo de áudio temporário

        Args:
            audio_path: Caminho do arquivo a ser removido
        """
        try:
            if os.path.exists(audio_path):
                os.unlink(audio_path)
                logger.info(f"🗑️ Áudio removido: {audio_path}")
            else:
                logger.warning(f"⚠️ Arquivo não encontrado para remoção: {audio_path}")
        except Exception as e:
            logger.error(f"❌ Erro ao remover áudio: {e}")

    def validar_configuracao(self) -> dict:
        """
        Valida se as configurações de áudio estão corretas

        Returns:
            Dict com status da validação
        """
        status = {
            "openai_configurado": bool(os.getenv("OPENAI_API_KEY")),
            "whisper_model": self.whisper_model,
            "tts_model": self.tts_model,
            "tts_voice": self.tts_voice,
            "tts_speed": self.tts_speed,
            "audio_input_enabled": os.getenv("ENABLE_AUDIO_INPUT", "false").lower() == "true",
            "audio_output_enabled": os.getenv("ENABLE_AUDIO_OUTPUT", "false").lower() == "true",
            "audio_output_mode": os.getenv("AUDIO_OUTPUT_MODE", "text")
        }

        logger.info("🔍 Validação de configuração de áudio:")
        for key, value in status.items():
            logger.info(f"   {key}: {value}")

        return status


# Instância global do serviço (lazy loading)
_audio_service_instance = None

def get_audio_service() -> Optional[OpenAIAudioService]:
    """
    Retorna instância global do serviço de áudio (singleton)
    Retorna None se OpenAI não estiver configurada
    """
    global _audio_service_instance

    if _audio_service_instance is None:
        try:
            _audio_service_instance = OpenAIAudioService()
        except ValueError as e:
            logger.warning(f"⚠️ OpenAI Audio Service não disponível: {e}")
            return None

    return _audio_service_instance
