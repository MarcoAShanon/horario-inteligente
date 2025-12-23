# PLANO DE ADAPTAÇÃO - GESTÃO FINANCEIRA

**Sistema:** Horário Inteligente
**Data:** Dezembro/2024
**Objetivo:** Alinhar o sistema de gestão financeira com o Plano de Negócios v1.1

---

## ÍNDICE

1. [Visão Geral](#1-visão-geral)
2. [Fase 1: Correções Imediatas](#2-fase-1-correções-imediatas)
3. [Fase 2: Modelo de Receita](#3-fase-2-modelo-de-receita)
4. [Fase 3: Parceria Estratégica](#4-fase-3-parceria-estratégica)
5. [Fase 4: Gestão de Parceiros de Vendas](#5-fase-4-gestão-de-parceiros-de-vendas)
6. [Fase 5: Programas de Indicação e Parceiros](#6-fase-5-programas-de-indicação-e-parceiros)
7. [Fase 6: Tributação e Simuladores](#7-fase-6-tributação-e-simuladores)
8. [Checklist de Implementação](#8-checklist-de-implementação)

---

## 1. VISÃO GERAL

### 1.1 Situação Atual vs Plano de Negócios

| Área | Sistema Atual | Plano de Negócios |
|------|---------------|-------------------|
| Receita/cliente | R$ 200/médico | R$ 150 base + R$ 50/adicional |
| Custo IA | R$ 28/médico | R$ 0,50/cliente (Haiku) |
| Custos fixos | R$ 100/mês | R$ 564,56/mês |
| Taxa ativação | Não existe | R$ 150-200 |
| Parceria estratégica | Genérica | 40% margem, 80% dos 50 primeiros |
| Indicações | Não existe | Cashback R$ 75 |
| Níveis parceiros | Não existe | 4 níveis com bônus |
| Tributação | 6% fixo | Fator R dinâmico |

### 1.2 Dependências entre Fases

```
FASE 1 ──► FASE 2 ──► FASE 3
   │          │          │
   │          │          └──► FASE 5
   │          │
   │          └──► FASE 4
   │
   └──► (independente, pode iniciar imediatamente)
```

### 1.3 Estimativa de Esforço

| Fase | Descrição | Complexidade | Arquivos Afetados |
|------|-----------|--------------|-------------------|
| 1 | Correções Imediatas | Baixa | 2-3 |
| 2 | Modelo de Receita | Média | 5-7 |
| 3 | Parceria Estratégica | Média | 3-4 |
| 4 | Indicações e Parceiros | Alta | 6-8 |
| 5 | Tributação | Média | 2-3 |

---

## 2. FASE 1: CORREÇÕES IMEDIATAS

**Objetivo:** Corrigir valores hardcoded no sistema para refletir custos reais.
**Prioridade:** 🔴 ALTA
**Pré-requisitos:** Nenhum

### 2.1 Etapa 1.1: Corrigir Custo de IA

**Arquivo:** `/root/sistema_agendamento/app/api/financeiro.py`

**Situação Atual:**
```python
# Linha aproximada 180-200
"ia_claude": {
    "por_medico": 28,  # R$ 28/mês - INCORRETO
    "total": total_medicos * 28
}
```

**Correção:**
```python
"ia_claude": {
    "por_cliente": 0.50,  # R$ 0,50/mês (Claude Haiku)
    "total": total_clientes * 0.50
}
```

**Justificativa (do Plano de Negócios):**
- Claude Haiku: ~385 chamadas/mês por cliente
- Custo por chamada: ~R$ 0,0012
- Total: 385 × 0,0012 = R$ 0,50/cliente/mês

---

### 2.2 Etapa 1.2: Corrigir Custo de Infraestrutura

**Arquivo:** `/root/sistema_agendamento/app/api/financeiro.py`

**Situação Atual:**
```python
"infraestrutura": {
    "servidor_vps": 100,  # R$ 100/mês - DESATUALIZADO
    "whatsapp": 0,
    "email": 0,
    "total": 100
}
```

**Correção:**
```python
"infraestrutura": {
    "servidor_vps": 160.00,      # VPS Hostinger
    "dominio": 5.42,             # Domínio .com.br (R$ 65/ano)
    "email": 7.99,               # E-mail profissional
    "total": 173.41
}
```

---

### 2.3 Etapa 1.3: Adicionar Custos Variáveis por Cliente

**Arquivo:** `/root/sistema_agendamento/app/api/financeiro.py`

**Adicionar novo bloco:**
```python
"custos_variaveis_cliente": {
    "whatsapp_api": 4.00,        # ~80 lembretes utility
    "claude_haiku": 0.50,        # ~385 chamadas
    "gateway_pagamento": 5.99,   # PagSeguro 3.99%
    "simples_nacional": 9.00,    # 6% sobre R$ 150
    "total_por_cliente": 19.49
}
```

---

### 2.4 Etapa 1.4: Cadastrar Despesas Fixas Reais

**Ação:** Cadastrar via API ou diretamente no banco as despesas do Plano de Negócios.

**Despesas a cadastrar:**

| Descrição | Categoria | Valor | Recorrente | Dia |
|-----------|-----------|-------|------------|-----|
| ContaJá - Contabilidade | fixa | 224.17 | Sim | 10 |
| VPS Hostinger | fixa | 160.00 | Sim | 5 |
| Domínio .com.br | fixa | 5.42 | Sim | 1 |
| E-mail Profissional | fixa | 7.99 | Sim | 1 |
| INSS Pró-labore (11%) | fixa | 166.98 | Sim | 20 |

**Script SQL para inserção:**
```sql
INSERT INTO despesas (descricao, categoria, tipo, valor, recorrente, dia_recorrencia, periodicidade, status)
VALUES
('ContaJá - Contabilidade Completa', 'fixa', 'contabilidade', 224.17, true, 10, 'mensal', 'pendente'),
('VPS Hostinger - Servidor', 'fixa', 'infraestrutura', 160.00, true, 5, 'mensal', 'pendente'),
('Domínio horariointeligente.com.br', 'fixa', 'infraestrutura', 5.42, true, 1, 'mensal', 'pendente'),
('E-mail Profissional Hostinger', 'fixa', 'infraestrutura', 7.99, true, 1, 'mensal', 'pendente'),
('INSS Pró-labore (11% sobre 1 SM)', 'fixa', 'tributos_pessoais', 166.98, true, 20, 'mensal', 'pendente');
```

---

### 2.5 Etapa 1.5: Atualizar Dashboard de Custos

**Arquivo:** `/root/sistema_agendamento/static/financeiro/dashboard.html`

**Alterações na aba "Custos":**
1. Atualizar labels de R$ 28 para R$ 0,50
2. Adicionar seção de custos variáveis por cliente
3. Mostrar breakdown completo conforme Plano de Negócios

---

### 2.6 Validação da Fase 1

**Testes a realizar:**
- [ ] Dashboard mostra custo IA correto (R$ 0,50/cliente)
- [ ] Infraestrutura mostra R$ 173,41 total
- [ ] Despesas fixas cadastradas aparecem no sistema
- [ ] Cálculo de margem está correto
- [ ] Break-even calculado corretamente (5-7 clientes)

**Critério de Sucesso:**
```
Custos Fixos Mensais = R$ 564,56
Custo Variável/Cliente = R$ 19,49
Margem por Cliente (R$ 150) = R$ 130,51 (87%)
Break-even = 5 clientes (sem parceria)
```

---

## 3. FASE 2: MODELO DE RECEITA

**Objetivo:** Implementar estrutura de planos e preços conforme Plano de Negócios.
**Prioridade:** 🔴 ALTA
**Pré-requisitos:** Fase 1 concluída

### 3.1 Etapa 2.1: Criar Tabela de Planos

**Nova migração Alembic:** `h08_create_planos.py`

```python
"""
Criar tabela de planos de assinatura
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'planos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('codigo', sa.String(50), unique=True, nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.Text()),
        sa.Column('valor_mensal', sa.Numeric(10, 2), nullable=False),
        sa.Column('profissionais_inclusos', sa.Integer(), default=1),
        sa.Column('valor_profissional_adicional', sa.Numeric(10, 2), default=50.00),
        sa.Column('taxa_ativacao', sa.Numeric(10, 2), default=150.00),
        sa.Column('ativo', sa.Boolean(), default=True),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(), onupdate=sa.func.now())
    )

    # Inserir planos iniciais
    op.execute("""
        INSERT INTO planos (codigo, nome, descricao, valor_mensal, profissionais_inclusos, valor_profissional_adicional, taxa_ativacao)
        VALUES
        ('individual', 'Individual', 'Ideal para profissionais autônomos', 150.00, 1, 50.00, 150.00),
        ('clinica', 'Clínica', 'Para clínicas com múltiplos profissionais', 200.00, 2, 50.00, 200.00)
    """)

def downgrade():
    op.drop_table('planos')
```

---

### 3.2 Etapa 2.2: Criar Tabela de Assinaturas

**Nova migração Alembic:** `h09_create_assinaturas.py`

```python
"""
Criar tabela de assinaturas (vínculo cliente-plano)
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'assinaturas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id'), nullable=False),
        sa.Column('plano_id', sa.Integer(), sa.ForeignKey('planos.id'), nullable=False),

        # Valores da assinatura (podem ter desconto)
        sa.Column('valor_mensal', sa.Numeric(10, 2), nullable=False),
        sa.Column('valor_profissional_adicional', sa.Numeric(10, 2), default=50.00),
        sa.Column('profissionais_contratados', sa.Integer(), default=1),

        # Taxa de ativação
        sa.Column('taxa_ativacao', sa.Numeric(10, 2), default=150.00),
        sa.Column('taxa_ativacao_paga', sa.Boolean(), default=False),
        sa.Column('desconto_ativacao_percentual', sa.Numeric(5, 2), default=0),
        sa.Column('motivo_desconto_ativacao', sa.String(100)),

        # Serviços adicionais
        sa.Column('numero_virtual_salvy', sa.Boolean(), default=False),
        sa.Column('valor_numero_virtual', sa.Numeric(10, 2), default=40.00),

        # Datas
        sa.Column('data_inicio', sa.Date(), nullable=False),
        sa.Column('data_fim', sa.Date()),  # NULL = ativa
        sa.Column('dia_vencimento', sa.Integer(), default=10),

        # Status
        sa.Column('status', sa.String(20), default='ativa'),  # ativa, suspensa, cancelada
        sa.Column('motivo_cancelamento', sa.Text()),

        # Auditoria
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(), onupdate=sa.func.now())
    )

    op.create_index('ix_assinaturas_cliente', 'assinaturas', ['cliente_id'])
    op.create_index('ix_assinaturas_status', 'assinaturas', ['status'])

def downgrade():
    op.drop_table('assinaturas')
```

---

### 3.3 Etapa 2.3: Criar Modelo SQLAlchemy - Plano

**Novo arquivo:** `/root/sistema_agendamento/app/models/plano.py`

```python
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Plano(Base):
    __tablename__ = "planos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    valor_mensal = Column(Numeric(10, 2), nullable=False)
    profissionais_inclusos = Column(Integer, default=1)
    valor_profissional_adicional = Column(Numeric(10, 2), default=50.00)
    taxa_ativacao = Column(Numeric(10, 2), default=150.00)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, onupdate=func.now())

    # Relacionamentos
    assinaturas = relationship("Assinatura", back_populates="plano")

    def calcular_valor_total(self, profissionais_adicionais: int = 0) -> float:
        """Calcula valor total mensal com profissionais adicionais"""
        return float(self.valor_mensal) + (profissionais_adicionais * float(self.valor_profissional_adicional))
```

---

### 3.4 Etapa 2.4: Criar Modelo SQLAlchemy - Assinatura

**Novo arquivo:** `/root/sistema_agendamento/app/models/assinatura.py`

```python
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
from decimal import Decimal

class Assinatura(Base):
    __tablename__ = "assinaturas"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=False)
    plano_id = Column(Integer, ForeignKey('planos.id'), nullable=False)

    # Valores
    valor_mensal = Column(Numeric(10, 2), nullable=False)
    valor_profissional_adicional = Column(Numeric(10, 2), default=50.00)
    profissionais_contratados = Column(Integer, default=1)

    # Taxa de ativação
    taxa_ativacao = Column(Numeric(10, 2), default=150.00)
    taxa_ativacao_paga = Column(Boolean, default=False)
    desconto_ativacao_percentual = Column(Numeric(5, 2), default=0)
    motivo_desconto_ativacao = Column(String(100))

    # Serviços adicionais
    numero_virtual_salvy = Column(Boolean, default=False)
    valor_numero_virtual = Column(Numeric(10, 2), default=40.00)

    # Datas
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date)
    dia_vencimento = Column(Integer, default=10)

    # Status
    status = Column(String(20), default='ativa')
    motivo_cancelamento = Column(Text)

    # Auditoria
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, onupdate=func.now())

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="assinatura")
    plano = relationship("Plano", back_populates="assinaturas")

    @property
    def valor_total_mensal(self) -> Decimal:
        """Calcula valor total mensal incluindo adicionais"""
        base = self.valor_mensal

        # Profissionais além do incluso no plano
        if self.plano:
            adicionais = max(0, self.profissionais_contratados - self.plano.profissionais_inclusos)
            base += adicionais * self.valor_profissional_adicional

        # Número virtual
        if self.numero_virtual_salvy:
            base += self.valor_numero_virtual

        return base

    @property
    def taxa_ativacao_final(self) -> Decimal:
        """Calcula taxa de ativação com desconto aplicado"""
        desconto = self.taxa_ativacao * (self.desconto_ativacao_percentual / 100)
        return self.taxa_ativacao - desconto

    @property
    def is_ativa(self) -> bool:
        return self.status == 'ativa' and self.data_fim is None
```

---

### 3.5 Etapa 2.5: Atualizar Modelo Cliente

**Arquivo:** `/root/sistema_agendamento/app/models/cliente.py`

**Adicionar relacionamento:**
```python
# Adicionar no modelo Cliente
assinatura = relationship("Assinatura", back_populates="cliente", uselist=False)
```

---

### 3.6 Etapa 2.6: Criar API de Planos e Assinaturas

**Novo arquivo:** `/root/sistema_agendamento/app/api/planos.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.plano import Plano
from app.models.assinatura import Assinatura
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import date

router = APIRouter(prefix="/api/interno/planos", tags=["Planos"])

# ============ SCHEMAS ============

class PlanoResponse(BaseModel):
    id: int
    codigo: str
    nome: str
    descricao: Optional[str]
    valor_mensal: Decimal
    profissionais_inclusos: int
    valor_profissional_adicional: Decimal
    taxa_ativacao: Decimal
    ativo: bool

    class Config:
        from_attributes = True

class CriarAssinaturaRequest(BaseModel):
    cliente_id: int
    plano_codigo: str  # 'individual' ou 'clinica'
    profissionais_contratados: int = 1
    numero_virtual_salvy: bool = False
    desconto_ativacao_percentual: Decimal = 0
    motivo_desconto_ativacao: Optional[str] = None
    dia_vencimento: int = 10

class AssinaturaResponse(BaseModel):
    id: int
    cliente_id: int
    plano_codigo: str
    valor_mensal: Decimal
    valor_total_mensal: Decimal
    profissionais_contratados: int
    taxa_ativacao: Decimal
    taxa_ativacao_final: Decimal
    taxa_ativacao_paga: bool
    numero_virtual_salvy: bool
    status: str
    data_inicio: date

    class Config:
        from_attributes = True

# ============ ENDPOINTS ============

@router.get("/", response_model=list[PlanoResponse])
def listar_planos(db: Session = Depends(get_db)):
    """Lista todos os planos disponíveis"""
    return db.query(Plano).filter(Plano.ativo == True).all()

@router.get("/{codigo}", response_model=PlanoResponse)
def obter_plano(codigo: str, db: Session = Depends(get_db)):
    """Obtém detalhes de um plano específico"""
    plano = db.query(Plano).filter(Plano.codigo == codigo).first()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    return plano

@router.post("/assinaturas", response_model=AssinaturaResponse)
def criar_assinatura(dados: CriarAssinaturaRequest, db: Session = Depends(get_db)):
    """Cria uma nova assinatura para um cliente"""

    # Buscar plano
    plano = db.query(Plano).filter(Plano.codigo == dados.plano_codigo).first()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    # Verificar se cliente já tem assinatura ativa
    assinatura_existente = db.query(Assinatura).filter(
        Assinatura.cliente_id == dados.cliente_id,
        Assinatura.status == 'ativa'
    ).first()

    if assinatura_existente:
        raise HTTPException(status_code=400, detail="Cliente já possui assinatura ativa")

    # Criar assinatura
    assinatura = Assinatura(
        cliente_id=dados.cliente_id,
        plano_id=plano.id,
        valor_mensal=plano.valor_mensal,
        valor_profissional_adicional=plano.valor_profissional_adicional,
        profissionais_contratados=dados.profissionais_contratados,
        taxa_ativacao=plano.taxa_ativacao,
        desconto_ativacao_percentual=dados.desconto_ativacao_percentual,
        motivo_desconto_ativacao=dados.motivo_desconto_ativacao,
        numero_virtual_salvy=dados.numero_virtual_salvy,
        dia_vencimento=dados.dia_vencimento,
        data_inicio=date.today(),
        status='ativa'
    )

    db.add(assinatura)
    db.commit()
    db.refresh(assinatura)

    return assinatura

@router.get("/assinaturas/{cliente_id}", response_model=AssinaturaResponse)
def obter_assinatura(cliente_id: int, db: Session = Depends(get_db)):
    """Obtém a assinatura ativa de um cliente"""
    assinatura = db.query(Assinatura).filter(
        Assinatura.cliente_id == cliente_id,
        Assinatura.status == 'ativa'
    ).first()

    if not assinatura:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")

    return assinatura

@router.post("/assinaturas/{assinatura_id}/pagar-ativacao")
def registrar_pagamento_ativacao(assinatura_id: int, db: Session = Depends(get_db)):
    """Registra pagamento da taxa de ativação"""
    assinatura = db.query(Assinatura).filter(Assinatura.id == assinatura_id).first()

    if not assinatura:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")

    assinatura.taxa_ativacao_paga = True
    db.commit()

    return {"success": True, "message": "Taxa de ativação registrada como paga"}

@router.post("/assinaturas/{assinatura_id}/cancelar")
def cancelar_assinatura(assinatura_id: int, motivo: str, db: Session = Depends(get_db)):
    """Cancela uma assinatura"""
    assinatura = db.query(Assinatura).filter(Assinatura.id == assinatura_id).first()

    if not assinatura:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")

    assinatura.status = 'cancelada'
    assinatura.data_fim = date.today()
    assinatura.motivo_cancelamento = motivo
    db.commit()

    return {"success": True, "message": "Assinatura cancelada"}

@router.get("/simulacao/{plano_codigo}")
def simular_assinatura(
    plano_codigo: str,
    profissionais: int = 1,
    numero_virtual: bool = False,
    desconto_ativacao: float = 0,
    db: Session = Depends(get_db)
):
    """Simula valores de uma assinatura"""
    plano = db.query(Plano).filter(Plano.codigo == plano_codigo).first()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    # Calcular valores
    adicionais = max(0, profissionais - plano.profissionais_inclusos)
    valor_adicionais = adicionais * float(plano.valor_profissional_adicional)
    valor_numero_virtual = 40.00 if numero_virtual else 0

    valor_mensal_total = float(plano.valor_mensal) + valor_adicionais + valor_numero_virtual

    taxa_ativacao_original = float(plano.taxa_ativacao)
    taxa_ativacao_desconto = taxa_ativacao_original * (desconto_ativacao / 100)
    taxa_ativacao_final = taxa_ativacao_original - taxa_ativacao_desconto

    # Custos variáveis (do Plano de Negócios)
    custos_variaveis = 19.49  # WhatsApp + Claude + Gateway + Impostos
    margem = valor_mensal_total - custos_variaveis
    margem_percentual = (margem / valor_mensal_total) * 100

    return {
        "plano": {
            "codigo": plano.codigo,
            "nome": plano.nome,
            "valor_base": float(plano.valor_mensal),
            "profissionais_inclusos": plano.profissionais_inclusos
        },
        "configuracao": {
            "profissionais_contratados": profissionais,
            "profissionais_adicionais": adicionais,
            "numero_virtual": numero_virtual
        },
        "valores": {
            "valor_base": float(plano.valor_mensal),
            "valor_adicionais": valor_adicionais,
            "valor_numero_virtual": valor_numero_virtual,
            "valor_mensal_total": valor_mensal_total
        },
        "taxa_ativacao": {
            "valor_original": taxa_ativacao_original,
            "desconto_percentual": desconto_ativacao,
            "valor_desconto": taxa_ativacao_desconto,
            "valor_final": taxa_ativacao_final
        },
        "analise_financeira": {
            "custos_variaveis": custos_variaveis,
            "margem_bruta": round(margem, 2),
            "margem_percentual": round(margem_percentual, 1)
        }
    }
```

---

### 3.7 Etapa 2.7: Atualizar Cálculo de MRR

**Arquivo:** `/root/sistema_agendamento/app/api/financeiro.py`

**Alterar endpoint `/dashboard/metricas`:**

```python
# ANTES (baseado em médicos)
mrr = total_medicos * 200

# DEPOIS (baseado em assinaturas)
from app.models.assinatura import Assinatura

assinaturas_ativas = db.query(Assinatura).filter(
    Assinatura.status == 'ativa'
).all()

mrr = sum(a.valor_total_mensal for a in assinaturas_ativas)
```

---

### 3.8 Validação da Fase 2

**Testes a realizar:**
- [ ] Tabelas `planos` e `assinaturas` criadas no banco
- [ ] Endpoint `/api/interno/planos` retorna planos
- [ ] Simulador de assinatura funciona corretamente
- [ ] Criar assinatura para cliente existente
- [ ] Cálculo de MRR usa valores das assinaturas
- [ ] Taxa de ativação com desconto calculada corretamente

**Critério de Sucesso:**
```
Plano Individual: R$ 150 + R$ 50/adicional + R$ 40 (virtual opcional)
Plano Clínica: R$ 200 (2 inclusos) + R$ 50/adicional
Taxa ativação: R$ 150-200 com descontos configuráveis
```

---

## 4. FASE 3: PARCERIA ESTRATÉGICA

**Objetivo:** Implementar lógica da parceria de lançamento (40% margem, 80% dos 50 primeiros).
**Prioridade:** 🟡 MÉDIA
**Pré-requisitos:** Fase 2 concluída

### 4.1 Etapa 3.1: Configurar Parceiro Estratégico

**Ação:** Cadastrar parceiro especial no sistema.

**Via API `/api/interno/parceiros`:**
```json
{
    "nome": "Parceria Estratégica de Lançamento",
    "tipo_pessoa": "PF",
    "cpf_cnpj": "000.000.000-00",
    "email": "parceiro@estrategico.com",
    "tipo_comissao": "percentual_margem",
    "percentual_comissao": 40,
    "observacoes": "Parceria de lançamento: 40% da margem para 80% dos primeiros 50 clientes (40 clientes). Comissão recorrente enquanto cliente ativo.",
    "dados_bancarios": {
        "pix": "parceiro@email.com"
    }
}
```

---

### 4.2 Etapa 3.2: Adicionar Campo tipo_comissao no Modelo

**Arquivo:** `/root/sistema_agendamento/app/models/parceiro_comercial.py`

**Alterar enum de tipo_comissao:**
```python
# ANTES
tipo_comissao = Column(String(20))  # 'percentual', 'fixo'

# DEPOIS
tipo_comissao = Column(String(30))  # 'percentual', 'fixo', 'percentual_margem'
```

**Lógica:**
- `percentual`: % sobre receita bruta
- `fixo`: valor fixo por cliente
- `percentual_margem`: % sobre margem de contribuição (novo)

---

### 4.3 Etapa 3.3: Adicionar Campos de Controle na Tabela cliente_parceiro

**Nova migração:** `h10_parceria_estrategica.py`

```python
"""
Adicionar campos para parceria estratégica
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Adicionar campos em clientes_parceiros
    op.add_column('clientes_parceiros',
        sa.Column('tipo_parceria', sa.String(30), default='padrao')
    )  # 'padrao', 'lancamento'

    op.add_column('clientes_parceiros',
        sa.Column('ordem_cliente', sa.Integer())
    )  # Número sequencial do cliente (1-50 para parceria lançamento)

    op.add_column('clientes_parceiros',
        sa.Column('comissao_sobre', sa.String(20), default='receita')
    )  # 'receita', 'margem'

    # Adicionar campo no parceiro para marcar como estratégico
    op.add_column('parceiros_comerciais',
        sa.Column('parceria_lancamento', sa.Boolean(), default=False)
    )

    op.add_column('parceiros_comerciais',
        sa.Column('limite_clientes_lancamento', sa.Integer(), default=40)
    )

def downgrade():
    op.drop_column('clientes_parceiros', 'tipo_parceria')
    op.drop_column('clientes_parceiros', 'ordem_cliente')
    op.drop_column('clientes_parceiros', 'comissao_sobre')
    op.drop_column('parceiros_comerciais', 'parceria_lancamento')
    op.drop_column('parceiros_comerciais', 'limite_clientes_lancamento')
```

---

### 4.4 Etapa 3.4: Implementar Lógica de Cálculo de Comissão

**Arquivo:** `/root/sistema_agendamento/app/api/parceiros_comerciais.py`

**Adicionar função de cálculo:**

```python
def calcular_comissao_parceiro(
    parceiro: ParceiroComerical,
    cliente_parceiro: ClienteParceiro,
    receita_cliente: Decimal,
    custos_variaveis: Decimal = Decimal('19.49')
) -> dict:
    """
    Calcula comissão de um parceiro para um cliente específico.

    Regras de Parceria Estratégica de Lançamento:
    - 80% dos primeiros 50 clientes (40 clientes)
    - 40% da margem de contribuição
    - Recorrente enquanto cliente ativo
    """

    # Calcular margem
    margem = receita_cliente - custos_variaveis

    # Determinar base de cálculo
    if cliente_parceiro.comissao_sobre == 'margem':
        base_calculo = margem
    else:
        base_calculo = receita_cliente

    # Calcular comissão
    percentual = cliente_parceiro.percentual_comissao_override or parceiro.percentual_comissao

    if parceiro.tipo_comissao == 'fixo':
        comissao = parceiro.valor_fixo_comissao
    else:
        comissao = base_calculo * (percentual / 100)

    return {
        "receita_cliente": float(receita_cliente),
        "custos_variaveis": float(custos_variaveis),
        "margem": float(margem),
        "base_calculo": float(base_calculo),
        "tipo_comissao": parceiro.tipo_comissao,
        "percentual": float(percentual),
        "comissao": float(comissao),
        "margem_apos_comissao": float(margem - comissao),
        "tipo_parceria": cliente_parceiro.tipo_parceria,
        "ordem_cliente": cliente_parceiro.ordem_cliente
    }
```

---

### 4.5 Etapa 3.5: Endpoint de Relatório de Comissões

**Arquivo:** `/root/sistema_agendamento/app/api/parceiros_comerciais.py`

**Adicionar endpoint:**

```python
@router.get("/relatorio/comissoes-mensais")
def relatorio_comissoes_mensais(
    mes: int = None,
    ano: int = None,
    db: Session = Depends(get_db)
):
    """
    Gera relatório de comissões a pagar no mês.
    Separa parceria estratégica de outras parcerias.
    """
    from datetime import date
    from app.models.assinatura import Assinatura

    if not mes:
        mes = date.today().month
    if not ano:
        ano = date.today().year

    # Buscar clientes ativos com parceiros vinculados
    clientes_parceiros = db.query(ClienteParceiro).filter(
        ClienteParceiro.ativo == True
    ).all()

    comissoes_parceria_lancamento = []
    comissoes_outros = []

    CUSTOS_VARIAVEIS = Decimal('19.49')

    for cp in clientes_parceiros:
        # Buscar assinatura ativa do cliente
        assinatura = db.query(Assinatura).filter(
            Assinatura.cliente_id == cp.cliente_id,
            Assinatura.status == 'ativa'
        ).first()

        if not assinatura:
            continue

        receita = assinatura.valor_total_mensal
        calculo = calcular_comissao_parceiro(
            cp.parceiro, cp, receita, CUSTOS_VARIAVEIS
        )

        dados = {
            "parceiro_id": cp.parceiro_id,
            "parceiro_nome": cp.parceiro.nome,
            "cliente_id": cp.cliente_id,
            "cliente_nome": cp.cliente.nome,
            **calculo
        }

        if cp.tipo_parceria == 'lancamento':
            comissoes_parceria_lancamento.append(dados)
        else:
            comissoes_outros.append(dados)

    total_lancamento = sum(c['comissao'] for c in comissoes_parceria_lancamento)
    total_outros = sum(c['comissao'] for c in comissoes_outros)

    return {
        "periodo": {"mes": mes, "ano": ano},
        "parceria_lancamento": {
            "total_clientes": len(comissoes_parceria_lancamento),
            "limite_clientes": 40,
            "vagas_disponiveis": 40 - len(comissoes_parceria_lancamento),
            "comissao_total": total_lancamento,
            "detalhes": comissoes_parceria_lancamento
        },
        "outras_parcerias": {
            "total_clientes": len(comissoes_outros),
            "comissao_total": total_outros,
            "detalhes": comissoes_outros
        },
        "resumo": {
            "total_comissoes": total_lancamento + total_outros,
            "comissao_fixa_lancamento_50_clientes": 2088.00  # 40 clientes × R$ 52,20
        }
    }
```

---

### 4.6 Etapa 3.6: Vincular Cliente Automaticamente à Parceria

**Lógica ao criar novo cliente:**

```python
def vincular_cliente_parceria_lancamento(
    cliente_id: int,
    db: Session
):
    """
    Verifica se deve vincular novo cliente à parceria de lançamento.
    Regra: 80% dos primeiros 50 clientes (40 clientes)
    """
    from random import random

    # Buscar parceiro de lançamento
    parceiro = db.query(ParceiroComerical).filter(
        ParceiroComerical.parceria_lancamento == True,
        ParceiroComerical.ativo == True
    ).first()

    if not parceiro:
        return None

    # Contar clientes já vinculados à parceria de lançamento
    clientes_lancamento = db.query(ClienteParceiro).filter(
        ClienteParceiro.parceiro_id == parceiro.id,
        ClienteParceiro.tipo_parceria == 'lancamento',
        ClienteParceiro.ativo == True
    ).count()

    # Verificar limite (40 clientes)
    if clientes_lancamento >= parceiro.limite_clientes_lancamento:
        return None

    # Total de clientes do sistema
    total_clientes = db.query(Cliente).count()

    # Se ainda nos primeiros 50 clientes
    if total_clientes <= 50:
        # 80% de chance de ser parceria de lançamento
        if random() <= 0.80:
            vinculo = ClienteParceiro(
                cliente_id=cliente_id,
                parceiro_id=parceiro.id,
                percentual_comissao_override=40,  # 40% da margem
                tipo_parceria='lancamento',
                ordem_cliente=clientes_lancamento + 1,
                comissao_sobre='margem',
                ativo=True
            )
            db.add(vinculo)
            db.commit()
            return vinculo

    return None
```

---

### 4.7 Validação da Fase 3

**Testes a realizar:**
- [ ] Parceiro de lançamento cadastrado com flag `parceria_lancamento=True`
- [ ] Novos clientes vinculados automaticamente (80% chance)
- [ ] Limite de 40 clientes respeitado
- [ ] Comissão calculada sobre margem (não receita)
- [ ] Relatório mostra comissões separadas
- [ ] Após cliente 51, sem vínculo automático à parceria

**Critério de Sucesso:**
```
Cliente com receita R$ 150:
- Margem: R$ 150 - R$ 19,49 = R$ 130,51
- Comissão (40%): R$ 52,20
- Margem após comissão: R$ 78,31

Com 40 clientes: Comissão total = R$ 2.088/mês
```

---

## 5. FASE 4: GESTÃO DE PARCEIROS DE VENDAS

**Objetivo:** Implementar CRUD completo de parceiros, vínculo de clientes e controle de pagamentos de comissões.
**Prioridade:** 🟡 MÉDIA
**Pré-requisitos:** Fase 3 concluída
**Status:** 🔜 A IMPLEMENTAR

### 5.1 Contexto

A estrutura base de parceiros já existe (tabelas `parceiros_comerciais` e `clientes_parceiros`), porém falta:
- Interface administrativa para cadastro e gestão de parceiros
- Mecanismo para vincular qualquer cliente a qualquer parceiro (não só parceria de lançamento)
- Controle de comissões pagas vs pendentes
- Relatórios e extratos por parceiro

### 5.2 Etapa 4.1: CRUD Completo de Parceiros

**Endpoints a implementar:**

```python
# Arquivo: /root/sistema_agendamento/app/api/parceiros_comerciais.py

@router.post("/")
def criar_parceiro(dados: CriarParceiroRequest, db: Session = Depends(get_db)):
    """Cadastra novo parceiro comercial/de vendas"""
    pass

@router.get("/")
def listar_parceiros(
    ativo: bool = None,
    tipo_comissao: str = None,
    db: Session = Depends(get_db)
):
    """Lista todos os parceiros com filtros"""
    pass

@router.get("/{parceiro_id}")
def obter_parceiro(parceiro_id: int, db: Session = Depends(get_db)):
    """Obtém detalhes de um parceiro específico"""
    pass

@router.put("/{parceiro_id}")
def atualizar_parceiro(
    parceiro_id: int,
    dados: AtualizarParceiroRequest,
    db: Session = Depends(get_db)
):
    """Atualiza dados de um parceiro"""
    pass

@router.delete("/{parceiro_id}")
def desativar_parceiro(parceiro_id: int, db: Session = Depends(get_db)):
    """Desativa um parceiro (soft delete)"""
    pass
```

**Schema de Parceiro:**
```python
class CriarParceiroRequest(BaseModel):
    nome: str
    tipo_pessoa: str = "PJ"  # PF ou PJ
    cpf_cnpj: Optional[str]
    email: Optional[str]
    telefone: Optional[str]
    endereco: Optional[str]
    tipo_comissao: str = "percentual"  # percentual, fixo, percentual_margem
    percentual_comissao: Decimal = 0
    valor_fixo_comissao: Optional[Decimal]
    dados_bancarios: Optional[dict]
    observacoes: Optional[str]
```

---

### 5.3 Etapa 4.2: Vínculo Cliente-Parceiro (Genérico)

**Endpoint para vincular cliente a parceiro:**

```python
@router.post("/{parceiro_id}/vincular-cliente")
def vincular_cliente(
    parceiro_id: int,
    dados: VincularClienteRequest,
    db: Session = Depends(get_db)
):
    """
    Vincula um cliente a um parceiro comercial.
    Diferente da parceria de lançamento, este é um vínculo manual.
    """
    pass

class VincularClienteRequest(BaseModel):
    cliente_id: int
    data_vinculo: date = None  # Default: hoje
    percentual_comissao_override: Optional[Decimal]  # Sobrescreve % do parceiro
    comissao_sobre: str = "receita"  # receita ou margem
    observacoes: Optional[str]
```

**Endpoint para listar clientes de um parceiro:**

```python
@router.get("/{parceiro_id}/clientes")
def listar_clientes_parceiro(
    parceiro_id: int,
    ativo: bool = True,
    db: Session = Depends(get_db)
):
    """Lista todos os clientes vinculados a um parceiro"""
    pass
```

**Endpoint para desvincular cliente:**

```python
@router.post("/{parceiro_id}/desvincular-cliente/{cliente_id}")
def desvincular_cliente(
    parceiro_id: int,
    cliente_id: int,
    motivo: str = None,
    db: Session = Depends(get_db)
):
    """Desvincula um cliente de um parceiro (encerra comissionamento)"""
    pass
```

---

### 5.4 Etapa 4.3: Tabela de Pagamentos de Comissões

**Nova migração:** `h11_pagamentos_comissoes.py`

```python
"""
Criar tabela para registro de pagamentos de comissões
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'pagamentos_comissoes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('parceiro_id', sa.Integer(), sa.ForeignKey('parceiros_comerciais.id'), nullable=False),

        # Período de referência
        sa.Column('mes_referencia', sa.Integer(), nullable=False),
        sa.Column('ano_referencia', sa.Integer(), nullable=False),

        # Valores
        sa.Column('valor_bruto', sa.Numeric(10, 2), nullable=False),  # Total calculado
        sa.Column('deducoes', sa.Numeric(10, 2), default=0),  # Impostos retidos, etc
        sa.Column('valor_liquido', sa.Numeric(10, 2), nullable=False),  # Valor pago

        # Detalhamento
        sa.Column('qtd_clientes', sa.Integer(), default=0),
        sa.Column('detalhamento', sa.JSON()),  # Lista de clientes e valores

        # Status do pagamento
        sa.Column('status', sa.String(20), default='pendente'),
        # pendente, agendado, pago, cancelado

        # Dados do pagamento
        sa.Column('data_vencimento', sa.Date()),
        sa.Column('data_pagamento', sa.Date()),
        sa.Column('forma_pagamento', sa.String(50)),  # PIX, TED, etc
        sa.Column('comprovante_url', sa.String(500)),
        sa.Column('observacoes', sa.Text()),

        # Auditoria
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(), onupdate=sa.func.now()),
        sa.Column('pago_por', sa.Integer())  # user_id que registrou pagamento
    )

    op.create_index('ix_pagamentos_parceiro', 'pagamentos_comissoes', ['parceiro_id'])
    op.create_index('ix_pagamentos_periodo', 'pagamentos_comissoes', ['ano_referencia', 'mes_referencia'])
    op.create_index('ix_pagamentos_status', 'pagamentos_comissoes', ['status'])

def downgrade():
    op.drop_table('pagamentos_comissoes')
```

---

### 5.5 Etapa 4.4: Endpoints de Pagamento de Comissões

```python
@router.post("/{parceiro_id}/comissoes/gerar")
def gerar_comissao_mensal(
    parceiro_id: int,
    mes: int,
    ano: int,
    db: Session = Depends(get_db)
):
    """
    Gera registro de comissão mensal para um parceiro.
    Calcula valores baseado nos clientes ativos vinculados.
    """
    pass

@router.get("/{parceiro_id}/comissoes")
def listar_comissoes_parceiro(
    parceiro_id: int,
    status: str = None,
    ano: int = None,
    db: Session = Depends(get_db)
):
    """Lista histórico de comissões de um parceiro"""
    pass

@router.post("/comissoes/{comissao_id}/pagar")
def registrar_pagamento(
    comissao_id: int,
    dados: RegistrarPagamentoRequest,
    db: Session = Depends(get_db)
):
    """Registra pagamento de uma comissão"""
    pass

class RegistrarPagamentoRequest(BaseModel):
    data_pagamento: date
    forma_pagamento: str  # PIX, TED, etc
    comprovante_url: Optional[str]
    observacoes: Optional[str]
```

---

### 5.6 Etapa 4.5: Relatórios de Parceiros

```python
@router.get("/relatorios/resumo-geral")
def relatorio_resumo_parceiros(
    mes: int = None,
    ano: int = None,
    db: Session = Depends(get_db)
):
    """
    Relatório geral de todos os parceiros:
    - Total de parceiros ativos
    - Total de clientes vinculados
    - Comissões pendentes vs pagas
    - Ranking de parceiros por volume
    """
    pass

@router.get("/{parceiro_id}/extrato")
def extrato_parceiro(
    parceiro_id: int,
    data_inicio: date = None,
    data_fim: date = None,
    db: Session = Depends(get_db)
):
    """
    Extrato detalhado de um parceiro:
    - Clientes vinculados e data de vínculo
    - Comissões geradas por mês
    - Pagamentos realizados
    - Saldo pendente
    """
    pass
```

---

### 5.7 Etapa 4.6: Interface Administrativa (Frontend)

**Arquivos a criar:**

| Arquivo | Descrição |
|---------|-----------|
| `/static/admin/parceiros.html` | Lista e gestão de parceiros |
| `/static/admin/parceiro-detalhe.html` | Detalhe do parceiro + clientes |
| `/static/admin/comissoes.html` | Gestão de pagamentos de comissões |

**Funcionalidades da interface:**
- Listagem de parceiros com filtros (ativos, tipo comissão)
- Formulário de cadastro/edição de parceiro
- Vincular/desvincular clientes com busca
- Visualizar comissões pendentes e pagas
- Registrar pagamento com upload de comprovante

---

### 5.8 Validação da Fase 4

**Testes a realizar:**
- [ ] CRUD de parceiros funciona corretamente
- [ ] Vincular cliente a parceiro atualiza tabela clientes_parceiros
- [ ] Cálculo de comissão considera tipo (receita vs margem)
- [ ] Gerar comissão mensal cria registro correto
- [ ] Registrar pagamento atualiza status
- [ ] Relatórios mostram dados consolidados
- [ ] Interface admin permite todas as operações

**Critério de Sucesso:**
```
Fluxo completo:
1. Cadastrar parceiro "João Vendedor" com 10% comissão
2. Vincular cliente "Clínica ABC" ao parceiro
3. No fim do mês, gerar comissão (R$ 15,00 = 10% de R$ 150)
4. Registrar pagamento via PIX
5. Extrato mostra histórico completo
```

---

## 6. FASE 5: PROGRAMAS DE INDICAÇÃO E PARCEIROS

**Objetivo:** Implementar programa de cashback por indicação e níveis de parceiros.
**Prioridade:** 🟢 BAIXA
**Pré-requisitos:** Fase 2 concluída

### 6.1 Etapa 5.1: Criar Tabela de Indicações

**Nova migração:** `h12_programa_indicacoes.py`

```python
"""
Criar estrutura para programa de indicações/cashback
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'indicacoes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('indicador_id', sa.Integer(), sa.ForeignKey('clientes.id'), nullable=False),
        sa.Column('indicado_id', sa.Integer(), sa.ForeignKey('clientes.id'), nullable=False),

        # Código de indicação usado
        sa.Column('codigo_indicacao', sa.String(20)),

        # Status da indicação
        sa.Column('status', sa.String(20), default='pendente'),
        # pendente: indicado ainda não pagou 1ª mensalidade
        # ativa: gatilho atingido, créditos liberados
        # expirada: passou validade sem conversão
        # cancelada: indicado cancelou antes do gatilho

        # Benefícios
        sa.Column('credito_indicador', sa.Numeric(10, 2), default=75.00),
        sa.Column('desconto_indicado_ativacao', sa.Numeric(5, 2), default=50.00),  # percentual

        # Controle
        sa.Column('credito_utilizado', sa.Boolean(), default=False),
        sa.Column('data_utilizacao_credito', sa.Date()),

        # Validade
        sa.Column('data_indicacao', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('data_expiracao', sa.Date()),  # 6 meses após indicação
        sa.Column('data_ativacao', sa.DateTime()),  # quando indicado pagou 1ª mensalidade

        # Auditoria
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(), onupdate=sa.func.now())
    )

    op.create_index('ix_indicacoes_indicador', 'indicacoes', ['indicador_id'])
    op.create_index('ix_indicacoes_indicado', 'indicacoes', ['indicado_id'])
    op.create_index('ix_indicacoes_status', 'indicacoes', ['status'])

    # Adicionar campos no cliente para controle de indicações
    op.add_column('clientes',
        sa.Column('codigo_indicacao', sa.String(20), unique=True)
    )
    op.add_column('clientes',
        sa.Column('creditos_indicacao', sa.Numeric(10, 2), default=0)
    )
    op.add_column('clientes',
        sa.Column('indicado_por_id', sa.Integer(), sa.ForeignKey('clientes.id'))
    )
    op.add_column('clientes',
        sa.Column('elegivel_programa_indicacao', sa.Boolean(), default=True)
    )

def downgrade():
    op.drop_table('indicacoes')
    op.drop_column('clientes', 'codigo_indicacao')
    op.drop_column('clientes', 'creditos_indicacao')
    op.drop_column('clientes', 'indicado_por_id')
    op.drop_column('clientes', 'elegivel_programa_indicacao')
```

---

### 6.2 Etapa 5.2: Modelo de Indicação

**Novo arquivo:** `/root/sistema_agendamento/app/models/indicacao.py`

```python
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import date, timedelta

class Indicacao(Base):
    __tablename__ = "indicacoes"

    id = Column(Integer, primary_key=True, index=True)
    indicador_id = Column(Integer, ForeignKey('clientes.id'), nullable=False)
    indicado_id = Column(Integer, ForeignKey('clientes.id'), nullable=False)
    codigo_indicacao = Column(String(20))

    status = Column(String(20), default='pendente')

    credito_indicador = Column(Numeric(10, 2), default=75.00)
    desconto_indicado_ativacao = Column(Numeric(5, 2), default=50.00)

    credito_utilizado = Column(Boolean, default=False)
    data_utilizacao_credito = Column(Date)

    data_indicacao = Column(DateTime, server_default=func.now())
    data_expiracao = Column(Date)
    data_ativacao = Column(DateTime)

    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, onupdate=func.now())

    # Relacionamentos
    indicador = relationship("Cliente", foreign_keys=[indicador_id])
    indicado = relationship("Cliente", foreign_keys=[indicado_id])

    @classmethod
    def criar(cls, indicador_id: int, indicado_id: int, codigo: str = None):
        """Cria nova indicação com validade de 6 meses"""
        return cls(
            indicador_id=indicador_id,
            indicado_id=indicado_id,
            codigo_indicacao=codigo,
            data_expiracao=date.today() + timedelta(days=180)
        )

    def ativar(self):
        """Ativa indicação quando indicado paga 1ª mensalidade"""
        from datetime import datetime
        self.status = 'ativa'
        self.data_ativacao = datetime.now()

    @property
    def is_valida(self) -> bool:
        return (
            self.status in ['pendente', 'ativa'] and
            (self.data_expiracao is None or date.today() <= self.data_expiracao)
        )
```

---

### 6.3 Etapa 5.3: API de Indicações

**Novo arquivo:** `/root/sistema_agendamento/app/api/indicacoes.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.indicacao import Indicacao
from app.models.cliente import Cliente
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
import secrets

router = APIRouter(prefix="/api/interno/indicacoes", tags=["Indicações"])

# ============ SCHEMAS ============

class CriarIndicacaoRequest(BaseModel):
    indicador_id: int
    indicado_id: int

class IndicacaoResponse(BaseModel):
    id: int
    indicador_id: int
    indicador_nome: str
    indicado_id: int
    indicado_nome: str
    status: str
    credito_indicador: Decimal
    desconto_indicado_ativacao: Decimal
    credito_utilizado: bool
    is_valida: bool

    class Config:
        from_attributes = True

# ============ HELPERS ============

def gerar_codigo_indicacao() -> str:
    """Gera código único de indicação"""
    return f"HI{secrets.token_hex(4).upper()}"

# ============ ENDPOINTS ============

@router.post("/gerar-codigo/{cliente_id}")
def gerar_codigo_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Gera código de indicação para um cliente"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    if cliente.codigo_indicacao:
        return {"codigo": cliente.codigo_indicacao, "novo": False}

    # Verificar elegibilidade (primeiros 50 clientes)
    total_clientes = db.query(Cliente).count()
    if total_clientes > 50:
        cliente.elegivel_programa_indicacao = False
        db.commit()
        raise HTTPException(status_code=400, detail="Programa de indicação encerrado (limite de 50 clientes atingido)")

    codigo = gerar_codigo_indicacao()
    cliente.codigo_indicacao = codigo
    db.commit()

    return {"codigo": codigo, "novo": True}

@router.get("/validar-codigo/{codigo}")
def validar_codigo(codigo: str, db: Session = Depends(get_db)):
    """Valida código de indicação e retorna benefícios"""
    cliente = db.query(Cliente).filter(Cliente.codigo_indicacao == codigo).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Código de indicação inválido")

    if not cliente.elegivel_programa_indicacao:
        raise HTTPException(status_code=400, detail="Este código não está mais ativo")

    return {
        "valido": True,
        "indicador": cliente.nome,
        "beneficios": {
            "desconto_taxa_ativacao": "50%",
            "valor_original": 150.00,
            "valor_com_desconto": 75.00
        }
    }

@router.post("/registrar")
def registrar_indicacao(dados: CriarIndicacaoRequest, db: Session = Depends(get_db)):
    """Registra uma nova indicação"""

    # Validar indicador
    indicador = db.query(Cliente).filter(Cliente.id == dados.indicador_id).first()
    if not indicador:
        raise HTTPException(status_code=404, detail="Indicador não encontrado")

    if not indicador.elegivel_programa_indicacao:
        raise HTTPException(status_code=400, detail="Indicador não elegível ao programa")

    # Validar indicado
    indicado = db.query(Cliente).filter(Cliente.id == dados.indicado_id).first()
    if not indicado:
        raise HTTPException(status_code=404, detail="Indicado não encontrado")

    # Verificar se já existe indicação
    existente = db.query(Indicacao).filter(
        Indicacao.indicador_id == dados.indicador_id,
        Indicacao.indicado_id == dados.indicado_id
    ).first()

    if existente:
        raise HTTPException(status_code=400, detail="Indicação já registrada")

    # Criar indicação
    indicacao = Indicacao.criar(
        indicador_id=dados.indicador_id,
        indicado_id=dados.indicado_id,
        codigo=indicador.codigo_indicacao
    )

    # Atualizar indicado
    indicado.indicado_por_id = dados.indicador_id

    db.add(indicacao)
    db.commit()
    db.refresh(indicacao)

    return {"success": True, "indicacao_id": indicacao.id}

@router.post("/{indicacao_id}/ativar")
def ativar_indicacao(indicacao_id: int, db: Session = Depends(get_db)):
    """
    Ativa indicação quando indicado paga 1ª mensalidade.
    Libera crédito de R$ 75 para o indicador.
    """
    indicacao = db.query(Indicacao).filter(Indicacao.id == indicacao_id).first()
    if not indicacao:
        raise HTTPException(status_code=404, detail="Indicação não encontrada")

    if indicacao.status != 'pendente':
        raise HTTPException(status_code=400, detail=f"Indicação já está {indicacao.status}")

    # Ativar indicação
    indicacao.ativar()

    # Adicionar crédito ao indicador
    indicador = db.query(Cliente).filter(Cliente.id == indicacao.indicador_id).first()
    creditos_atuais = indicador.creditos_indicacao or Decimal('0')
    indicador.creditos_indicacao = creditos_atuais + indicacao.credito_indicador

    db.commit()

    return {
        "success": True,
        "message": f"Indicação ativada. R$ {indicacao.credito_indicador} creditados para {indicador.nome}",
        "creditos_totais_indicador": float(indicador.creditos_indicacao)
    }

@router.get("/cliente/{cliente_id}/creditos")
def consultar_creditos(cliente_id: int, db: Session = Depends(get_db)):
    """Consulta créditos de indicação de um cliente"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Buscar indicações ativas
    indicacoes = db.query(Indicacao).filter(
        Indicacao.indicador_id == cliente_id,
        Indicacao.status == 'ativa'
    ).all()

    return {
        "cliente_id": cliente_id,
        "cliente_nome": cliente.nome,
        "codigo_indicacao": cliente.codigo_indicacao,
        "elegivel_programa": cliente.elegivel_programa_indicacao,
        "creditos_disponiveis": float(cliente.creditos_indicacao or 0),
        "total_indicacoes_ativas": len(indicacoes),
        "valor_proximo_desconto": 75.00,
        "indicacoes_para_mensalidade_gratis": max(0, 2 - len(indicacoes)),
        "mensagem": self._mensagem_status(cliente, indicacoes)
    }

def _mensagem_status(cliente, indicacoes):
    creditos = float(cliente.creditos_indicacao or 0)
    if creditos >= 150:
        return "Você tem créditos para uma mensalidade grátis!"
    elif creditos >= 75:
        return "Mais 1 indicação e sua próxima mensalidade é grátis!"
    elif len(indicacoes) > 0:
        return f"Você já indicou {len(indicacoes)} cliente(s). Continue indicando!"
    else:
        return "Indique amigos e ganhe R$ 75 de desconto por indicação!"

@router.post("/cliente/{cliente_id}/usar-creditos")
def usar_creditos(cliente_id: int, valor: Decimal, db: Session = Depends(get_db)):
    """Usa créditos de indicação para abater mensalidade"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    creditos = cliente.creditos_indicacao or Decimal('0')

    if valor > creditos:
        raise HTTPException(status_code=400, detail=f"Créditos insuficientes. Disponível: R$ {creditos}")

    cliente.creditos_indicacao = creditos - valor
    db.commit()

    return {
        "success": True,
        "valor_utilizado": float(valor),
        "creditos_restantes": float(cliente.creditos_indicacao)
    }
```

---

### 6.4 Etapa 5.4: Adicionar Níveis de Parceiros

**Nova migração:** `h12_niveis_parceiros.py`

```python
"""
Adicionar sistema de níveis para parceiros comerciais
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Adicionar campos de nível e performance
    op.add_column('parceiros_comerciais',
        sa.Column('nivel', sa.String(20), default='indicador')
    )  # indicador, parceiro, premium, revendedor

    op.add_column('parceiros_comerciais',
        sa.Column('bonus_por_venda', sa.Numeric(10, 2), default=50.00)
    )

    op.add_column('parceiros_comerciais',
        sa.Column('percentual_recorrente', sa.Numeric(5, 2), default=0)
    )

    op.add_column('parceiros_comerciais',
        sa.Column('duracao_recorrencia_meses', sa.Integer(), default=0)
    )

    op.add_column('parceiros_comerciais',
        sa.Column('vendas_mes_atual', sa.Integer(), default=0)
    )

    op.add_column('parceiros_comerciais',
        sa.Column('total_vendas', sa.Integer(), default=0)
    )

    op.add_column('parceiros_comerciais',
        sa.Column('data_ultimo_upgrade', sa.Date())
    )

    # Tabela de histórico de comissões pagas
    op.create_table(
        'comissoes_pagas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('parceiro_id', sa.Integer(), sa.ForeignKey('parceiros_comerciais.id'), nullable=False),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id'), nullable=False),
        sa.Column('mes_referencia', sa.Integer(), nullable=False),
        sa.Column('ano_referencia', sa.Integer(), nullable=False),

        # Valores
        sa.Column('receita_cliente', sa.Numeric(10, 2)),
        sa.Column('tipo_comissao', sa.String(20)),  # bonus, recorrente
        sa.Column('valor_comissao', sa.Numeric(10, 2)),

        # Pagamento
        sa.Column('data_pagamento', sa.Date()),
        sa.Column('comprovante', sa.String(500)),
        sa.Column('observacoes', sa.Text()),

        # Auditoria
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now())
    )

    op.create_index('ix_comissoes_parceiro', 'comissoes_pagas', ['parceiro_id'])
    op.create_index('ix_comissoes_periodo', 'comissoes_pagas', ['ano_referencia', 'mes_referencia'])

def downgrade():
    op.drop_table('comissoes_pagas')
    op.drop_column('parceiros_comerciais', 'nivel')
    op.drop_column('parceiros_comerciais', 'bonus_por_venda')
    op.drop_column('parceiros_comerciais', 'percentual_recorrente')
    op.drop_column('parceiros_comerciais', 'duracao_recorrencia_meses')
    op.drop_column('parceiros_comerciais', 'vendas_mes_atual')
    op.drop_column('parceiros_comerciais', 'total_vendas')
    op.drop_column('parceiros_comerciais', 'data_ultimo_upgrade')
```

---

### 6.5 Etapa 5.5: Lógica de Níveis de Parceiros

**Adicionar ao modelo ParceiroComerical:**

```python
# Configuração de níveis
NIVEIS_PARCEIROS = {
    'indicador': {
        'requisito_vendas_mes': 0,
        'bonus_por_venda': 50.00,
        'percentual_recorrente': 0,
        'duracao_recorrencia': 0
    },
    'parceiro': {
        'requisito_vendas_mes': 3,
        'bonus_por_venda': 50.00,
        'percentual_recorrente': 10,
        'duracao_recorrencia': 12
    },
    'premium': {
        'requisito_vendas_mes': 10,
        'bonus_por_venda': 75.00,
        'percentual_recorrente': 15,
        'duracao_recorrencia': 12
    },
    'revendedor': {
        'requisito_vendas_mes': None,  # Contrato especial
        'bonus_por_venda': 0,
        'percentual_recorrente': 20,
        'duracao_recorrencia': None  # Enquanto ativo
    }
}

def verificar_upgrade_nivel(parceiro, db):
    """Verifica e aplica upgrade de nível baseado em performance"""
    vendas_mes = parceiro.vendas_mes_atual
    nivel_atual = parceiro.nivel

    if nivel_atual == 'revendedor':
        return  # Nível máximo por contrato

    novo_nivel = None

    if vendas_mes >= 10 and nivel_atual != 'premium':
        novo_nivel = 'premium'
    elif vendas_mes >= 3 and nivel_atual == 'indicador':
        novo_nivel = 'parceiro'

    if novo_nivel:
        config = NIVEIS_PARCEIROS[novo_nivel]
        parceiro.nivel = novo_nivel
        parceiro.bonus_por_venda = config['bonus_por_venda']
        parceiro.percentual_recorrente = config['percentual_recorrente']
        parceiro.duracao_recorrencia_meses = config['duracao_recorrencia']
        parceiro.data_ultimo_upgrade = date.today()
        db.commit()
```

---

### 6.6 Validação da Fase 5

**Testes a realizar:**
- [ ] Gerar código de indicação para cliente
- [ ] Validar código de indicação
- [ ] Registrar indicação entre clientes
- [ ] Ativar indicação após pagamento
- [ ] Créditos acumulados corretamente
- [ ] Usar créditos para abater mensalidade
- [ ] Upgrade automático de nível de parceiro
- [ ] Histórico de comissões pagas

**Critério de Sucesso:**
```
Indicação:
- Indicador ganha: R$ 75 crédito
- Indicado ganha: 50% desconto ativação
- 2 indicações = mensalidade grátis

Níveis Parceiros:
- Indicador: R$ 50/venda, sem recorrente
- Parceiro (3+ vendas): R$ 50 + 10% recorrente (12 meses)
- Premium (10+ vendas): R$ 75 + 15% recorrente (12 meses)
```

---

## 7. FASE 6: TRIBUTAÇÃO E SIMULADORES

**Objetivo:** Implementar calculadora de Fator R e alertas tributários.
**Prioridade:** 🟢 BAIXA
**Pré-requisitos:** Fase 1 e 2 concluídas

### 7.1 Etapa 6.1: Criar Endpoint de Simulação Tributária

**Adicionar em:** `/root/sistema_agendamento/app/api/financeiro.py`

```python
@router.get("/simulador/fator-r")
def simular_fator_r(
    receita_mensal: float,
    pro_labore: float = None,
    db: Session = Depends(get_db)
):
    """
    Simula Fator R e determina enquadramento tributário.

    Fator R = (Folha de Pagamento / Receita Bruta) × 100

    Se Fator R >= 28%: Anexo III (~6%)
    Se Fator R < 28%: Anexo V (~15,5%)
    """

    SALARIO_MINIMO = 1518.00
    ALIQUOTA_INSS = 0.11

    # Se não informou pró-labore, sugerir o mínimo para Anexo III
    if pro_labore is None:
        pro_labore_sugerido = receita_mensal * 0.28
        pro_labore = max(pro_labore_sugerido, SALARIO_MINIMO)

    # Garantir mínimo de 1 SM
    pro_labore = max(pro_labore, SALARIO_MINIMO)

    # Calcular Fator R
    fator_r = (pro_labore / receita_mensal) * 100 if receita_mensal > 0 else 0

    # Determinar anexo
    if fator_r >= 28:
        anexo = "III"
        aliquota_simples = 6.0
        descricao = "Tributação favorável"
    else:
        anexo = "V"
        aliquota_simples = 15.5
        descricao = "Tributação desfavorável"

    # Calcular INSS
    inss = pro_labore * ALIQUOTA_INSS

    # Calcular IRRF (base = pró-labore - INSS)
    base_irrf = pro_labore - inss
    irrf = calcular_irrf(base_irrf)

    # Calcular DAS (Simples Nacional)
    das = receita_mensal * (aliquota_simples / 100)

    # Totais
    total_tributos = inss + irrf + das
    liquido_socio = pro_labore - inss - irrf

    # Comparativo com outro anexo
    if anexo == "III":
        das_outro = receita_mensal * 0.155
        economia = das_outro - das
        mensagem_economia = f"Você está economizando R$ {economia:.2f}/mês com Anexo III"
    else:
        pro_labore_ideal = receita_mensal * 0.28
        mensagem_economia = f"Aumente pró-labore para R$ {pro_labore_ideal:.2f} para economizar ~9,5% em impostos"

    return {
        "entrada": {
            "receita_mensal": receita_mensal,
            "pro_labore": pro_labore
        },
        "fator_r": {
            "valor": round(fator_r, 2),
            "minimo_anexo_iii": 28.0,
            "status": "OK" if fator_r >= 28 else "ATENÇÃO"
        },
        "enquadramento": {
            "anexo": anexo,
            "aliquota": aliquota_simples,
            "descricao": descricao
        },
        "encargos": {
            "inss": {
                "aliquota": 11,
                "valor": round(inss, 2)
            },
            "irrf": {
                "base_calculo": round(base_irrf, 2),
                "valor": round(irrf, 2)
            },
            "das_simples": {
                "aliquota": aliquota_simples,
                "valor": round(das, 2)
            }
        },
        "resumo": {
            "total_tributos": round(total_tributos, 2),
            "percentual_carga": round((total_tributos / receita_mensal) * 100, 2),
            "liquido_socio": round(liquido_socio, 2)
        },
        "recomendacao": mensagem_economia,
        "pro_labore_sugerido": {
            "para_anexo_iii": round(receita_mensal * 0.28, 2),
            "minimo_legal": SALARIO_MINIMO
        }
    }


def calcular_irrf(base: float) -> float:
    """
    Calcula IRRF conforme tabela 2025.
    Base = Pró-labore - INSS
    """
    # Tabela IRRF 2025
    faixas = [
        (2428.80, 0, 0),
        (2826.65, 0.075, 182.16),
        (3751.05, 0.15, 394.16),
        (4664.68, 0.225, 675.49),
        (float('inf'), 0.275, 908.73)
    ]

    for limite, aliquota, deducao in faixas:
        if base <= limite:
            if aliquota == 0:
                return 0
            return (base * aliquota) - deducao

    return 0
```

---

### 7.2 Etapa 6.2: Endpoint de Alerta de Fator R

```python
@router.get("/alertas/fator-r")
def verificar_alerta_fator_r(db: Session = Depends(get_db)):
    """
    Verifica situação atual do Fator R e emite alertas.
    """
    from app.models.assinatura import Assinatura
    from app.models.despesa import Despesa

    # Calcular MRR atual
    assinaturas = db.query(Assinatura).filter(Assinatura.status == 'ativa').all()
    mrr = sum(float(a.valor_total_mensal) for a in assinaturas)

    # Buscar pró-labore atual (despesa fixa)
    pro_labore_despesa = db.query(Despesa).filter(
        Despesa.tipo.ilike('%pro-labore%') | Despesa.tipo.ilike('%pró-labore%'),
        Despesa.categoria == 'fixa'
    ).first()

    pro_labore_atual = float(pro_labore_despesa.valor) if pro_labore_despesa else 1518.00

    # Calcular Fator R
    fator_r = (pro_labore_atual / mrr) * 100 if mrr > 0 else 0

    # Determinar status
    if fator_r >= 28:
        status = "OK"
        nivel = "success"
        mensagem = f"Fator R em {fator_r:.1f}% - Anexo III mantido"
    elif fator_r >= 25:
        status = "ATENÇÃO"
        nivel = "warning"
        pro_labore_ideal = mrr * 0.28
        aumento = pro_labore_ideal - pro_labore_atual
        mensagem = f"Fator R em {fator_r:.1f}% - Aumente pró-labore em R$ {aumento:.2f} para manter Anexo III"
    else:
        status = "CRÍTICO"
        nivel = "error"
        pro_labore_ideal = mrr * 0.28
        aumento = pro_labore_ideal - pro_labore_atual
        mensagem = f"Fator R em {fator_r:.1f}% - URGENTE: Aumente pró-labore em R$ {aumento:.2f} ou pagará ~9,5% a mais de impostos"

    return {
        "mrr_atual": mrr,
        "pro_labore_atual": pro_labore_atual,
        "fator_r": round(fator_r, 2),
        "status": status,
        "nivel": nivel,
        "mensagem": mensagem,
        "pro_labore_ideal": round(mrr * 0.28, 2),
        "economia_mensal_anexo_iii": round(mrr * 0.095, 2)  # Diferença entre 15,5% e 6%
    }
```

---

### 7.3 Etapa 6.3: Adicionar Alerta no Dashboard

**Arquivo:** `/root/sistema_agendamento/static/financeiro/dashboard.html`

**Adicionar componente de alerta:**

```html
<!-- Alerta Fator R (adicionar no topo do dashboard) -->
<div id="alerta-fator-r" class="hidden mb-4 p-4 rounded-lg border">
    <div class="flex items-center gap-3">
        <i id="alerta-icone" class="fas fa-exclamation-triangle text-xl"></i>
        <div>
            <p id="alerta-titulo" class="font-semibold"></p>
            <p id="alerta-mensagem" class="text-sm opacity-80"></p>
        </div>
    </div>
</div>

<script>
async function verificarAlertaFatorR() {
    try {
        const response = await fetch('/api/financeiro/alertas/fator-r', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();

        const alerta = document.getElementById('alerta-fator-r');
        const icone = document.getElementById('alerta-icone');
        const titulo = document.getElementById('alerta-titulo');
        const mensagem = document.getElementById('alerta-mensagem');

        if (data.status !== 'OK') {
            alerta.classList.remove('hidden');

            if (data.nivel === 'warning') {
                alerta.className = 'mb-4 p-4 rounded-lg border border-yellow-500 bg-yellow-50 text-yellow-800';
                icone.className = 'fas fa-exclamation-triangle text-xl text-yellow-500';
            } else {
                alerta.className = 'mb-4 p-4 rounded-lg border border-red-500 bg-red-50 text-red-800';
                icone.className = 'fas fa-exclamation-circle text-xl text-red-500';
            }

            titulo.textContent = `Fator R: ${data.fator_r}%`;
            mensagem.textContent = data.mensagem;
        }
    } catch (error) {
        console.error('Erro ao verificar Fator R:', error);
    }
}

// Verificar ao carregar
verificarAlertaFatorR();
</script>
```

---

### 7.4 Validação da Fase 6

**Testes a realizar:**
- [ ] Simulador calcula Fator R corretamente
- [ ] IRRF calculado conforme tabela 2025
- [ ] Sugestão de pró-labore ideal para Anexo III
- [ ] Alerta aparece quando Fator R < 28%
- [ ] Comparativo de economia entre anexos

**Critério de Sucesso:**
```
Com 50 clientes (R$ 7.500/mês):
- Pró-labore mínimo Anexo III: R$ 2.100 (28%)
- INSS: R$ 231
- IRRF: R$ 0 (isento até R$ 2.428,80)
- DAS Anexo III: R$ 450 (6%)
- Total tributos: R$ 681

Se Anexo V (pró-labore R$ 1.518):
- INSS: R$ 167
- DAS Anexo V: R$ 1.162,50 (15,5%)
- Total: R$ 1.329,50
- Economia Anexo III: R$ 648,50/mês
```

---

## 8. CHECKLIST DE IMPLEMENTAÇÃO

### Fase 1: Correções Imediatas
- [ ] 1.1 Corrigir custo IA (R$ 28 → R$ 0,50)
- [ ] 1.2 Corrigir custo infraestrutura (R$ 100 → R$ 173,41)
- [ ] 1.3 Adicionar custos variáveis por cliente
- [ ] 1.4 Cadastrar despesas fixas reais
- [ ] 1.5 Atualizar dashboard de custos
- [ ] 1.6 Validar cálculos

### Fase 2: Modelo de Receita
- [ ] 2.1 Criar migração tabela planos
- [ ] 2.2 Criar migração tabela assinaturas
- [ ] 2.3 Criar modelo Plano
- [ ] 2.4 Criar modelo Assinatura
- [ ] 2.5 Atualizar modelo Cliente
- [ ] 2.6 Criar API de planos/assinaturas
- [ ] 2.7 Atualizar cálculo de MRR
- [ ] 2.8 Validar simulador

### Fase 3: Parceria Estratégica ✅ CONCLUÍDA
- [x] 3.1 Configurar parceiro estratégico
- [x] 3.2 Adicionar tipo_comissao 'percentual_margem'
- [x] 3.3 Criar migração campos parceria (h10_parceria_estrategica)
- [x] 3.4 Implementar cálculo de comissão sobre margem
- [x] 3.5 Criar endpoint de relatório
- [x] 3.6 Implementar vínculo automático
- [x] 3.7 Validar limite de 40 clientes

### Fase 4: Gestão de Parceiros de Vendas 🔜 A IMPLEMENTAR
- [ ] 4.1 CRUD completo de parceiros (criar, listar, editar, desativar)
- [ ] 4.2 Endpoint vincular cliente a parceiro (genérico)
- [ ] 4.3 Endpoint listar clientes de um parceiro
- [ ] 4.4 Endpoint desvincular cliente
- [ ] 4.5 Criar migração tabela pagamentos_comissoes (h11)
- [ ] 4.6 Endpoint gerar comissão mensal
- [ ] 4.7 Endpoint registrar pagamento de comissão
- [ ] 4.8 Relatório resumo geral de parceiros
- [ ] 4.9 Extrato detalhado por parceiro
- [ ] 4.10 Interface administrativa (frontend)

### Fase 5: Indicações e Parceiros
- [ ] 5.1 Criar migração programa indicações (h12)
- [ ] 5.2 Criar modelo Indicacao
- [ ] 5.3 Criar API de indicações
- [ ] 5.4 Criar migração níveis parceiros (h13)
- [ ] 5.5 Implementar lógica de níveis
- [ ] 5.6 Criar histórico de comissões
- [ ] 5.7 Validar créditos e upgrades

### Fase 6: Tributação ✅ CONCLUÍDA
- [x] 6.1 Criar simulador Fator R
- [x] 6.2 Implementar cálculo IRRF (tabela 2025)
- [x] 6.3 Criar endpoint de alerta Fator R
- [x] 6.4 Adicionar alerta no dashboard
- [x] 6.5 Validar cálculos tributários
- [x] 6.6 Simulador de cenários de crescimento (bônus)

---

## ANEXOS

### A. Tabela de Planos (Referência)

| Plano | Mensal | Profissionais | Adicional | Ativação |
|-------|--------|---------------|-----------|----------|
| Individual | R$ 150 | 1 | R$ 50 | R$ 150 |
| Clínica | R$ 200 | 2 | R$ 50 | R$ 200 |
| Número Virtual | +R$ 40 | - | - | - |

### B. Custos Variáveis (Referência)

| Item | Valor | Cálculo |
|------|-------|---------|
| WhatsApp API | R$ 4,00 | ~80 lembretes × R$ 0,05 |
| Claude Haiku | R$ 0,50 | ~385 chamadas × R$ 0,0012 |
| PagSeguro | R$ 5,99 | 3,99% × R$ 150 |
| Simples Nacional | R$ 9,00 | 6% × R$ 150 |
| **TOTAL** | **R$ 19,49** | |

### C. Custos Fixos (Referência)

| Item | Valor |
|------|-------|
| ContaJá | R$ 224,17 |
| VPS Hostinger | R$ 160,00 |
| Domínio | R$ 5,42 |
| E-mail | R$ 7,99 |
| INSS Pró-labore | R$ 166,98 |
| **TOTAL** | **R$ 564,56** |

### D. Níveis de Parceiros (Referência)

| Nível | Requisito | Bônus | Recorrente | Duração |
|-------|-----------|-------|------------|---------|
| Indicador | Cadastro | R$ 50 | - | - |
| Parceiro | 3+ vendas/mês | R$ 50 | 10% | 12 meses |
| Premium | 10+ vendas/mês | R$ 75 | 15% | 12 meses |
| Revendedor | Contrato | - | 20% | Enquanto ativo |

---

**Documento criado em:** Dezembro/2024
**Versão:** 1.0
**Autor:** Sistema de Planejamento
