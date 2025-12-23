#!/usr/bin/env python3
"""
Script para verificar configuração existente de IA no sistema
"""
import os
import sys
import json
import subprocess
from pathlib import Path

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def check_env_variables():
    """Verifica variáveis de ambiente de IA"""
    print_section("VARIÁVEIS DE AMBIENTE")
    
    ai_vars = [
        'ANTHROPIC_API_KEY',
        'OPENAI_API_KEY',
        'CLAUDE_API_KEY',
        'API_KEY',
        'AI_API_KEY'
    ]
    
    found = False
    for var in ai_vars:
        value = os.environ.get(var)
        if value:
            masked = value[:10] + "..." + value[-4:] if len(value) > 20 else value[:5] + "..."
            print(f"✅ {var}: {masked}")
            found = True
    
    if not found:
        print("❌ Nenhuma variável de API de IA encontrada no ambiente")
    
    return found

def check_env_files():
    """Verifica arquivos .env"""
    print_section("ARQUIVOS DE CONFIGURAÇÃO")
    
    paths_to_check = [
        '/root/sistema_agendamento/.env',
        '/root/sistema_agendamento/app/.env',
        '/root/.env',
        '/root/sistema_agendamento/config.py',
        '/root/sistema_agendamento/app/config.py',
        '/root/sistema_agendamento/settings.py'
    ]
    
    for path in paths_to_check:
        if os.path.exists(path):
            print(f"✅ Encontrado: {path}")
            
            # Verificar conteúdo relevante
            try:
                with open(path, 'r') as f:
                    content = f.read()
                    
                # Procurar por configurações de IA
                ai_keywords = ['ANTHROPIC', 'OPENAI', 'CLAUDE', 'AI_', 'api', 'key']
                for keyword in ai_keywords:
                    if keyword.lower() in content.lower():
                        lines = content.split('\n')
                        for line in lines:
                            if keyword.lower() in line.lower() and '=' in line:
                                # Mascarar valores sensíveis
                                key_val = line.split('=')
                                if len(key_val) >= 2:
                                    key = key_val[0].strip()
                                    val = key_val[1].strip().strip('"').strip("'")
                                    if len(val) > 10:
                                        masked = val[:8] + "..." + val[-4:]
                                    else:
                                        masked = val[:3] + "..."
                                    print(f"   → {key} = {masked}")
            except Exception as e:
                print(f"   ⚠️ Erro ao ler: {e}")
        else:
            print(f"❌ Não existe: {path}")

def check_existing_services():
    """Verifica serviços de IA existentes"""
    print_section("SERVIÇOS DE IA EXISTENTES")
    
    services_to_check = [
        '/root/sistema_agendamento/app/services/ai_service.py',
        '/root/sistema_agendamento/app/services/claude_service.py',
        '/root/sistema_agendamento/app/services/anthropic_service.py',
        '/root/sistema_agendamento/app/services/openai_service.py',
        '/root/sistema_agendamento/app/ai.py',
        '/root/sistema_agendamento/ai_handler.py'
    ]
    
    for service_path in services_to_check:
        if os.path.exists(service_path):
            print(f"✅ Encontrado: {service_path}")
            
            # Analisar imports e configurações
            try:
                with open(service_path, 'r') as f:
                    content = f.read()
                    
                # Verificar imports de IA
                if 'anthropic' in content.lower():
                    print("   → Usa Anthropic/Claude")
                    
                    # Procurar modelo usado
                    if 'claude-3-opus' in content:
                        print("   → Modelo: Claude 3 Opus")
                    elif 'claude-3-sonnet' in content:
                        print("   → Modelo: Claude 3 Sonnet")
                    elif 'claude-2' in content:
                        print("   → Modelo: Claude 2")
                    
                    # Procurar como pega a API key
                    if 'ANTHROPIC_API_KEY' in content:
                        print("   → Usa ANTHROPIC_API_KEY do ambiente")
                    elif 'getenv' in content or 'environ' in content:
                        print("   → Lê configuração do ambiente")
                        
                if 'openai' in content.lower():
                    print("   → Usa OpenAI/GPT")
                    
            except Exception as e:
                print(f"   ⚠️ Erro ao analisar: {e}")

def check_installed_packages():
    """Verifica pacotes de IA instalados"""
    print_section("PACOTES PYTHON INSTALADOS")
    
    try:
        result = subprocess.run(
            ['pip', 'list'], 
            capture_output=True, 
            text=True
        )
        
        ai_packages = ['anthropic', 'openai', 'langchain', 'transformers', 'claude']
        installed = []
        
        for line in result.stdout.split('\n'):
            for package in ai_packages:
                if package in line.lower():
                    installed.append(line.strip())
        
        if installed:
            print("✅ Pacotes de IA encontrados:")
            for pkg in installed:
                print(f"   → {pkg}")
        else:
            print("❌ Nenhum pacote de IA instalado")
            
    except Exception as e:
        print(f"⚠️ Erro ao verificar pacotes: {e}")

