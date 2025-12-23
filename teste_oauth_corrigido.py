import requests
import json
from datetime import datetime

print("=" * 50)
print("🚀 TESTE OAUTH GOOGLE CALENDAR")
print("=" * 50)

# Teste 1: Sistema rodando
try:
    r = requests.get("http://localhost:8000/api/v1/sistema/status")
    print(f"✅ Sistema: {r.status_code}")
except:
    print("❌ Sistema não responde")

# Teste 2: URL OAuth
try:
    r = requests.get("http://localhost:8000/api/v1/calendar/auth/1")
    if r.status_code == 200:
        data = r.json()
        url = data.get('url_autorizacao', '')
        print(f"✅ URL OAuth gerada")
        
        # Verificar parâmetros
        checks = {
            'include_granted_scopes=true': 'include_granted_scopes',
            'access_type=offline': 'access_type',
            'prompt=consent': 'prompt'
        }
        
        for param, name in checks.items():
            if param in url:
                print(f"  ✅ {name}: OK")
            else:
                print(f"  ❌ {name}: ERRO")
        
        print(f"\n🔗 URL PARA TESTE:")
        print(url)
        
        # Salvar URL
        with open('url_oauth_teste.txt', 'w') as f:
            f.write(url)
        print(f"\n📄 URL salva em: url_oauth_teste.txt")
        
    else:
        print(f"❌ Erro OAuth: {r.status_code}")
        print(r.text)
        
except Exception as e:
    print(f"❌ Erro: {e}")

print("=" * 50)
