# Atores do Sistema - Horário Inteligente

**Versão:** 2.0
**Data:** 21/12/2025
**Status:** Implementado

---

## Sumário

1. [Visão Geral](#visão-geral)
2. [Hierarquia de Acesso](#hierarquia-de-acesso)
3. [Administrador](#1-administrador)
4. [Financeiro](#2-financeiro)
5. [Suporte](#3-suporte)
6. [Cliente](#4-cliente)
7. [Ambiente Demo](#5-ambiente-demo)
8. [Matriz de Permissões](#matriz-de-permissões)
9. [Considerações de Segurança](#considerações-de-segurança)
10. [URLs de Acesso](#urls-de-acesso)

---

## Visão Geral

O sistema Horário Inteligente é uma plataforma SaaS multi-tenant para agendamento médico com integração de IA. Os atores são divididos em três grupos principais:

### Atores Internos (Equipe Horário Inteligente)
- **Administrador** - Gestão completa do sistema
- **Financeiro** - Gestão de pagamentos e comissões
- **Suporte** - Manutenção e atendimento técnico

### Atores Externos (Clientes)
- **Profissional de Saúde** - Usuário principal do cliente
- **Secretária** - Usuário auxiliar com acesso multi-profissional

### Ambiente Demonstração
- **Usuário Demo** - Acesso ao sandbox para teste de funcionalidades

---

## Hierarquia de Acesso

```
┌─────────────────────────────────────────────────────────────────┐
│                      ADMINISTRADOR                               │
│                    (Acesso Total)                                │
│              admin.horariointeligente.com.br                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    ┌──────────────┐                    ┌──────────────┐         │
│    │  FINANCEIRO  │                    │   SUPORTE    │         │
│    │  (Restrito)  │                    │  (Restrito)  │         │
│    └──────────────┘                    └──────────────┘         │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                       CLIENTES                                   │
│              [subdominio].horariointeligente.com.br              │
│                                                                  │
│    ┌─────────────────────────────────────────────────┐          │
│    │              PROFISSIONAL DE SAÚDE              │          │
│    │         (Administrador do Cliente)              │          │
│    ├─────────────────────────────────────────────────┤          │
│    │                  SECRETÁRIA                     │          │
│    │            (Usuário Operacional)                │          │
│    └─────────────────────────────────────────────────┘          │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                    AMBIENTE DEMO                                 │
│              demo.horariointeligente.com.br                      │
│                                                                  │
│    ┌─────────────────────────────────────────────────┐          │
│    │              USUÁRIO DEMONSTRAÇÃO               │          │
│    │     (Acesso sandbox com dados simulados)        │          │
│    └─────────────────────────────────────────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Administrador

### Descrição
Usuário com acesso irrestrito a todas as funcionalidades do sistema. Responsável pela gestão estratégica, monitoramento global e tomada de decisões críticas.

### Perfil de Acesso
- **Nível:** Super Admin
- **Escopo:** Global (todos os clientes)
- **Ambiente:** admin.horariointeligente.com.br

### Funcionalidades

#### 1.1 Dashboard Administrativo
| Funcionalidade | Descrição |
|----------------|-----------|
| Status do Sistema | Indicadores de saúde: API, banco de dados, Redis, WhatsApp |
| Clientes Ativos | Total de clientes ativos vs. inativos, crescimento mensal |
| Métricas de Uso | Agendamentos realizados, taxa de confirmação, no-shows |
| Alertas Críticos | Notificações de falhas, limites atingidos, anomalias |

#### 1.2 Gestão de Clientes
| Funcionalidade | Descrição |
|----------------|-----------|
| CRUD de Clientes | Criar, visualizar, editar e desativar clientes |
| Configuração de Planos | Definir limites e recursos por plano |
| Migração de Planos | Upgrade/downgrade de clientes |
| Gestão de Subdomínios | Configurar e validar subdomínios personalizados |
| Branding | Personalização visual por cliente (logo, cores) |

#### 1.3 Monitoramento de Mensagens
| Tipo de Mensagem | Descrição | Métricas |
|------------------|-----------|----------|
| Serviço | Agendamentos, confirmações, cancelamentos | Volume/dia, taxa de sucesso |
| Alerta | Lembretes 24h, 3h, 1h | Enviados vs. entregues |
| Marketing | Campanhas promocionais (futuro) | Abertura, conversão |
| Suporte | Mensagens de erro, ajuda | Tempo de resposta |
| IA | Interações com Claude | Tokens consumidos, custo |

#### 1.4 Gestão de Usuários Internos
| Funcionalidade | Descrição |
|----------------|-----------|
| Criar Usuários | Administrador, Financeiro, Suporte |
| Atribuir Permissões | Perfis de acesso granulares |
| Auditoria | Log de ações por usuário |
| Desativar Usuários | Revogar acesso mantendo histórico |

#### 1.5 Configurações Globais
| Funcionalidade | Descrição |
|----------------|-----------|
| Parâmetros do Sistema | Timeouts, limites, configurações padrão |
| Integrações | API keys, webhooks, credenciais externas |
| Templates de Mensagem | Modelos padrão para lembretes e notificações |
| Backup e Restore | Agendamento de backups, restauração |

#### 1.6 Relatórios Estratégicos
| Relatório | Descrição |
|-----------|-----------|
| MRR (Monthly Recurring Revenue) | Receita recorrente mensal |
| Churn Rate | Taxa de cancelamento de clientes |
| LTV (Lifetime Value) | Valor médio do cliente |
| CAC (Customer Acquisition Cost) | Custo de aquisição |
| NPS (Net Promoter Score) | Satisfação do cliente (futuro) |

### Permissões Especiais
- Acesso ao banco de dados em modo leitura
- Execução de scripts de manutenção
- Alteração de configurações críticas
- Impersonação de qualquer usuário (para suporte)

---

## 2. Financeiro

### Descrição
Usuário responsável pela gestão financeira do negócio, incluindo faturamento, cobrança, comissões de parceiros e controle de custos operacionais.

### Perfil de Acesso
- **Nível:** Restrito (área financeira)
- **Escopo:** Dados financeiros de todos os clientes
- **Ambiente:** admin.horariointeligente.com.br/financeiro

### Funcionalidades

#### 2.1 Dashboard Financeiro
| Funcionalidade | Descrição |
|----------------|-----------|
| Receita Total | Faturamento bruto e líquido |
| Inadimplência | Clientes com pagamento pendente |
| Projeção | Estimativa de receita futura |
| Custos | Despesas operacionais consolidadas |

#### 2.2 Gestão de Cobrança
| Funcionalidade | Descrição |
|----------------|-----------|
| Faturas | Emissão, consulta e reenvio de faturas |
| Pagamentos | Registro de pagamentos recebidos |
| Inadimplentes | Lista de clientes em atraso |
| Régua de Cobrança | Automação de lembretes de pagamento |
| Suspensão | Bloqueio por inadimplência (com aviso prévio) |

#### 2.3 Integração PagSeguro (a implementar)
| Funcionalidade | Descrição |
|----------------|-----------|
| Checkout | Link de pagamento para novos clientes |
| Assinaturas | Cobrança recorrente automática |
| Notificações | Webhook de status de pagamento |
| Estorno | Processamento de cancelamentos |
| Relatórios | Conciliação bancária |

#### 2.4 Gestão de Parceiros Comerciais
| Funcionalidade | Descrição |
|----------------|-----------|
| Cadastro de Parceiros | Nome, CNPJ, dados bancários, % comissão |
| Vínculo Cliente-Parceiro | Associar clientes aos parceiros indicadores |
| Cálculo de Comissão | Automático baseado em mensalidades pagas |
| Relatório de Comissões | Extrato por parceiro e período |
| Pagamento de Comissões | Registro de repasses realizados |

**Exemplo de estrutura de parceiro:**
```
Parceiro: Dr. João Silva
CNPJ: 12.345.678/0001-90
Comissão: 20% sobre mensalidade
Clientes vinculados: 5
Comissão acumulada (mês): R$ 450,00
Status: Ativo
```

#### 2.5 Controle de Custos Operacionais
| Categoria | Exemplos | Frequência |
|-----------|----------|------------|
| Infraestrutura | Servidor VPS, domínio, SSL | Mensal/Anual |
| APIs | Anthropic (Claude), OpenAI (Whisper/TTS) | Mensal (uso) |
| Comunicação | WhatsApp Business API, SMTP | Mensal |
| Serviços | Contabilidade, jurídico | Mensal |
| Marketing | Google Ads, redes sociais | Variável |
| Pessoal | Salários, freelancers | Mensal |

**Campos por lançamento:**
- Data do lançamento
- Categoria
- Descrição
- Valor
- Fornecedor
- Comprovante (upload)
- Recorrência (único/mensal/anual)
- Centro de custo

#### 2.6 Relatórios Financeiros
| Relatório | Descrição |
|-----------|-----------|
| DRE Simplificado | Receitas - Custos = Resultado |
| Fluxo de Caixa | Entradas e saídas por período |
| Aging | Análise de vencimentos (a receber) |
| Comissões a Pagar | Débitos com parceiros |
| Custo por Cliente | Rateio de custos operacionais |
| Margem por Plano | Rentabilidade de cada plano |

### Permissões Especiais
- Visualizar dados financeiros de todos os clientes
- Exportar relatórios em Excel/PDF
- Configurar preços e planos
- Gerenciar parceiros comerciais

### Restrições
- Não pode alterar dados cadastrais de clientes
- Não pode acessar configurações técnicas
- Não pode ver conteúdo de mensagens/agendamentos

---

## 3. Suporte

### Descrição
Usuário técnico responsável por manter o sistema operacional, resolver problemas reportados por clientes e garantir a qualidade do serviço.

### Perfil de Acesso
- **Nível:** Restrito (área técnica)
- **Escopo:** Status e configurações operacionais
- **Ambiente:** admin.horariointeligente.com.br/suporte

### Funcionalidades

#### 3.1 Dashboard de Monitoramento
| Componente | Métricas | Alerta |
|------------|----------|--------|
| API FastAPI | Uptime, latência, erros/min | > 1% erros |
| PostgreSQL | Conexões ativas, queries lentas | > 80% conexões |
| Redis | Memória, hit rate | > 90% memória |
| WhatsApp (Evolution) | Status por instância, fila de mensagens | Desconectado |
| Anthropic API | Rate limits, tokens/hora | > 80% limite |

#### 3.2 Status por Cliente
| Funcionalidade | Descrição |
|----------------|-----------|
| Visão Individual | Status de cada componente por cliente |
| WhatsApp | Conexão da instância, QR Code para reconexão |
| Últimas Mensagens | Log das últimas interações (sem conteúdo sensível) |
| Agendamentos | Volume e status recentes |
| Erros | Log de erros específicos do cliente |

#### 3.3 Ferramentas de Diagnóstico
| Ferramenta | Descrição |
|------------|-----------|
| Health Check | Verificação completa de todos os serviços |
| Log Viewer | Visualização de logs filtrados por cliente/período |
| Teste de Webhook | Simular recebimento de mensagem |
| Teste de Notificação | Enviar mensagem de teste |
| Reconexão WhatsApp | Forçar reconexão de instância |

#### 3.4 Gestão de Tickets (futuro)
| Funcionalidade | Descrição |
|----------------|-----------|
| Abertura | Registro de chamados por cliente |
| Categorização | Bug, dúvida, melhoria, urgência |
| Atribuição | Designar responsável |
| SLA | Tempo de resposta por prioridade |
| Histórico | Registro de todas as interações |

#### 3.5 Base de Conhecimento
| Tipo | Descrição |
|------|-----------|
| FAQ Interno | Problemas comuns e soluções |
| Runbooks | Procedimentos para incidentes |
| Documentação Técnica | Arquitetura, APIs, integrações |
| Changelog | Histórico de atualizações |

#### 3.6 Ações de Manutenção
| Ação | Descrição | Requer Aprovação |
|------|-----------|------------------|
| Reiniciar Instância WhatsApp | Reconectar cliente específico | Não |
| Limpar Cache | Redis flush por cliente | Não |
| Reprocessar Lembretes | Forçar envio de lembretes pendentes | Não |
| Bloquear Cliente | Suspensão temporária (problema crítico) | Sim (Admin) |
| Rollback de Dados | Restaurar dados de backup | Sim (Admin) |

### Permissões Especiais
- Acesso a logs do sistema
- Execução de comandos de diagnóstico
- Reconexão de instâncias WhatsApp
- Visualização de métricas em tempo real

### Restrições
- Não pode alterar dados cadastrais de clientes
- Não pode ver dados financeiros
- Não pode excluir dados permanentemente
- Acesso limitado ao conteúdo de mensagens (apenas metadados)

---

## 4. Cliente

### Descrição
Usuários finais que contratam o serviço Horário Inteligente. Divididos em dois perfis: Profissional de Saúde (administrador do cliente) e Secretária (operacional).

### Perfil de Acesso
- **Nível:** Cliente (isolado por tenant)
- **Escopo:** Apenas dados do próprio cliente
- **Ambiente:** [subdominio].horariointeligente.com.br

### 4.1 Profissional de Saúde

#### Descrição
Médico, dentista, psicólogo ou outro profissional de saúde que é o titular da conta. Pode atuar individualmente ou em consultório compartilhado.

#### Funcionalidades

##### Dashboard Pessoal
| Funcionalidade | Descrição |
|----------------|-----------|
| Agenda do Dia | Compromissos de hoje |
| Próximos Pacientes | Lista dos próximos atendimentos |
| Métricas | Consultas realizadas, confirmações, faltas |
| Notificações | Alertas de novos agendamentos, cancelamentos |

##### Gestão de Agenda
| Funcionalidade | Descrição |
|----------------|-----------|
| Visualizar Agenda | Calendário mensal/semanal/diário |
| Configurar Horários | Dias e horários de atendimento |
| Bloquear Horários | Férias, feriados, compromissos pessoais |
| Intervalos | Tempo entre consultas, horário de almoço |
| Tipos de Consulta | Duração, valor, convênios aceitos |

##### Gestão de Pacientes
| Funcionalidade | Descrição |
|----------------|-----------|
| Cadastro | Dados pessoais, contato, convênio |
| Histórico | Consultas anteriores, observações |
| Busca | Por nome, telefone, CPF |
| Exportação | Lista de pacientes (Excel/CSV) |

##### Gestão de Agendamentos
| Funcionalidade | Descrição |
|----------------|-----------|
| Novo Agendamento | Via sistema ou WhatsApp |
| Confirmar/Cancelar | Alterar status do agendamento |
| Reagendar | Mover para novo horário |
| Marcar Falta | Registrar no-show |
| Observações | Notas sobre a consulta |

##### Configurações Pessoais
| Funcionalidade | Descrição |
|----------------|-----------|
| Perfil | Foto, nome, especialidade, CRM |
| Notificações | Preferências de alertas (WhatsApp/Email) |
| Mensagens Personalizadas | Templates de confirmação, lembrete |
| Senha | Alteração de senha |

##### Funcionalidades por Plano

| Funcionalidade | Básico | Profissional | Enterprise |
|----------------|--------|--------------|------------|
| Agendamentos/mês | 100 | 500 | Ilimitado |
| Profissionais | 1 | 3 | Ilimitado |
| WhatsApp IA | Básico | Completo | Personalizado |
| Lembretes automáticos | 24h | 24h, 3h, 1h | Customizável |
| Relatórios | Básico | Avançado | Personalizado |
| Suporte | Email | Email + Chat | Prioritário |
| Backup de dados | Semanal | Diário | Tempo real |
| API de integração | Não | Limitada | Completa |

### 4.2 Secretária

#### Descrição
Usuário operacional que gerencia a agenda de um ou mais profissionais. Comum em consultórios compartilhados e clínicas.

#### Funcionalidades

##### Dashboard Operacional
| Funcionalidade | Descrição |
|----------------|-----------|
| Visão Multi-Profissional | Agenda de todos os profissionais vinculados |
| Agenda do Dia | Consolidado de todos os compromissos |
| Alertas | Conflitos de horário, pendências |

##### Gestão de Agenda
| Funcionalidade | Descrição |
|----------------|-----------|
| Visualizar | Agenda de qualquer profissional vinculado |
| Agendar | Criar compromissos para qualquer profissional |
| Cancelar/Reagendar | Alterar agendamentos |
| Confirmar | Validar presença do paciente |

##### Gestão de Pacientes
| Funcionalidade | Descrição |
|----------------|-----------|
| Cadastro | Mesmo do profissional |
| Busca | Acesso a todos os pacientes do cliente |

##### Diferenças em relação ao Profissional
| Aspecto | Profissional | Secretária |
|---------|--------------|------------|
| Visualização de agenda | Apenas própria | Todos os profissionais |
| Configuração de horários | Sim | Não |
| Relatórios financeiros | Sim | Não |
| Gestão de usuários | Sim | Não |
| Personalização de mensagens | Sim | Não |

### Restrições do Cliente
- Acesso apenas aos próprios dados (isolamento multi-tenant)
- Funcionalidades limitadas ao plano contratado
- Não pode acessar dados de outros clientes
- Não pode alterar configurações do sistema

---

## 5. Ambiente Demo

### Descrição
Ambiente sandbox para potenciais clientes testarem o sistema antes da contratação. Contém dados simulados e é resetado automaticamente todas as noites.

### Perfil de Acesso
- **Nível:** Demonstração (isolado)
- **Escopo:** Dados fictícios pré-carregados
- **Ambiente:** demo.horariointeligente.com.br

### Características

#### 5.1 Dados Pré-Carregados
| Tipo | Quantidade | Descrição |
|------|------------|-----------|
| Médicos | 3 | Dr. Carlos Silva, Dra. Ana Beatriz, Dr. Roberto Mendes |
| Pacientes | 20 | Nomes fictícios com convênios variados |
| Agendamentos Passados | 40 | Últimos 30 dias (status: realizado) |
| Agendamentos Futuros | 25 | Próximos 14 dias (status: confirmado/pendente) |

#### 5.2 Credenciais Demo
| Perfil | Email | Senha |
|--------|-------|-------|
| Médico | dr.carlos@demo.horariointeligente.com.br | demo123 |
| Médica | dra.ana@demo.horariointeligente.com.br | demo123 |
| Médico | dr.roberto@demo.horariointeligente.com.br | demo123 |

#### 5.3 Funcionalidades Disponíveis
| Funcionalidade | Status | Descrição |
|----------------|--------|-----------|
| Visualização de Agenda | Ativo | Calendário com agendamentos simulados |
| Criação de Agendamentos | Ativo | Funciona normalmente, resetado diariamente |
| Gestão de Pacientes | Ativo | CRUD completo de pacientes |
| Dashboard | Ativo | Métricas baseadas nos dados demo |
| WhatsApp | Desabilitado | Não envia mensagens reais |

#### 5.4 Tour Guiado (Intro.js)
O ambiente demo inclui um tour interativo que apresenta:
1. Dashboard - Visão geral do dia
2. Calendário - Agenda visual com drag-and-drop
3. Novo Agendamento - Processo de criação
4. Lista de Pacientes - Gestão de cadastros
5. Relatórios - Métricas e estatísticas
6. Configurações - Personalização do sistema

#### 5.5 Reset Automático
- **Frequência:** Diariamente às 03:00 (cron job)
- **Script:** /scripts/reset_demo.py
- **Ação:** Limpa e recria todos os dados do ambiente demo

#### 5.6 Fluxo de Conversão
1. Visitante acessa demo.horariointeligente.com.br
2. Seleciona perfil (Médico ou Secretária)
3. Login automático com credenciais demo
4. Tour guiado apresenta funcionalidades
5. Botão "Contratar Agora" em todas as telas
6. Redirecionamento para onboarding de novo cliente

### Restrições
- Não envia mensagens WhatsApp reais
- Dados resetados a cada 24 horas
- Sem persistência entre sessões
- Funcionalidades administrativas desabilitadas

---

## Matriz de Permissões

### Legenda
- **C** = Criar
- **R** = Ler/Visualizar
- **U** = Atualizar
- **D** = Deletar
- **-** = Sem acesso

### Recursos vs. Atores

| Recurso | Admin | Financeiro | Suporte | Profissional | Secretária |
|---------|-------|------------|---------|--------------|------------|
| **Clientes** |
| Dados cadastrais | CRUD | R | R | R (próprio) | R (próprio) |
| Configurações | CRUD | - | R | CRU (próprio) | - |
| Planos | CRUD | RU | R | R (próprio) | - |
| **Financeiro** |
| Faturas | CRUD | CRUD | R | R (próprio) | - |
| Pagamentos | CRUD | CRUD | R | - | - |
| Comissões | CRUD | CRUD | - | - | - |
| Custos | CRUD | CRUD | - | - | - |
| **Operacional** |
| Agendamentos | CRUD | - | R | CRUD (próprio) | CRUD |
| Pacientes | CRUD | - | R | CRUD (próprio) | CRUD |
| Mensagens | R | - | R (meta) | R (próprio) | R |
| **Técnico** |
| Status sistema | R | - | R | - | - |
| Logs | R | - | R | - | - |
| Configurações globais | CRUD | - | R | - | - |
| WhatsApp instâncias | CRUD | - | RU | R (próprio) | R |
| **Usuários** |
| Internos (Admin/Fin/Sup) | CRUD | - | - | - | - |
| Clientes (Prof/Sec) | CRUD | R | R | CRU (próprio) | R |

---

## Considerações de Segurança

### Autenticação
- JWT com expiração de 8 horas
- Verificação de email obrigatória
- Senha com hash bcrypt (mínimo 6 caracteres, recomendado 8+)
- Bloqueio após 5 tentativas de login falhas (futuro)

### Autorização
- Middleware de verificação de tenant (cliente_id)
- Verificação de perfil em cada endpoint
- Princípio do menor privilégio

### Auditoria
- Log de todas as ações administrativas
- Registro de IP e user-agent
- Retenção de logs por 12 meses

### Dados Sensíveis
- Dados de pacientes criptografados em repouso (futuro)
- Comunicação exclusivamente via HTTPS
- Conformidade com LGPD

### Sessões
- Token revogável
- Logout em todos os dispositivos (futuro)
- Detecção de sessão suspeita (futuro)

---

## Roadmap de Implementação

### Fase 1 - Concluída
- [x] Cliente (Profissional e Secretária)
- [x] Administrador (básico)
- [x] Login com verificação de email
- [x] Multi-tenant com subdomínios

### Fase 2 - Concluída
- [x] Financeiro (dashboard e gestão)
- [x] Suporte (dashboard de monitoramento)
- [x] Gestão de parceiros comerciais
- [x] Controle de custos operacionais
- [x] Ambiente Demo/Sandbox
- [ ] Integração PagSeguro

### Fase 3 - Médio Prazo
- [ ] Sistema de tickets
- [ ] Relatórios avançados
- [ ] Notificações push

### Fase 4 - Longo Prazo
- [ ] API pública para clientes Enterprise
- [ ] Multi-idioma
- [ ] App mobile

---

## URLs de Acesso

### Ambientes Principais
| Ambiente | URL | Descrição |
|----------|-----|-----------|
| Site Comercial | https://horariointeligente.com.br | Landing page e informações |
| Painel Admin | https://admin.horariointeligente.com.br | Gestão interna do SaaS |
| Ambiente Demo | https://demo.horariointeligente.com.br | Sandbox para testes |
| Cliente | https://[subdomain].horariointeligente.com.br | Acesso do cliente |

### Credenciais de Teste (Ambiente Admin)
| Perfil | Email | Dashboard |
|--------|-------|-----------|
| Administrador | thelemarco@horariointeligente.com.br | dashboard.html |
| Financeiro | financeiro@horariointeligente.com.br | dashboard-financeiro.html |
| Suporte | suporte@horariointeligente.com.br | dashboard-suporte.html |

---

## Anexo: Estrutura de Dados (Implementada)

### Tabela: usuarios_internos
```sql
CREATE TABLE usuarios_internos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    senha VARCHAR(255) NOT NULL,
    perfil VARCHAR(50) NOT NULL, -- 'admin', 'financeiro', 'suporte'
    ativo BOOLEAN DEFAULT true,
    ultimo_acesso TIMESTAMP,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);
```

### Tabela: parceiros_comerciais
```sql
CREATE TABLE parceiros_comerciais (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    cnpj VARCHAR(18),
    email VARCHAR(255),
    telefone VARCHAR(20),
    percentual_comissao DECIMAL(5,2) DEFAULT 0,
    dados_bancarios JSONB,
    ativo BOOLEAN DEFAULT true,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);
```

### Tabela: clientes_parceiros
```sql
CREATE TABLE clientes_parceiros (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER REFERENCES clientes(id),
    parceiro_id INTEGER REFERENCES parceiros_comerciais(id),
    data_vinculo DATE NOT NULL,
    ativo BOOLEAN DEFAULT true,
    UNIQUE(cliente_id, parceiro_id)
);
```

### Tabela: custos_operacionais
```sql
CREATE TABLE custos_operacionais (
    id SERIAL PRIMARY KEY,
    data_lancamento DATE NOT NULL,
    categoria VARCHAR(100) NOT NULL,
    descricao TEXT,
    valor DECIMAL(10,2) NOT NULL,
    fornecedor VARCHAR(255),
    comprovante_url VARCHAR(500),
    recorrencia VARCHAR(20), -- 'unico', 'mensal', 'anual'
    centro_custo VARCHAR(100),
    criado_por INTEGER REFERENCES usuarios_internos(id),
    criado_em TIMESTAMP DEFAULT NOW()
);
```

### Tabela: log_auditoria
```sql
CREATE TABLE log_auditoria (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER,
    usuario_tipo VARCHAR(50), -- 'interno', 'cliente'
    acao VARCHAR(100) NOT NULL,
    recurso VARCHAR(100),
    recurso_id INTEGER,
    dados_anteriores JSONB,
    dados_novos JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);
```

---

**Documento elaborado por:** Claude AI
**Revisado por:** Equipe Horário Inteligente
**Aprovado por:** [Pendente]
**Última atualização:** 21/12/2025