def check_docker_compose():
    """Verifica se há configuração no docker-compose"""
    print_section("DOCKER COMPOSE")
    
    compose_files = [
        '/root/sistema_agendamento/docker-compose.yml',
        '/root/sistema_agendamento/docker-compose.yaml',
        '/root/docker-compose.yml'
    ]
    
    for compose_file in compose_files:
        if os.path.exists(compose_file):
            print(f"✅ Encontrado: {compose_file}")
            
            try:
                with open(compose_file, 'r') as f:
                    content = f.read()
                    
                # Procurar por variáveis de ambiente de IA
                if 'ANTHROPIC' in content or 'OPENAI' in content:
                    print("   → Contém configuração de IA")
                    
                    # Mostrar linhas relevantes
                    for line in content.split('\n'):
                        if 'API_KEY' in line and ('ANTHROPIC' in line or 'AI' in line):
                            # Mascarar valor
                            if '=' in line or ':' in line:
                                print(f"   → {line.strip()[:50]}...")
                                
            except Exception as e:
                print(f"   ⚠️ Erro: {e}")

def check_systemd_service():
    """Verifica se há serviço systemd com configuração"""
    print_section("SERVIÇOS SYSTEMD")
    
    service_files = [
        '/etc/systemd/system/prosaude.service',
        '/etc/systemd/system/agendamento.service',
        '/lib/systemd/system/prosaude.service'
    ]
    
    for service_file in service_files:
        if os.path.exists(service_file):
            print(f"✅ Encontrado: {service_file}")
            
            try:
                with open(service_file, 'r') as f:
                    content = f.read()
                    
                if 'Environment=' in content:
                    print("   → Contém variáveis de ambiente")
                    
                    for line in content.split('\n'):
                        if 'Environment=' in line and 'API' in line:
                            print(f"   → {line.strip()[:60]}...")
                            
            except Exception as e:
                print(f"   ⚠️ Erro: {e}")

def find_api_keys_in_code():
    """Procura por API keys hardcoded no código"""
    print_section("BUSCA POR API KEYS NO CÓDIGO")
    
    base_path = Path('/root/sistema_agendamento')
    
    # Padrões de API key da Anthropic
    patterns = [
        'sk-ant-',
        'ANTHROPIC_API_KEY',
        'anthropic.Anthropic(',
        'claude',
        'api_key'
    ]
    
    found_files = []
    
    for pattern in patterns:
        # Buscar em arquivos Python
        for py_file in base_path.rglob('*.py'):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    if pattern in content or pattern.lower() in content.lower():
                        if str(py_file) not in found_files:
                            found_files.append(str(py_file))
                            print(f"✅ {py_file}")
                            
                            # Mostrar linhas relevantes
                            for i, line in enumerate(content.split('\n'), 1):
                                if pattern in line or pattern.lower() in line.lower():
                                    # Mascarar possíveis keys
                                    if 'sk-ant-' in line:
                                        line = line.replace(line[line.find('sk-ant-'):line.find('sk-ant-')+50], 'sk-ant-...[MASKED]...')
                                    print(f"   Linha {i}: {line.strip()[:80]}...")
                                    break
            except:
                pass

def test_anthropic_import():
    """Testa se Anthropic pode ser importado"""
    print_section("TESTE DE IMPORT")
    
    try:
        import anthropic
        print("✅ Módulo 'anthropic' pode ser importado")
        print(f"   Versão: {anthropic.__version__ if hasattr(anthropic, '__version__') else 'N/A'}")
        
        # Tentar criar cliente
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key:
            client = anthropic.Anthropic(api_key=api_key)
            print("✅ Cliente Anthropic criado com sucesso")
        else:
            print("⚠️ API key não encontrada no ambiente")
            
    except ImportError:
        print("❌ Módulo 'anthropic' não está instalado")
        print("   Execute: pip install anthropic")
    except Exception as e:
        print(f"⚠️ Erro ao importar: {e}")

def main():
    print("="*60)
    print("  VERIFICAÇÃO DE CONFIGURAÇÃO DE IA - SISTEMA PRO-SAÚDE")
    print("="*60)
    
    # Executar todas as verificações
    env_found = check_env_variables()
    check_env_files()
    check_existing_services()
    check_installed_packages()
    check_docker_compose()
    check_systemd_service()
    find_api_keys_in_code()
    test_anthropic_import()
    
    # Resumo
    print_section("RESUMO E RECOMENDAÇÕES")
    
    if env_found:
        print("✅ API Key encontrada no ambiente!")
        print("\nPara usar a IA existente:")
        print("1. Verifique qual arquivo de serviço já existe")
        print("2. Importe esse serviço no webhook")
        print("3. Use a função de IA já implementada")
    else:
        print("⚠️ API Key não está no ambiente atual")
        print("\nAções recomendadas:")
        print("1. Verificar arquivos .env encontrados")
        print("2. Exportar a variável: export ANTHROPIC_API_KEY='sua-key'")
        print("3. Ou carregar de arquivo: source .env")
    
    print("\n💡 Dica: Execute 'env | grep -i api' para ver todas as variáveis")

if __name__ == "__main__":
    main()
