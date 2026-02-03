"""
Serviço de Envio de Emails e Notificações
Para recuperação de senha, notificações, formulário de contato e Telegram
"""
import smtplib
import logging
from email.message import EmailMessage
from typing import Optional
import os
import urllib.request
import urllib.parse
import json

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
        self.contact_email = os.getenv("CONTACT_EMAIL", "contato@horariointeligente.com.br")  # Para formulário de contato
        self.from_name = "Horário Inteligente"

        # Default para emails automáticos — deve ser o mesmo do SMTP_USER para evitar bloqueio por MailChannels
        self.from_email = self.smtp_user

        # Configurações Telegram
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

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
            <p>&copy; 2026 Horário Inteligente. Todos os direitos reservados.</p>
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
            message = EmailMessage()
            message["Subject"] = "🔒 Recuperação de Senha - Horário Inteligente"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            message.set_content(text_body)
            message.add_alternative(html_body, subtype='html', cte='base64')

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
            message = EmailMessage()
            message["Subject"] = "Confirme seu email - Horário Inteligente"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            message.set_content(text_body)
            message.add_alternative(html_body, subtype='html', cte='base64')

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

            message = EmailMessage()
            message["Subject"] = "🎉 Bem-vindo ao Horário Inteligente!"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            message.set_content(html_body, subtype='html', cte='base64')

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

    def send_pre_cadastro_confirmation(
        self,
        to_email: str,
        to_name: str
    ) -> bool:
        """
        Envia email de confirmação de pré-cadastro para o lead

        Args:
            to_email: Email do destinatário
            to_name: Nome do destinatário

        Returns:
            True se enviou com sucesso, False caso contrário
        """
        try:
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
            background: linear-gradient(135deg, #3B82F6 0%, #06B6D4 100%);
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
        .benefit {{
            display: flex;
            align-items: center;
            margin: 15px 0;
            padding: 10px;
            background: #f0fdf4;
            border-radius: 8px;
        }}
        .benefit-icon {{
            font-size: 20px;
            margin-right: 10px;
        }}
        .button {{
            display: inline-block;
            padding: 15px 30px;
            background: #10B981;
            color: white !important;
            text-decoration: none;
            border-radius: 8px;
            margin: 20px 0;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Voce esta na lista VIP!</h1>
        </div>
        <div class="content">
            <p>Ola, <strong>{to_name}</strong>!</p>

            <p>Obrigado por se cadastrar para o pre-lancamento do <strong>Horario Inteligente</strong>!</p>

            <p>Voce agora faz parte da nossa lista VIP e tera acesso a:</p>

            <div class="benefit">
                <span class="benefit-icon">&#10003;</span>
                <span><strong>Desconto exclusivo</strong> na taxa de ativacao</span>
            </div>

            <div class="benefit">
                <span class="benefit-icon">&#10003;</span>
                <span><strong>Preco promocional</strong> de lancamento</span>
            </div>

            <div class="benefit">
                <span class="benefit-icon">&#10003;</span>
                <span><strong>Suporte prioritario</strong> na implantacao</span>
            </div>

            <div class="benefit">
                <span class="benefit-icon">&#127873;</span>
                <span><strong>Bonus surpresa</strong> para os primeiros cadastrados</span>
            </div>

            <p>Fique de olho no seu email e WhatsApp - em breve entraremos em contato com as condicoes especiais!</p>

            <p>Enquanto isso, voce pode explorar nosso ambiente de demonstracao:</p>

            <p style="text-align: center;">
                <a href="https://demo.horariointeligente.com.br" class="button">
                    Acessar Demonstracao
                </a>
            </p>

            <p>Qualquer duvida, e so responder este email.</p>

            <p>Ate breve!<br>
            <strong>Equipe Horario Inteligente</strong></p>
        </div>
        <div class="footer">
            <p>Voce recebeu este email porque se cadastrou em horariointeligente.com.br</p>
            <p>Para cancelar, responda este email com "CANCELAR"</p>
            <p>&copy; 2026 Horario Inteligente. Todos os direitos reservados.</p>
        </div>
    </div>
</body>
</html>
            """

            text_body = f"""
Ola, {to_name}!

Obrigado por se cadastrar para o pre-lancamento do Horario Inteligente!

Voce agora faz parte da nossa lista VIP e tera acesso a:

- Desconto exclusivo na taxa de ativacao
- Preco promocional de lancamento
- Suporte prioritario na implantacao
- Bonus surpresa para os primeiros cadastrados

Fique de olho no seu email e WhatsApp - em breve entraremos em contato com as condicoes especiais!

Enquanto isso, voce pode explorar nosso ambiente de demonstracao:
https://demo.horariointeligente.com.br

Qualquer duvida, e so responder este email.

Ate breve!
Equipe Horario Inteligente

---
Voce recebeu este email porque se cadastrou em horariointeligente.com.br
Para cancelar, responda este email com "CANCELAR"
            """

            message = EmailMessage()
            message["Subject"] = "Voce esta na lista VIP do Horario Inteligente!"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            message.set_content(text_body)
            message.add_alternative(html_body, subtype='html', cte='base64')

            if self.smtp_password:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)

                logger.info("Email de confirmacao de pre-cadastro enviado")
                return True
            else:
                logger.warning("SMTP nao configurado - email de pre-cadastro nao enviado")
                return True

        except Exception as e:
            logger.error(f"Erro ao enviar email de pre-cadastro: {e}", exc_info=True)
            return False

    def send_admin_notification_pre_cadastro(
        self,
        lead_data: dict,
        total_cadastros: int
    ) -> bool:
        """
        Envia notificacao ao admin sobre novo pre-cadastro

        Args:
            lead_data: Dados do lead (nome, email, whatsapp, profissao, cidade_estado, usa_sistema, nome_sistema_atual, origem)
            total_cadastros: Total de pre-cadastros ate o momento

        Returns:
            True se enviou com sucesso, False caso contrario
        """
        try:
            sistema_atual = lead_data.get('usa_sistema', 'Nao informado')
            if lead_data.get('nome_sistema_atual'):
                sistema_atual += f" ({lead_data['nome_sistema_atual']})"

            text_body = f"""Novo pre-cadastro!

Nome: {lead_data.get('nome', 'N/A')}
Email: {lead_data.get('email', 'N/A')}
WhatsApp: {lead_data.get('whatsapp', 'N/A')}
Profissao: {lead_data.get('profissao', 'N/A')}
Cidade/Estado: {lead_data.get('cidade_estado', 'N/A')}
Sistema atual: {sistema_atual}
Origem: {lead_data.get('origem', 'Nao informado')}
Data: {lead_data.get('data_cadastro', 'N/A')}

Total de pre-cadastros: {total_cadastros}
"""

            message = EmailMessage()
            message["Subject"] = f"Novo pre-cadastro - {lead_data.get('nome', 'Lead')}"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = self.contact_email

            message.set_content(text_body)

            if self.smtp_password:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)

                logger.info(f"Notificacao de pre-cadastro enviada ao admin")
                return True
            else:
                logger.warning(f"SMTP nao configurado. Notificacao admin: {lead_data.get('nome')}")
                return True

        except Exception as e:
            logger.error(f"Erro ao enviar notificacao admin: {e}", exc_info=True)
            return False

    def send_telegram_notification(
        self,
        message: str,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        Envia notificação via Telegram

        Args:
            message: Mensagem a ser enviada
            parse_mode: Formato da mensagem (HTML ou Markdown)

        Returns:
            True se enviou com sucesso, False caso contrário
        """
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram nao configurado. Pulando notificacao.")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"

            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": parse_mode
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get("ok"):
                    logger.info("Notificacao Telegram enviada com sucesso")
                    return True
                else:
                    logger.error(f"Erro Telegram: {result}")
                    return False

        except Exception as e:
            logger.error(f"Erro ao enviar Telegram: {e}", exc_info=True)
            return False

    def send_telegram_pre_cadastro(
        self,
        lead_data: dict,
        total_cadastros: int
    ) -> bool:
        """
        Envia notificação de pré-cadastro via Telegram

        Args:
            lead_data: Dados do lead
            total_cadastros: Total de pré-cadastros

        Returns:
            True se enviou com sucesso
        """
        sistema_atual = lead_data.get('usa_sistema', 'Nao informado')
        if lead_data.get('nome_sistema_atual'):
            sistema_atual += f" ({lead_data['nome_sistema_atual']})"

        message = f"""🆕 <b>Novo Pré-Cadastro!</b>

👤 <b>Nome:</b> {lead_data.get('nome', 'N/A')}
📧 <b>Email:</b> {lead_data.get('email', 'N/A')}
📱 <b>WhatsApp:</b> {lead_data.get('whatsapp', 'N/A')}
🩺 <b>Profissão:</b> {lead_data.get('profissao', 'N/A')}
📍 <b>Cidade:</b> {lead_data.get('cidade_estado', 'N/A')}
💻 <b>Sistema atual:</b> {sistema_atual}
🔗 <b>Origem:</b> {lead_data.get('origem', 'Nao informado')}

📊 <b>Total de cadastros:</b> {total_cadastros}"""

        return self.send_telegram_notification(message)

    def send_ativacao_conta(
        self,
        to_email: str,
        to_name: str,
        token: str,
        base_url: str = "https://horariointeligente.com.br"
    ) -> bool:
        """
        Envia email com link de ativação de conta (aceite de termos).
        O link expira em 7 dias.
        """
        try:
            activation_link = f"{base_url}/static/ativar-conta.html?token={token}"

            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
        .info-box {{ background: #e8f4fd; border-left: 4px solid #667eea; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .step {{ display: flex; align-items: flex-start; margin: 10px 0; }}
        .step-number {{ background: #667eea; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; margin-right: 10px; flex-shrink: 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Ative Sua Conta</h1>
        </div>
        <div class="content">
            <p>Ola, <strong>{to_name}</strong>!</p>

            <p>Sua conta no <strong>Horario Inteligente</strong> foi criada com sucesso! Para comecar a usar o sistema, voce precisa aceitar nossos termos de uso e politica de privacidade.</p>

            <p style="text-align: center;">
                <a href="{activation_link}" class="button">
                    Ativar Minha Conta
                </a>
            </p>

            <div class="info-box">
                <strong>Proximos passos:</strong>
                <div style="margin-top: 10px;">
                    <div class="step">
                        <span class="step-number">1</span>
                        <span>Acesse a pagina de ativacao pelo link acima</span>
                    </div>
                    <div class="step">
                        <span class="step-number">2</span>
                        <span>Revise e aceite os termos de uso e politica de privacidade</span>
                    </div>
                    <div class="step">
                        <span class="step-number">3</span>
                        <span>Sua conta sera ativada e voce podera fazer login</span>
                    </div>
                </div>
            </div>

            <div class="warning">
                <strong>Importante:</strong>
                <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                    <li>Este link e valido por <strong>7 dias</strong></li>
                    <li>Se voce nao solicitou este cadastro, ignore este email</li>
                </ul>
            </div>

            <p>Ou copie e cole o link abaixo no navegador:</p>
            <p style="font-size: 12px; word-break: break-all; background: #f5f5f5; padding: 10px; border-radius: 5px;">
                {activation_link}
            </p>

            <p>Atenciosamente,<br>
            <strong>Equipe Horario Inteligente</strong></p>
        </div>
        <div class="footer">
            <p>Duvidas? Responda este email ou acesse horariointeligente.com.br</p>
            <p>&copy; 2026 Horario Inteligente. Todos os direitos reservados.</p>
        </div>
    </div>
</body>
</html>
            """

            text_body = f"""
Ola, {to_name}!

Sua conta no Horario Inteligente foi criada com sucesso!

Para ativar sua conta, acesse o link abaixo:
{activation_link}

Proximos passos:
1. Acesse o link acima
2. Aceite os termos de uso e politica de privacidade
3. Sua conta sera ativada

IMPORTANTE:
- Este link e valido por 7 dias
- Se voce nao solicitou este cadastro, ignore este email

Atenciosamente,
Equipe Horario Inteligente
            """

            message = EmailMessage()
            message["Subject"] = "Ative sua conta - Horario Inteligente"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Reply-To"] = "contato@horariointeligente.com.br"

            message.set_content(text_body)
            message.add_alternative(html_body, subtype='html', cte='base64')

            if self.smtp_password:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)

                logger.info(f"Email de ativacao enviado para {to_email}")
                return True
            else:
                logger.warning(f"SMTP nao configurado. Link de ativacao: {activation_link}")
                return True

        except Exception as e:
            logger.error(f"Erro ao enviar email de ativacao: {e}", exc_info=True)
            return False

    def send_boas_vindas_ativacao(
        self,
        to_email: str,
        to_name: str,
        subdomain: str
    ) -> bool:
        """
        Envia email de boas-vindas apos ativacao da conta (aceite de termos).
        """
        try:
            login_url = f"https://{subdomain}.horariointeligente.com.br/static/login.html"

            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; }}
        .header {{ background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white !important; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
        .info-box {{ background: #ecfdf5; border-left: 4px solid #10B981; padding: 15px; margin: 20px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Conta Ativada com Sucesso!</h1>
        </div>
        <div class="content">
            <p>Ola, <strong>{to_name}</strong>!</p>

            <p>Sua conta no <strong>Horario Inteligente</strong> foi ativada com sucesso! Agora voce pode acessar o sistema e comecar a gerenciar sua agenda de forma inteligente.</p>

            <p style="text-align: center;">
                <a href="{login_url}" class="button">
                    Acessar o Sistema
                </a>
            </p>

            <div class="info-box">
                <strong>Seu acesso:</strong>
                <p style="margin: 10px 0 0 0;">
                    URL: <strong>{login_url}</strong><br>
                    Use seu email cadastrado e a senha que voce criou durante a ativacao para fazer login.
                </p>
            </div>

            <p>Se tiver alguma duvida, entre em contato conosco.</p>

            <p>Atenciosamente,<br>
            <strong>Equipe Horario Inteligente</strong></p>
        </div>
        <div class="footer">
            <p>Duvidas? Responda este email ou acesse horariointeligente.com.br</p>
            <p>&copy; 2026 Horario Inteligente. Todos os direitos reservados.</p>
        </div>
    </div>
</body>
</html>
            """

            message = EmailMessage()
            message["Subject"] = "Sua conta esta pronta - Horario Inteligente"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Reply-To"] = "contato@horariointeligente.com.br"

            text_body = f"""
Ola, {to_name}!

Sua conta no Horario Inteligente foi ativada com sucesso! Agora voce pode acessar o sistema e comecar a gerenciar sua agenda de forma inteligente.

Seu acesso:
URL: {login_url}
Use seu email cadastrado e a senha que voce criou durante a ativacao para fazer login.

Se tiver alguma duvida, entre em contato conosco.

Atenciosamente,
Equipe Horario Inteligente
            """

            message.set_content(text_body)
            message.add_alternative(html_body, subtype='html', cte='base64')

            if self.smtp_password:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)

                logger.info(f"Email de boas-vindas pos-ativacao enviado para {to_email}")
                return True
            else:
                logger.warning(f"SMTP nao configurado. Boas-vindas para {to_email}")
                return True

        except Exception as e:
            logger.error(f"Erro ao enviar email de boas-vindas: {e}", exc_info=True)
            return False

    def send_notificacao_parceiro_ativacao(
        self,
        parceiro_email: str,
        parceiro_nome: str,
        cliente_nome: str
    ) -> bool:
        """
        Notifica parceiro que um cliente indicado por ele ativou a conta.
        """
        try:
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 10px; }}
        .content {{ padding: 30px; background: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Cliente Ativado!</h1>
        </div>
        <div class="content">
            <p>Ola, <strong>{parceiro_nome}</strong>!</p>
            <p>O cliente <strong>{cliente_nome}</strong>, indicado por voce, acaba de ativar a conta no Horario Inteligente.</p>
            <p>Voce pode acompanhar seus clientes e comissoes no Portal do Parceiro.</p>
            <p>Atenciosamente,<br><strong>Equipe Horario Inteligente</strong></p>
        </div>
    </div>
</body>
</html>
            """

            message = EmailMessage()
            message["Subject"] = f"Cliente {cliente_nome} ativou a conta - Horario Inteligente"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = parceiro_email

            message.set_content(html_body, subtype='html', cte='base64')

            if self.smtp_password:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)

                logger.info(f"Notificacao de ativacao enviada ao parceiro {parceiro_nome}")
                return True
            else:
                logger.warning(f"SMTP nao configurado. Notificacao parceiro: {parceiro_nome}")
                return True

        except Exception as e:
            logger.error(f"Erro ao notificar parceiro: {e}", exc_info=True)
            return False

    def send_credenciais_acesso(
        self,
        to_email: str,
        to_name: str,
        login_url: str,
        email_login: str,
        senha_temporaria: str,
        nome_clinica: str
    ) -> bool:
        """
        Envia email com credenciais de acesso ao profissional.

        Args:
            to_email: Email do destinatario
            to_name: Nome do profissional
            login_url: URL de login do sistema
            email_login: Email para login
            senha_temporaria: Senha temporaria gerada
            nome_clinica: Nome da clinica/cliente

        Returns:
            True se enviou com sucesso, False caso contrario
        """
        try:
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
        .credentials-box {{ background: #f0f4ff; border: 2px solid #667eea; border-radius: 8px; padding: 20px; margin: 20px 0; }}
        .credentials-box p {{ margin: 8px 0; }}
        .credentials-label {{ color: #666; font-size: 13px; margin-bottom: 2px; }}
        .credentials-value {{ color: #1a1a2e; font-family: monospace; font-size: 16px; font-weight: bold; background: #e8ecf8; padding: 6px 10px; border-radius: 4px; display: inline-block; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Suas Credenciais de Acesso</h1>
        </div>
        <div class="content">
            <p>Ola, <strong>{to_name}</strong>!</p>

            <p>Suas credenciais de acesso ao sistema <strong>Horario Inteligente</strong> para a clinica <strong>{nome_clinica}</strong> estao prontas.</p>

            <div class="credentials-box">
                <p class="credentials-label">URL de acesso:</p>
                <p><span class="credentials-value">{login_url}</span></p>

                <p class="credentials-label">Email:</p>
                <p><span class="credentials-value">{email_login}</span></p>

                <p class="credentials-label">Senha temporaria:</p>
                <p><span class="credentials-value">{senha_temporaria}</span></p>
            </div>

            <p style="text-align: center;">
                <a href="{login_url}" class="button">
                    Acessar o Sistema
                </a>
            </p>

            <div class="warning">
                <strong>Importante:</strong>
                <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                    <li>Recomendamos que voce <strong>troque sua senha</strong> no primeiro acesso</li>
                    <li>Nao compartilhe suas credenciais com terceiros</li>
                </ul>
            </div>

            <p>Se tiver alguma duvida, entre em contato com o administrador da clinica.</p>

            <p>Atenciosamente,<br>
            <strong>Equipe Horario Inteligente</strong></p>
        </div>
        <div class="footer">
            <p>Este e um email automatico, por favor nao responda.</p>
            <p>&copy; 2026 Horario Inteligente. Todos os direitos reservados.</p>
        </div>
    </div>
</body>
</html>
            """

            text_body = f"""
Ola, {to_name}!

Suas credenciais de acesso ao sistema Horario Inteligente para a clinica {nome_clinica} estao prontas.

URL de acesso: {login_url}
Email: {email_login}
Senha temporaria: {senha_temporaria}

IMPORTANTE:
- Recomendamos que voce troque sua senha no primeiro acesso
- Nao compartilhe suas credenciais com terceiros

Atenciosamente,
Equipe Horario Inteligente
            """

            message = EmailMessage()
            message["Subject"] = "Suas credenciais de acesso - Horario Inteligente"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            message.set_content(text_body)
            message.add_alternative(html_body, subtype='html', cte='base64')

            if self.smtp_password:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)

                logger.info(f"Email de credenciais enviado para {to_email}")
                return True
            else:
                logger.warning(f"SMTP nao configurado. Credenciais para {to_email}: {email_login} / {senha_temporaria}")
                return True

        except Exception as e:
            logger.error(f"Erro ao enviar email de credenciais para {to_email}: {e}", exc_info=True)
            return False

    def send_ativacao_parceiro(
        self,
        to_email: str,
        to_name: str,
        token: str,
        percentual_comissao: float = 0,
        recorrencia_meses: int = None,
        base_url: str = "https://horariointeligente.com.br"
    ) -> bool:
        """
        Envia email com link de ativacao de conta para parceiro comercial.
        Template limpo (anti-spam). O token aqui e o codigo_ativacao curto.
        O link e valido por 7 dias.
        """
        try:
            activation_link = f"{base_url}/static/parceiro/ativar-conta.html?code={token}"

            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; }}
        .header {{ background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white !important; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
        .info-box {{ background: #ecfdf5; border-left: 4px solid #10B981; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .step {{ display: flex; align-items: flex-start; margin: 10px 0; }}
        .step-number {{ background: #10B981; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; margin-right: 10px; flex-shrink: 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Convite de Parceria</h1>
        </div>
        <div class="content">
            <p>Ola, <strong>{to_name}</strong>!</p>

            <p>Voce foi convidado(a) para ser Parceiro Comercial do <strong>Horario Inteligente</strong>.</p>

            <p>Acesse o Portal do Parceiro e configure sua conta:</p>

            <p style="text-align: center;">
                <a href="{activation_link}" class="button">
                    Acessar Portal do Parceiro
                </a>
            </p>

            <div class="info-box">
                <strong>Proximos passos:</strong>
                <div style="margin-top: 10px;">
                    <div class="step">
                        <span class="step-number">1</span>
                        <span>Crie sua senha de acesso</span>
                    </div>
                    <div class="step">
                        <span class="step-number">2</span>
                        <span>Aceite o Termo de Parceria</span>
                    </div>
                    <div class="step">
                        <span class="step-number">3</span>
                        <span>Acesse o Portal do Parceiro</span>
                    </div>
                </div>
            </div>

            <p>Ou copie e cole o link abaixo no navegador:</p>
            <p style="font-size: 12px; word-break: break-all; background: #f5f5f5; padding: 10px; border-radius: 5px;">
                {activation_link}
            </p>

            <p style="font-size: 13px; color: #666;">Este link e valido por 7 dias.</p>

            <p>Atenciosamente,<br>
            <strong>Equipe Horario Inteligente</strong></p>
        </div>
        <div class="footer">
            <p>Duvidas? Responda este email ou acesse horariointeligente.com.br</p>
            <p>&copy; 2026 Horario Inteligente. Todos os direitos reservados.</p>
        </div>
    </div>
</body>
</html>
            """

            text_body = f"""
Ola, {to_name}!

Voce foi convidado(a) para ser Parceiro Comercial do Horario Inteligente.

Acesse o Portal do Parceiro e configure sua conta:
{activation_link}

Proximos passos:
1. Crie sua senha de acesso
2. Aceite o Termo de Parceria
3. Acesse o Portal do Parceiro

Este link e valido por 7 dias.

Atenciosamente,
Equipe Horario Inteligente

Duvidas? Responda este email ou acesse horariointeligente.com.br
            """

            message = EmailMessage()
            message["Subject"] = "Convite de Parceria - Horario Inteligente"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Reply-To"] = "contato@horariointeligente.com.br"

            message.set_content(text_body)
            message.add_alternative(html_body, subtype='html', cte='base64')

            if self.smtp_password:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)

                logger.info(f"Email de ativacao parceiro enviado para {to_email}")
                return True
            else:
                logger.warning(f"SMTP nao configurado. Link de ativacao parceiro: {activation_link}")
                return True

        except Exception as e:
            logger.error(f"Erro ao enviar email de ativacao parceiro: {e}", exc_info=True)
            return False

    def send_ativacao_parceiro_com_senha(
        self,
        to_email: str,
        to_name: str,
        token: str,
        senha_provisoria: str = None,
        percentual_comissao: float = 0,
        recorrencia_meses: int = None,
        base_url: str = "https://horariointeligente.com.br"
    ) -> bool:
        """
        Envia email de ativacao para parceiro aprovado.
        Template limpo (anti-spam). senha_provisoria e mantido por compatibilidade mas nao e incluido.
        O token aqui e o codigo_ativacao curto (8 chars).
        """
        try:
            activation_link = f"{base_url}/static/parceiro/ativar-conta.html?code={token}"

            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; }}
        .header {{ background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white !important; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
        .info-box {{ background: #ecfdf5; border-left: 4px solid #10B981; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .step {{ display: flex; align-items: flex-start; margin: 10px 0; }}
        .step-number {{ background: #10B981; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; margin-right: 10px; flex-shrink: 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Bem-vindo a Parceria!</h1>
        </div>
        <div class="content">
            <p>Ola, <strong>{to_name}</strong>!</p>

            <p>Sua solicitacao de parceria com o <strong>Horario Inteligente</strong> foi aprovada.</p>

            <p>Acesse o Portal do Parceiro e configure sua conta:</p>

            <p style="text-align: center;">
                <a href="{activation_link}" class="button">
                    Acessar Portal do Parceiro
                </a>
            </p>

            <div class="info-box">
                <strong>Proximos passos:</strong>
                <div style="margin-top: 10px;">
                    <div class="step">
                        <span class="step-number">1</span>
                        <span>Crie sua senha de acesso</span>
                    </div>
                    <div class="step">
                        <span class="step-number">2</span>
                        <span>Aceite o Termo de Parceria</span>
                    </div>
                    <div class="step">
                        <span class="step-number">3</span>
                        <span>Acesse o Portal do Parceiro</span>
                    </div>
                </div>
            </div>

            <p>Ou copie e cole o link abaixo no navegador:</p>
            <p style="font-size: 12px; word-break: break-all; background: #f5f5f5; padding: 10px; border-radius: 5px;">
                {activation_link}
            </p>

            <p style="font-size: 13px; color: #666;">Este link e valido por 7 dias.</p>

            <p>Atenciosamente,<br>
            <strong>Equipe Horario Inteligente</strong></p>
        </div>
        <div class="footer">
            <p>Duvidas? Responda este email ou acesse horariointeligente.com.br</p>
            <p>&copy; 2026 Horario Inteligente. Todos os direitos reservados.</p>
        </div>
    </div>
</body>
</html>
            """

            text_body = f"""
Ola, {to_name}!

Sua solicitacao de parceria com o Horario Inteligente foi aprovada.

Acesse o Portal do Parceiro e configure sua conta:
{activation_link}

Proximos passos:
1. Crie sua senha de acesso
2. Aceite o Termo de Parceria
3. Acesse o Portal do Parceiro

Este link e valido por 7 dias.

Atenciosamente,
Equipe Horario Inteligente

Duvidas? Responda este email ou acesse horariointeligente.com.br
            """

            message = EmailMessage()
            message["Subject"] = "Bem-vindo a Parceria - Horario Inteligente"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Reply-To"] = "contato@horariointeligente.com.br"

            message.set_content(text_body)
            message.add_alternative(html_body, subtype='html', cte='base64')

            if self.smtp_password:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)

                logger.info(f"Email de ativacao parceiro enviado para {to_email}")
                return True
            else:
                logger.warning(f"SMTP nao configurado. Link de ativacao parceiro: {activation_link}")
                return True

        except Exception as e:
            logger.error(f"Erro ao enviar email de ativacao parceiro: {e}", exc_info=True)
            return False

    def send_convite_registro(
        self,
        to_email: str,
        to_name: str,
        url_convite: str,
        parceiro_nome: str = None
    ) -> bool:
        """
        Envia email com link de convite para registro de cliente.

        Args:
            to_email: Email do prospect
            to_name: Nome do prospect
            url_convite: URL completa do formulario de registro
            parceiro_nome: Nome do parceiro que enviou o convite (opcional)

        Returns:
            True se enviou com sucesso, False caso contrario
        """
        try:
            # Texto personalizado se houver parceiro
            convite_por = f"<strong>{parceiro_nome}</strong> convidou voce" if parceiro_nome else "Voce foi convidado(a)"
            convite_por_text = f"{parceiro_nome} convidou voce" if parceiro_nome else "Voce foi convidado(a)"

            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; }}
        .header {{ background: linear-gradient(135deg, #3B82F6 0%, #06B6D4 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #3B82F6 0%, #06B6D4 100%); color: white !important; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
        .info-box {{ background: #eff6ff; border-left: 4px solid #3B82F6; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .step {{ display: flex; align-items: flex-start; margin: 10px 0; }}
        .step-number {{ background: #3B82F6; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; margin-right: 10px; flex-shrink: 0; }}
        .partner-box {{ background: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px 15px; margin: 15px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Convite para Cadastro</h1>
        </div>
        <div class="content">
            <p>Ola, <strong>{to_name}</strong>!</p>

            {f'<div class="partner-box"><strong>{parceiro_nome}</strong> convidou voce para conhecer o Horario Inteligente!</div>' if parceiro_nome else ''}

            <p>{convite_por} para cadastrar sua clinica no <strong>Horario Inteligente</strong>, o sistema de agendamento automatizado mais humanizado do mercado!</p>

            <p>Clique no botao abaixo para preencher seus dados:</p>

            <p style="text-align: center;">
                <a href="{url_convite}" class="button">
                    Iniciar Cadastro
                </a>
            </p>

            <div class="info-box">
                <strong>Como funciona:</strong>
                <div style="margin-top: 10px;">
                    <div class="step">
                        <span class="step-number">1</span>
                        <span>Preencha os dados basicos da sua clinica</span>
                    </div>
                    <div class="step">
                        <span class="step-number">2</span>
                        <span>Nossa equipe ira configurar seu plano</span>
                    </div>
                    <div class="step">
                        <span class="step-number">3</span>
                        <span>Voce recebera um email para ativar sua conta</span>
                    </div>
                </div>
            </div>

            <p>Ou copie e cole o link abaixo no navegador:</p>
            <p style="font-size: 12px; word-break: break-all; background: #f5f5f5; padding: 10px; border-radius: 5px;">
                {url_convite}
            </p>

            <p style="font-size: 13px; color: #666;">Este link e valido por 30 dias.</p>

            <p>Atenciosamente,<br>
            <strong>Equipe Horario Inteligente</strong></p>
        </div>
        <div class="footer">
            <p>Duvidas? Responda este email ou acesse horariointeligente.com.br</p>
            <p>&copy; 2026 Horario Inteligente. Todos os direitos reservados.</p>
        </div>
    </div>
</body>
</html>
            """

            text_body = f"""
Ola, {to_name}!

{convite_por_text} para cadastrar sua clinica no Horario Inteligente.

Acesse o link abaixo para preencher seus dados:
{url_convite}

Como funciona:
1. Preencha os dados basicos da sua clinica
2. Nossa equipe ira configurar seu plano
3. Voce recebera um email para ativar sua conta

Este link e valido por 30 dias.

Atenciosamente,
Equipe Horario Inteligente
            """

            message = EmailMessage()
            message["Subject"] = "Convite para Cadastro - Horario Inteligente"
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Reply-To"] = "contato@horariointeligente.com.br"

            message.set_content(text_body)
            message.add_alternative(html_body, subtype='html', cte='base64')

            if self.smtp_password:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)

                logger.info(f"Email de convite de registro enviado para {to_email}")
                return True
            else:
                logger.warning(f"SMTP nao configurado. Convite para {to_email}: {url_convite}")
                return True

        except Exception as e:
            logger.error(f"Erro ao enviar email de convite de registro: {e}", exc_info=True)
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

            message = EmailMessage()
            message["Subject"] = f"Site - {nome}"
            message["From"] = f"Horario Inteligente <{self.from_email}>"
            message["To"] = self.contact_email

            message.set_content(text_body)

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
