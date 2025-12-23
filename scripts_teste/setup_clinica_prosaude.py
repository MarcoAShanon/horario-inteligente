"""
Script de Setup da Clínica Pro-Saúde
Sistema de agendamento médico SaaS
Desenvolvido por Marco
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
from app.models.cliente import Cliente
from app.models.medico import Medico
from app.models.convenio import Convenio
from app.models.configuracao import Configuracao


# Configuração do banco
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/agendamento_saas"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def setup_clinica_prosaude():
    """Setup completo da Clínica Pro-Saúde."""
    
    db = SessionLocal()
    
    try:
        print("🏥 Iniciando setup da Clínica Pro-Saúde...")
        
        # 1. Criar cliente (clínica)
        print("\n📋 Criando dados da clínica...")
        cliente = Cliente(
            nome="Clínica Pro-Saúde",
            email="contato@clinicaprosaude.com.br",
            plano="profissional",
            ativo=True,
            valor_mensalidade="150.00"
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        print(f"✅ Clínica criada com ID: {cliente.id}")
        
        # 2. Criar convênios
        print("\n💳 Criando convênios aceitos...")
        convenios_data = [
            {"nome": "Unimed", "codigo": "unimed", "ativo": True},
            {"nome": "Amil", "codigo": "amil", "ativo": True},
            {"nome": "Bradesco Saúde", "codigo": "bradesco", "ativo": True},
            {"nome": "Particular", "codigo": "particular", "ativo": True}
        ]
        
        convenios_criados = []
        for conv_data in convenios_data:
            convenio = Convenio(
                cliente_id=cliente.id,
                nome=conv_data["nome"],
                codigo=conv_data["codigo"],
                ativo=conv_data["ativo"]
            )
            db.add(convenio)
            convenios_criados.append(convenio)
        
        db.commit()
        print(f"✅ {len(convenios_criados)} convênios criados")
        
        # 3. Criar médicos
        print("\n👨‍⚕️ Criando médicos...")
        
        # Dra. Tânia Maria - Alergista
        dra_tania = Medico(
            cliente_id=cliente.id,
            nome="Dra. Tânia Maria",
            crm="CRM-RJ 12345",
            especialidade="Alergista",
            calendario_id="tania@clinicaprosaude.com.br",
            convenios_aceitos=["unimed", "amil", "particular"],
            horarios_atendimento={
                "segunda": {"inicio": "08:00", "fim": "17:00", "ativo": True},
                "terca": {"inicio": "08:00", "fim": "17:00", "ativo": True},
                "quarta": {"inicio": "08:00", "fim": "12:00", "ativo": True},
                "quinta": {"inicio": "14:00", "fim": "18:00", "ativo": True},
                "sexta": {"inicio": "08:00", "fim": "17:00", "ativo": True},
                "sabado": {"ativo": False},
                "domingo": {"ativo": False}
            },
            ativo=True
        )
        db.add(dra_tania)
        
        # Dr. Marco Aurélio - Cardiologista
        dr_marco = Medico(
            cliente_id=cliente.id,
            nome="Dr. Marco Aurélio",
            crm="CRM-RJ 67890",
            especialidade="Cardiologista",
            calendario_id="marco@clinicaprosaude.com.br",
            convenios_aceitos=["unimed", "bradesco", "particular"],
            horarios_atendimento={
                "segunda": {"inicio": "08:00", "fim": "18:00", "ativo": True},
                "terca": {"inicio": "08:00", "fim": "18:00", "ativo": True},
                "quarta": {"inicio": "08:00", "fim": "18:00", "ativo": True},
                "quinta": {"inicio": "08:00", "fim": "18:00", "ativo": True},
                "sexta": {"inicio": "08:00", "fim": "16:00", "ativo": True},
                "sabado": {"ativo": False},
                "domingo": {"ativo": False}
            },
            ativo=True
        )
        db.add(dr_marco)
        
        db.commit()
        db.refresh(dra_tania)
        db.refresh(dr_marco)
        
        print(f"✅ Dra. Tânia Maria criada - ID: {dra_tania.id}")
        print(f"✅ Dr. Marco Aurélio criado - ID: {dr_marco.id}")
        
        # 4. Resumo final
        print("\n" + "="*60)
        print("🎉 SETUP CONCLUÍDO COM SUCESSO!")
        print("="*60)
        print(f"📋 Clínica: {cliente.nome} (ID: {cliente.id})")
        print(f"👨‍⚕️ Médicos criados: 2")
        print(f"   - Dra. Tânia Maria (Alergista) - ID: {dra_tania.id}")
        print(f"   - Dr. Marco Aurélio (Cardiologista) - ID: {dr_marco.id}")
        print(f"💳 Convênios: {len(convenios_criados)}")
        print("="*60)
        
        return cliente.id
        
    except Exception as e:
        print(f"❌ Erro durante setup: {e}")
        db.rollback()
        return None
        
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Script de Setup - Clínica Pro-Saúde")
    print("=" * 50)
    
    cliente_id = setup_clinica_prosaude()
    
    if cliente_id:
        print(f"\n✅ Setup concluído! Cliente ID: {cliente_id}")
    else:
        print("\n❌ Falha no setup")
