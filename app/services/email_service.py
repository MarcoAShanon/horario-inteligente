"""
Serviço de Envio de Emails
Para recuperação de senha, notificações e formulário de contato
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os

logger = logging.getLogger(__name__)


class EmailService:
    """Serviço para envio de emails"""

    def __init__(self):
        # Configurações SMTP
        self.smtp_server = os.getenv("SMTP_HOST", "smtp.hostinger.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "465"))
        self.smtp_user = os.getenv("SMTP_USER", "contato@horariointeligente.com.br")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")

        # Remetentes
        self.noreply_email = "noreply@horariointeligente.com.br"  # Para emails automáticos
        self.contact_email = os.getenv("CONTACT_EMAIL", "contato@horariointeligente.com.br")  # Para formulário de contato
        self.from_name = "Horário Inteligente"

        # Default para emails automáticos
        self.from_email = self.noreply_email

    def send_password_recovery(
        self,
        to_email: str,
        to_name: str,
        recovery_token: str,
        base_url: str = "https://horariointeligente.com.br"
    ) -> bool:
        """
        Envia email de recuperação de senha

        Args:
            to_email: Email do destinatário
            to_name: Nome do destinatário
            recovery_token: Token de recuperação
            base_url: URL base do sistema

        Returns:
            True se enviou com sucesso, False caso contrário
        """
        try:
            # Construir link de recuperação
            recovery_link = f"{base_url}/static/reset-senha.html?token={recovery_token}"

            # Corpo do email em HTML
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .content {{
            background: white;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .button {{
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }}
        .alert {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 Recuperação de Senha</h1>
        </div>
        <div class="content">
            <p>Olá, <strong>{to_name}</strong>!</p>

            <p>Recebemos uma solicitação para redefinir a senha da sua conta no <strong>Horário Inteligente</strong>.</p>

            <p>Para criar uma nova senha, clique no botão abaixo:</p>

            <p style="text-align: center;">
                <a href="{recovery_link}" class="button">
                    Redefinir Minha Senha
                </a>
            </p>

            <div class="alert">
                <strong>⚠️ Importante:</strong>
                <ul>
                    <li>Este link expira em <strong>1 hora</strong></li>
                    <li>Se você não solicitou esta alteração, ignore este email</li>
                    <li>Sua senha atual permanece ativa até que você a redefina</li>
                </ul>
            </div>

            <p>Ou copie e cole o link abaixo no navegador:</p>
            <p style="font-size: 12px; word-break: break-all; background: #f5f5f5; padding: 10px; border-radius: 5px;">
                {recovery_link}
            </p>

            <p>Se tiver alguma dúvida, entre em contato conosco.</p>

            <p>Atenciosamente,<br>
            <strong>Equipe Horário Inteligente</strong> 💙</p>
        </div>
        <div class="footer">
            <p>Este é um email automático, por favor não responda.</p>
            <p>&copy; 2025 Horário Inteligente. Todos os direitos reservados.</p>
        </div>
    </div>
</body>
</html>
            """

            # Texto simples (fallback)
            text_body = f"""
Olá, {to_name}!

Recebemos uma solicitação para redefinir a senha da sua conta no Horário Inteligente.

Para criar uma nova senha, acesse o link abaixo:
{recovery_link}

IMPORTANTE:
- Este link expira em 1 hora
- Se você não solicitou esta alteração, ignore este email
- Sua senha atual permanece ativa até que você a redefina

Se tiver alguma dúvida, entre em contato conosco.

Atenciosamente,
Equipe Horário Inteligente
            """

            # Criar mensagem
            message = MIMEMultipart("alternative")
            message["Subject"] = "🔒 Recuperação de Senha - Horário Inteligente"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            # Anexar versões texto e HTML
            part1 = MIMEText(text_body, "plain", "utf-8")
            part2 = MIMEText(html_body, "html", "utf-8")
            message.attach(part1)
            message.attach(part2)

            # Enviar email
            if self.smtp_password:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)

                logger.info(f"✅ Email de recuperação enviado para {to_email}")
                return True
            else:
                # Modo desenvolvimento - apenas loga
                logger.warning(f"⚠️ SMTP não configurado. Email de recuperação para {to_email}:")
                logger.warning(f"Link de recuperação: {recovery_link}")
                return True

        except Exception as e:
            logger.error(f"❌ Erro ao enviar email de recuperação: {e}", exc_info=True)
            return False

    def send_email_verification(
        self,
        to_email: str,
        to_name: str,
        verification_token: str,
        base_url: str = "https://horariointeligente.com.br"
    ) -> bool:
        """
        Envia email de verificação de conta

        Args:
            to_email: Email do destinatário
            to_name: Nome do destinatário
            verification_token: Token de verificação
            base_url: URL base do sistema

        Returns:
            True se enviou com sucesso, False caso contrário
        """
        try:
            # Construir link de verificação
            verification_link = f"{base_url}/static/verificar-email.html?token={verification_token}"

            # Corpo do email em HTML
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .content {{
            background: white;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .button {{
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }}
        .info-box {{
            background: #e8f4fd;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Confirme seu Email</h1>
        </div>
        <div class="content">
            <p>Olá, <strong>{to_name}</strong>!</p>

            <p>Obrigado por se cadastrar no <strong>Horário Inteligente</strong>!</p>

            <p>Para ativar sua conta e começar a usar o sistema, confirme seu email clicando no botão abaixo:</p>

            <p style="text-align: center;">
                <a href="{verification_link}" class="button">
                    Confirmar Meu Email
                </a>
            </p>

            <div class="info-box">
                <strong>O que acontece depois?</strong>
                <p style="margin: 10px 0 0 0;">Após confirmar seu email, você poderá fazer login e começar a configurar sua agenda inteligente.</p>
            </div>

            <div class="warning">
                <strong>Importante:</strong>
                <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                    <li>Este link expira em <strong>24 horas</strong></li>
                    <li>Se você não criou esta conta, ignore este email</li>
                </ul>
            </div>

            <p>Ou copie e cole o link abaixo no navegador:</p>
            <p style="font-size: 12px; word-break: break-all; background: #f5f5f5; padding: 10px; border-radius: 5px;">
                {verification_link}
            </p>

            <p>Atenciosamente,<br>
            <strong>Equipe Horário Inteligente</strong></p>
        </div>
        <div class="footer">
            <p>Este é um email automático, por favor não responda.</p>
            <p>© 2025 Horário Inteligente. Todos os direitos reservados.</p>
        </div>
    </div>
</body>
</html>
            """

            # Texto simples (fallback)
            text_body = f"""
Olá, {to_name}!

Obrigado por se cadastrar no Horário Inteligente!

Para ativar sua conta, acesse o link abaixo:
{verification_link}

IMPORTANTE:
- Este link expira em 24 horas
- Se você não criou esta conta, ignore este email

Atenciosamente,
Equipe Horário Inteligente
            """

            # Criar mensagem
            message = MIMEMultipart("alternative")
            message["Subject"] = "Confirme seu email - Horário Inteligente"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            # Anexar versões texto e HTML
            part1 = MIMEText(text_body, "plain", "utf-8")
            part2 = MIMEText(html_body, "html", "utf-8")
            message.attach(part1)
            message.attach(part2)

            # Enviar email
            if self.smtp_password:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)

                logger.info(f"✅ Email de verificação enviado para {to_email}")
                return True
            else:
                # Modo desenvolvimento - apenas loga
                logger.warning(f"⚠️ SMTP não configurado. Email de verificação para {to_email}:")
                logger.warning(f"Link de verificação: {verification_link}")
                return True

        except Exception as e:
            logger.error(f"❌ Erro ao enviar email de verificação: {e}", exc_info=True)
            return False

    def send_welcome_email(
        self,
        to_email: str,
        to_name: str,
        user_type: str
    ) -> bool:
        """
        Envia email de boas-vindas após cadastro

        Args:
            to_email: Email do destinatário
            to_name: Nome do destinatário
            user_type: Tipo de usuário (medico/secretaria)

        Returns:
            True se enviou com sucesso
        """
        try:
            tipo_texto = "médico(a)" if user_type == "medico" else "secretária"

            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px; }}
        .content {{ padding: 30px; background: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Bem-vindo(a) ao Horário Inteligente!</h1>
        </div>
        <div class="content">
            <p>Olá, <strong>{to_name}</strong>!</p>
            <p>Seu cadastro como <strong>{tipo_texto}</strong> foi realizado com sucesso!</p>
            <p>Agora você pode acessar o sistema e começar a gerenciar sua agenda de forma inteligente.</p>
            <p>Acesse: <a href="https://horariointeligente.com.br/static/login.html">https://horariointeligente.com.br</a></p>
            <p>Atenciosamente,<br><strong>Equipe Horário Inteligente</strong> 💙</p>
        </div>
    </div>
</body>
</html>
            """

            message = MIMEMultipart("alternative")
            message["Subject"] = "🎉 Bem-vindo ao Horário Inteligente!"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            message.attach(MIMEText(html_body, "html", "utf-8"))

            if self.smtp_password:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)

                logger.info(f"✅ Email de boas-vindas enviado para {to_email}")
                return True
            else:
                logger.warning(f"⚠️ Email de boas-vindas (dev mode): {to_email}")
                return True

        except Exception as e:
            logger.error(f"❌ Erro ao enviar email de boas-vindas: {e}")
            return False

    def send_contact_form(
        self,
        nome: str,
        email: str,
        telefone: str,
        especialidade: str,
        mensagem: str
    ) -> bool:
        """
        Envia email do formulário de contato do site

        Args:
            nome: Nome do remetente
            email: Email do remetente
            telefone: Telefone/WhatsApp
            especialidade: Especialidade médica
            mensagem: Mensagem do contato

        Returns:
            True se enviou com sucesso
        """
        try:
            logger.info(f"📧 Iniciando envio de email de contato de {nome}")

            text_body = f"""Novo Contato do Site
====================

Nome: {nome}
Email: {email}
Telefone: {telefone}
Especialidade: {especialidade or 'Nao informada'}

Mensagem:
{mensagem or 'Sem mensagem'}"""

            message = MIMEMultipart()
            message["Subject"] = f"Site - {nome}"
            message["From"] = f"Horario Inteligente <{self.from_email}>"
            message["To"] = self.contact_email

            message.attach(MIMEText(text_body, "plain", "utf-8"))

            if self.smtp_password:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)

                logger.info(f"✅ Email de contato enviado: {nome} ({email})")
                return True
            else:
                logger.warning(f"⚠️ SMTP não configurado. Contato de {nome} ({email})")
                return True

        except Exception as e:
            logger.error(f"❌ Erro ao enviar email de contato: {e}", exc_info=True)
            return False


# Instância global
_email_service = None

def get_email_service() -> EmailService:
    """Factory para obter instância do serviço"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
