#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Teste - Evolution API com Números Virtuais
Pro-Saúde SaaS
"""

import requests
import json
from datetime import datetime
import asyncio
import aiohttp

class EvolutionAPITester:
    def __init__(self, base_url="http://localhost:8080", api_key="your-api-key"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "apikey": api_key
        }
    
    def verificar_status_servidor(self):
        """Verifica se a Evolution API está funcionando"""
        try:
            response = requests.get(f"{self.base_url}/manager/status", headers=self.headers)
            print(f"🟢 Status Server: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Dados: {json.dumps(data, indent=2)}")
                return True
            return False
        except Exception as e:
            print(f"❌ Erro ao conectar Evolution API: {e}")
            return False
    
    def listar_instancias(self):
        """Lista todas as instâncias configuradas"""
        try:
            response = requests.get(f"{self.base_url}/instance/fetchInstances", headers=self.headers)
            if response.status_code == 200:
                instancias = response.json()
                print(f"📱 Instâncias encontradas: {len(instancias)}")
                for inst in instancias:
                    print(f"  - {inst.get('instance', {}).get('instanceName', 'N/A')}: {inst.get('instance', {}).get('status', 'N/A')}")
                return instancias
            else:
                print(f"❌ Erro ao listar instâncias: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Erro: {e}")
            return []
    
    def criar_instancia_virtual(self, nome_instancia="prosaude_virtual"):
        """Cria uma nova instância com número virtual"""
        try:
            payload = {
                "instanceName": nome_instancia,
                "integration": "WHATSAPP-BAILEYS",  # Para números virtuais/QR Code
                "webhook_wa_business": {
                    "url": f"http://145.223.95.35:8000/webhook/whatsapp/{nome_instancia}",
                    "enabled": True,
                    "events": [
                        "MESSAGE_RECEIVED",
                        "MESSAGE_SENT",
                        "CONNECTION_UPDATE"
                    ]
                }
            }
            
            response = requests.post(
                f"{self.base_url}/instance/create", 
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                print(f"✅ Instância criada: {nome_instancia}")
                print(f"📊 Dados: {json.dumps(data, indent=2)}")
                return data
            else:
                print(f"❌ Erro ao criar instância: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None
    
    def criar_instancia_cloud_api(self, nome_instancia="prosaude_cloud", phone_number_id="", access_token=""):
        """Cria instância com Cloud API (números oficiais)"""
        try:
            payload = {
                "instanceName": nome_instancia,
                "integration": "WHATSAPP-BUSINESS",  # Para Cloud API oficial
                "number": phone_number_id,
                "token": access_token,
                "webhook_wa_business": {
                    "url": f"http://145.223.95.35:8000/webhook/whatsapp/{nome_instancia}",
                    "enabled": True,
                    "events": [
                        "MESSAGE_RECEIVED",
                        "MESSAGE_SENT",
                        "CONNECTION_UPDATE"
                    ]
                }
            }
            
            response = requests.post(
                f"{self.base_url}/instance/create", 
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                print(f"✅ Instância Cloud API criada: {nome_instancia}")
                print(f"📊 Dados: {json.dumps(data, indent=2)}")
                return data
            else:
                print(f"❌ Erro ao criar instância Cloud API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None
    
    def obter_qr_code(self, nome_instancia):
        """Obtém QR Code para conectar WhatsApp"""
        try:
            response = requests.get(
                f"{self.base_url}/instance/connect/{nome_instancia}", 
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"📱 QR Code disponível para {nome_instancia}")
                
                # Se houver QR Code base64
                if 'qrcode' in data:
                    qr_b64 = data['qrcode']['base64']
                    print(f"🔲 QR Code (base64): {qr_b64[:50]}...")
                    
                    # Salvar QR como arquivo
                    import base64
                    with open(f"qr_{nome_instancia}.png", "wb") as f:
                        f.write(base64.b64decode(qr_b64.split(',')[1]))
                    print(f"💾 QR Code salvo como: qr_{nome_instancia}.png")
                
                return data
            else:
                print(f"❌ Erro ao obter QR: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None
    
    def verificar_conexao(self, nome_instancia):
        """Verifica status da conexão WhatsApp"""
        try:
            response = requests.get(
                f"{self.base_url}/instance/connectionState/{nome_instancia}", 
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"🔗 Status conexão {nome_instancia}: {data.get('instance', {}).get('state', 'N/A')}")
                return data
            else:
                print(f"❌ Erro ao verificar conexão: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None
    
    def enviar_mensagem_teste(self, nome_instancia, numero_destino, mensagem="🏥 Teste Pro-Saúde SaaS!"):
        """Envia mensagem de teste"""
        try:
            payload = {
                "number": numero_destino,
                "text": mensagem
            }
            
            response = requests.post(
                f"{self.base_url}/message/sendText/{nome_instancia}",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                print(f"✅ Mensagem enviada para {numero_destino}")
                print(f"📊 ID Mensagem: {data.get('key', {}).get('id', 'N/A')}")
                return data
            else:
                print(f"❌ Erro ao enviar mensagem: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None

def main():
    """Função principal para testar Evolution API"""
    print("🚀 Iniciando testes Evolution API - Pro-Saúde SaaS")
    print("=" * 60)
    
    # Configuração (ajustada para seu servidor)
    evolution = EvolutionAPITester(
        base_url="http://localhost:8082",  # Sua porta Evolution API
        api_key="evolution-api-prosaude-123"  # Sua API key
    )
    
    # Teste 1: Verificar se servidor está funcionando
    print("\n🔍 Teste 1: Verificando servidor Evolution API...")
    if not evolution.verificar_status_servidor():
        print("❌ Evolution API não está funcionando. Verifique a instalação.")
        return
    
    # Teste 2: Listar instâncias existentes
    print("\n📱 Teste 2: Listando instâncias existentes...")
    instancias = evolution.listar_instancias()
    
    # Teste 3: Criar nova instância (número virtual)
    print("\n🆕 Teste 3: Criando instância com número virtual...")
    nome_instancia = f"prosaude_teste_{int(datetime.now().timestamp())}"
    instancia_criada = evolution.criar_instancia_virtual(nome_instancia)
    
    if instancia_criada:
        # Teste 4: Obter QR Code para conectar
        print(f"\n📲 Teste 4: Obtendo QR Code para {nome_instancia}...")
        qr_data = evolution.obter_qr_code(nome_instancia)
        
        if qr_data:
            print(f"\n✅ QR Code gerado! Escaneie com seu WhatsApp para conectar.")
            print(f"⏳ Aguardando conexão... (scaneie o QR em até 30 segundos)")
            
            # Aguardar conexão
            import time
            for i in range(6):  # 30 segundos total
                time.sleep(5)
                status = evolution.verificar_conexao(nome_instancia)
                if status and status.get('instance', {}).get('state') == 'open':
                    print(f"🎉 WhatsApp conectado com sucesso!")
                    
                    # Teste 5: Enviar mensagem de teste
                    print(f"\n📤 Teste 5: Enviando mensagem de teste...")
                    # Substitua pelo seu número para teste
                    SEU_NUMERO = "5521992086879"  # Formato: 5521999999999
                    evolution.enviar_mensagem_teste(
                        nome_instancia, 
                        SEU_NUMERO, 
                        "🏥 Teste Pro-Saúde SaaS!\n\nSistema Evolution API funcionando perfeitamente! ✅"
                    )
                    break
                else:
                    print(f"⏳ Aguardando conexão... ({i+1}/6)")
    
    print("\n🏁 Testes concluídos!")
    print("=" * 60)

if __name__ == "__main__":
    main()
