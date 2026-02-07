"""
QR Code refresh endpoint for WhatsApp reconnection
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from datetime import datetime
import logging
import aiohttp

from app.api.webhooks.utils import (
    EVOLUTION_API_URL,
    EVOLUTION_API_KEY,
    verify_webhook_auth,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/whatsapp/refresh-qr")
async def refresh_qr_code(request: Request):
    """Gera novo QR Code para reconexão do WhatsApp - Retorna HTML"""
    if not verify_webhook_auth(request):
        raise HTTPException(status_code=401, detail="Nao autorizado")
    try:
        import base64

        url = f"{EVOLUTION_API_URL}/instance/connect/Clinica2024"
        headers = {"apikey": EVOLUTION_API_KEY}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    if 'base64' in data:
                        qr_base64 = data['base64']

                        # Salvar imagem PNG também
                        img_data = qr_base64.split(',')[1]
                        png_path = '/root/sistema_agendamento/static/whatsapp_qr.png'

                        with open(png_path, 'wb') as f:
                            f.write(base64.b64decode(img_data))

                        logger.info(f"✅ Novo QR Code gerado e salvo em {png_path}")

                        # Retornar HTML ao invés de JSON
                        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>QR Code - WhatsApp Horário Inteligente</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
            padding: 20px;
        }}
        .container {{
            text-align: center;
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            animation: fadeIn 0.5s ease-in;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(-20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        h1 {{
            color: #128C7E;
            margin-bottom: 10px;
            font-size: 28px;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 30px;
            font-size: 16px;
        }}
        .instructions {{
            margin: 20px 0;
            line-height: 1.8;
            text-align: left;
        }}
        .instructions ol {{
            padding-left: 20px;
        }}
        .instructions li {{
            margin: 10px 0;
            color: #333;
        }}
        .qr-container {{
            background: white;
            padding: 20px;
            border-radius: 15px;
            display: inline-block;
            margin: 20px 0;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        img {{
            max-width: 350px;
            width: 100%;
            height: auto;
            border-radius: 10px;
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
            color: #856404;
            text-align: left;
        }}
        .success {{
            background: #d4edda;
            border-left: 4px solid #28a745;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
            color: #155724;
            text-align: left;
        }}
        .refresh-btn {{
            background: #25D366;
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            margin-top: 20px;
            transition: all 0.3s;
            box-shadow: 0 4px 10px rgba(37, 211, 102, 0.3);
        }}
        .refresh-btn:hover {{
            background: #1fb855;
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(37, 211, 102, 0.4);
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 14px;
        }}
        .countdown {{
            font-size: 18px;
            font-weight: bold;
            color: #128C7E;
            margin: 15px 0;
        }}
        @media (max-width: 600px) {{
            .container {{ padding: 20px; }}
            h1 {{ font-size: 24px; }}
            img {{ max-width: 280px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 Conectar WhatsApp</h1>
        <p class="subtitle">Horário Inteligente - Sistema de Agendamento</p>

        <div class="success">
            <strong>✅ QR Code gerado com sucesso!</strong>
        </div>

        <div class="instructions">
            <p><strong>📋 Siga os passos:</strong></p>
            <ol>
                <li>Abra o <strong>WhatsApp</strong> no celular que responde aos clientes</li>
                <li>Toque em <strong>Mais opções (⋮)</strong> ou <strong>Configurações</strong></li>
                <li>Toque em <strong>Aparelhos conectados</strong></li>
                <li>Toque em <strong>Conectar um aparelho</strong></li>
                <li>Aponte a câmera para o QR Code abaixo:</li>
            </ol>
        </div>

        <div class="qr-container">
            <img src="{qr_base64}" alt="QR Code WhatsApp">
        </div>

        <div class="countdown" id="countdown">Atualizando em 25 segundos...</div>

        <div class="warning">
            <strong>⚠️ Importante:</strong><br>
            • Este QR Code expira rapidamente<br>
            • A página atualiza automaticamente a cada 25 segundos<br>
            • Se não conseguir escanear, aguarde a atualização automática
        </div>

        <button class="refresh-btn" onclick="location.reload()">🔄 Atualizar QR Code Agora</button>

        <div class="footer">
            Horário Inteligente - Agendamento com IA<br>
            Gerado em {datetime.now().strftime("%d/%m/%Y às %H:%M:%S")}
        </div>
    </div>

    <script>
        // Countdown timer
        let seconds = 25;
        const countdownEl = document.getElementById('countdown');

        setInterval(() => {{
            seconds--;
            if (seconds > 0) {{
                countdownEl.textContent = `Atualizando em ${{seconds}} segundos...`;
            }} else {{
                countdownEl.textContent = 'Atualizando...';
            }}
        }}, 1000);

        // Auto-refresh após 25 segundos
        setTimeout(() => {{
            location.reload();
        }}, 25000);
    </script>
</body>
</html>'''

                        return HTMLResponse(content=html_content)
                    else:
                        return HTMLResponse(content=f'''
                        <html>
                        <body style="font-family: Arial; text-align: center; padding: 50px;">
                            <h1 style="color: red;">❌ Erro</h1>
                            <p>QR Code não disponível na resposta da API</p>
                            <button onclick="location.reload()" style="padding: 10px 20px; font-size: 16px;">Tentar Novamente</button>
                        </body>
                        </html>
                        ''')
                else:
                    error = await response.text()
                    return HTMLResponse(content=f'''
                    <html>
                    <body style="font-family: Arial; text-align: center; padding: 50px;">
                        <h1 style="color: red;">❌ Erro na Evolution API</h1>
                        <p>{error}</p>
                        <button onclick="location.reload()" style="padding: 10px 20px; font-size: 16px;">Tentar Novamente</button>
                    </body>
                    </html>
                    ''')

    except Exception as e:
        logger.error(f"❌ Erro ao gerar QR Code: {e}")
        return HTMLResponse(content=f'''
        <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1 style="color: red;">❌ Erro</h1>
            <p>{str(e)}</p>
            <button onclick="location.reload()" style="padding: 10px 20px; font-size: 16px;">Tentar Novamente</button>
        </body>
        </html>
        ''')
