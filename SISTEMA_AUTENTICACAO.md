# Sistema de Autenticação e Gestão de Usuários - Horário Inteligente

## Visão Geral

Sistema completo de autenticação e gestão de usuários para o Horário Inteligente SaaS, incluindo:
- Cadastro de novos usuários (médicos e secretárias)
- Login com email e senha
- Recuperação de senha via email
- Gestão de perfil de usuário
- Upload de foto de perfil
- Alteração de senha

## Arquitetura

### 1. Database Schema

#### Tabela: `medicos`
```sql
-- Campos adicionados para gestão de usuários
telefone_particular VARCHAR(20)           -- Telefone pessoal do médico
valor_consulta_particular DECIMAL(10,2)   -- Valor da consulta particular
procedimentos JSONB DEFAULT '[]'::jsonb   -- Array de procedimentos [{nome, duracao_minutos, valor}]
foto_perfil TEXT                          -- Foto em base64
biografia TEXT                            -- Biografia/sobre o médico
recovery_token VARCHAR(255)               -- Token para recuperação de senha
recovery_token_expires TIMESTAMP          -- Expiração do token (1 hora)
```

#### Tabela: `usuarios` (secretárias)
```sql
-- Campos adicionados para gestão de usuários
telefone_particular VARCHAR(20)           -- Telefone pessoal
foto_perfil TEXT                          -- Foto em base64
recovery_token VARCHAR(255)               -- Token para recuperação de senha
recovery_token_expires TIMESTAMP          -- Expiração do token (1 hora)
```

### 2. Backend Services

#### Email Service (`app/services/email_service.py`)

Serviço de envio de emails usando SMTP:

```python
class EmailService:
    def send_password_recovery(to_email, to_name, recovery_token):
        """
        Envia email de recuperação de senha
        - Link expira em 1 hora
        - Template HTML profissional
        """

    def send_welcome_email(to_email, to_name, user_type):
        """
        Envia email de boas-vindas após cadastro
        - Confirmação de conta criada
        - Instruções iniciais
        """
```

**Configuração SMTP:**
- Host: smtp.gmail.com
- Port: 587
- TLS: Enabled
- Credenciais via variáveis de ambiente

### 3. API Endpoints

Todos os endpoints estão em `app/api/user_management.py`

#### 3.1 Registro de Usuário

**POST** `/api/auth/register`

Cadastra novo médico ou secretária no sistema.

**Request Body:**
```json
{
  "tipo": "medico",  // ou "secretaria"
  "nome": "Dr. João Silva",
  "email": "joao@exemplo.com",
  "senha": "senha123",  // mínimo 6 caracteres
  "telefone": "(11) 98765-4321",
  "telefone_particular": "(11) 91234-5678",

  // Campos específicos para médicos
  "crm": "CRM-SP 123456",
  "especialidade": "Cardiologista",
  "convenios_aceitos": ["Unimed", "SulAmérica"],
  "valor_consulta_particular": 300.00,
  "procedimentos": [
    {
      "nome": "Eletrocardiograma",
      "duracao_minutos": 30,
      "valor": 150.00
    }
  ],
  "biografia": "Cardiologista com 15 anos de experiência..."
}
```

**Response:**
```json
{
  "sucesso": true,
  "mensagem": "Cadastro realizado com sucesso! Verifique seu email.",
  "user_id": 123,
  "tipo": "medico"
}
```

**Validações:**
- Email único no sistema
- Senha mínima de 6 caracteres
- CRM e especialidade obrigatórios para médicos
- Envia email de boas-vindas

#### 3.2 Recuperação de Senha

**POST** `/api/auth/forgot-password`

Solicita recuperação de senha via email.

**Request Body:**
```json
{
  "email": "joao@exemplo.com"
}
```

**Response:**
```json
{
  "sucesso": true,
  "mensagem": "Se o email existir, você receberá instruções de recuperação"
}
```

**Comportamento:**
- Sempre retorna sucesso (segurança - não revela se email existe)
- Gera token único: `secrets.token_urlsafe(32)`
- Token expira em 1 hora
- Envia email com link: `/static/reset-senha.html?token=TOKEN`

#### 3.3 Redefinir Senha

**POST** `/api/auth/reset-password`

Redefine senha usando token válido.

**Request Body:**
```json
{
  "token": "abc123...",
  "nova_senha": "novaSenha123"
}
```

**Response:**
```json
{
  "sucesso": true,
  "mensagem": "Senha redefinida com sucesso! Você já pode fazer login."
}
```

**Validações:**
- Token deve existir e não estar expirado
- Nova senha mínimo 6 caracteres
- Invalida token após uso

#### 3.4 Obter Perfil

**GET** `/api/perfil`

Retorna dados do perfil do usuário logado.

**Headers:**
```
Authorization: Bearer {token}
```

**Response (Médico):**
```json
{
  "id": 1,
  "nome": "Dr. João Silva",
  "email": "joao@exemplo.com",
  "tipo": "medico",
  "crm": "CRM-SP 123456",
  "especialidade": "Cardiologista",
  "telefone": "(11) 98765-4321",
  "telefone_particular": "(11) 91234-5678",
  "convenios_aceitos": ["Unimed", "SulAmérica"],
  "valor_consulta_particular": 300.00,
  "procedimentos": [...],
  "biografia": "Cardiologista com 15 anos...",
  "foto_perfil": "data:image/jpeg;base64,...",
  "ativo": true
}
```

**Response (Secretária):**
```json
{
  "id": 2,
  "nome": "Maria Santos",
  "email": "maria@exemplo.com",
  "tipo": "secretaria",
  "telefone": "(11) 98765-4321",
  "telefone_particular": "(11) 91234-5678",
  "foto_perfil": "data:image/jpeg;base64,...",
  "ativo": true
}
```

#### 3.5 Atualizar Perfil

**PUT** `/api/perfil`

Atualiza dados do perfil do usuário logado.

**Headers:**
```
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "nome": "Dr. João Silva Junior",
  "telefone": "(11) 99999-9999",
  "telefone_particular": "(11) 88888-8888",

  // Campos específicos para médicos
  "especialidade": "Cardiologista Intervencionista",
  "convenios_aceitos": ["Unimed", "SulAmérica", "Bradesco"],
  "valor_consulta_particular": 350.00,
  "procedimentos": [
    {
      "nome": "Eletrocardiograma",
      "duracao_minutos": 30,
      "valor": 150.00
    },
    {
      "nome": "Ecocardiograma",
      "duracao_minutos": 45,
      "valor": 250.00
    }
  ],
  "biografia": "Cardiologista com 15 anos..."
}
```

**Response:**
```json
{
  "sucesso": true,
  "mensagem": "Perfil atualizado com sucesso!"
}
```

**Notas:**
- Campos opcionais - só atualiza o que for enviado
- Email não pode ser alterado (usado para login)
- Atualiza `atualizado_em` automaticamente

#### 3.6 Upload de Foto

**POST** `/api/perfil/foto`

Faz upload da foto de perfil (base64).

**Headers:**
```
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "foto_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

**Response:**
```json
{
  "sucesso": true,
  "mensagem": "Foto atualizada com sucesso!"
}
```

**Validações:**
- Tamanho máximo: 2MB
- Aceita qualquer formato de imagem (JPEG, PNG, GIF, etc)

#### 3.7 Alterar Senha

**POST** `/api/perfil/alterar-senha`

Altera senha do usuário logado.

**Headers:**
```
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "senha_atual": "senhaAtual123",
  "nova_senha": "novaSenha456"
}
```

**Response:**
```json
{
  "sucesso": true,
  "mensagem": "Senha alterada com sucesso!"
}
```

**Validações:**
- Senha atual deve estar correta
- Nova senha mínimo 6 caracteres
- Usa bcrypt para hash

### 4. Frontend Pages

#### 4.1 Login (`/static/login.html`)

**Funcionalidades:**
- Login com email e senha
- Verifica token existente ao carregar
- Redireciona para calendário se já logado
- Links para registro e recuperação de senha
- Credenciais de teste visíveis

**Endpoints usados:**
- `POST /api/auth/login`
- `POST /api/auth/verify-token`

#### 4.2 Registro (`/static/registro.html`)

**Funcionalidades:**
- Seleção de tipo de conta (médico/secretária)
- Formulário dinâmico baseado no tipo
- Campos específicos para médicos:
  - CRM e especialidade (obrigatórios)
  - Valor consulta particular
  - Biografia
- Validação de senha (confirmação)
- Telefone e telefone particular
- Redirect para login após sucesso

**Endpoints usados:**
- `POST /api/auth/register`

**Campos do Formulário:**

**Básicos (todos):**
- Nome completo
- Email
- Senha e confirmação
- Telefone
- Telefone particular

**Médicos (adicionais):**
- CRM
- Especialidade
- Valor consulta particular
- Biografia

#### 4.3 Esqueci Senha (`/static/esqueci-senha.html`)

**Funcionalidades:**
- Solicita email para recuperação
- Exibe mensagem de sucesso sempre (segurança)
- Link para voltar ao login

**Endpoints usados:**
- `POST /api/auth/forgot-password`

#### 4.4 Redefinir Senha (`/static/reset-senha.html`)

**Funcionalidades:**
- Recebe token via URL query parameter
- Valida token ao carregar
- Formulário de nova senha com confirmação
- Redirect para login após sucesso

**Endpoints usados:**
- `POST /api/auth/reset-password`

**URL esperada:**
```
/static/reset-senha.html?token=abc123def456...
```

#### 4.5 Perfil (`/static/perfil.html`)

**Funcionalidades:**
- Carrega dados do usuário logado
- Upload de foto (arrastar ou clicar)
- Edição de dados pessoais
- Campos específicos para médicos:
  - Gestão de convênios (adicionar/remover)
  - Gestão de procedimentos (adicionar/remover)
  - CRM, especialidade, biografia
- Alteração de senha
- Validação de campos
- Mensagens de sucesso/erro

**Endpoints usados:**
- `GET /api/perfil`
- `PUT /api/perfil`
- `POST /api/perfil/foto`
- `POST /api/perfil/alterar-senha`

**Gestão de Procedimentos:**
```javascript
procedimentosAtuais = [
  {
    nome: "Eletrocardiograma",
    duracao_minutos: 30,
    valor: 150.00
  }
]
```

## Fluxos de Usuário

### 1. Cadastro e Primeiro Acesso

```
1. Usuário acessa /static/registro.html
2. Seleciona tipo (médico/secretária)
3. Preenche formulário
4. Sistema valida e cria conta
5. Envia email de boas-vindas
6. Redireciona para login
7. Usuário faz login e acessa sistema
```

### 2. Recuperação de Senha

```
1. Usuário acessa /static/esqueci-senha.html
2. Informa email cadastrado
3. Sistema gera token e envia email
4. Usuário clica no link do email
5. Abre /static/reset-senha.html?token=...
6. Define nova senha
7. Redireciona para login
```

### 3. Gestão de Perfil

```
1. Usuário logado clica em "Perfil" no menu
2. Sistema carrega dados atuais
3. Usuário edita informações
4. Sistema valida e salva
5. Exibe mensagem de sucesso
```

## Segurança

### 1. Senhas
- Todas as senhas são hasheadas com **bcrypt**
- Salt gerado automaticamente
- Mínimo de 6 caracteres (pode ser aumentado)
- Nunca expõe senha no banco ou logs

### 2. Tokens de Recuperação
- Gerados com `secrets.token_urlsafe(32)` (criptograficamente seguro)
- Expiram em 1 hora
- Invalidados após uso
- Únicos e não previsíveis

### 3. Autenticação
- JWT tokens para sessões
- Bearer token em todas as requisições autenticadas
- Middleware valida token em cada request
- Token armazena: user_id, user_type, email, cliente_id

### 4. Proteções
- Email único por usuário
- Recuperação de senha não revela se email existe
- Validação de senha atual ao alterar senha
- CORS configurado adequadamente
- SQL injection prevenido com parametrização

## Configuração

### Variáveis de Ambiente

```bash
# Email SMTP
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-app
SMTP_FROM_EMAIL=noreply@horariointeligente.com.br
SMTP_FROM_NAME=Horário Inteligente Sistema

# Base URL para links de recuperação
BASE_URL=https://seu-dominio.com
```

### Habilitar "App Passwords" no Gmail

Para envio de emails via Gmail:

1. Acesse Google Account Security
2. Ative verificação em 2 etapas
3. Gere "App Password" para aplicativo
4. Use essa senha em `SMTP_PASSWORD`

## Testes

### Testar Cadastro

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "tipo": "medico",
    "nome": "Dr. Teste",
    "email": "teste@exemplo.com",
    "senha": "teste123",
    "crm": "CRM-SP 12345",
    "especialidade": "Clínico Geral",
    "telefone": "(11) 98765-4321",
    "telefone_particular": "(11) 91234-5678"
  }'
```

### Testar Recuperação de Senha

```bash
curl -X POST http://localhost:8000/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "teste@exemplo.com"}'
```

### Testar Atualização de Perfil

```bash
TOKEN="seu-jwt-token"

curl -X PUT http://localhost:8000/api/perfil \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Dr. Teste Atualizado",
    "telefone": "(11) 99999-9999"
  }'
```

## Navegação

### Menu Principal (calendario-unificado.html)

Botão "Perfil" adicionado ao menu:
- Desktop: Entre "userInfo" e botão "Novo"
- Mobile: Primeiro item do menu dropdown

### Estrutura de Navegação

```
Login (/static/login.html)
├─> Registro (/static/registro.html)
├─> Esqueci Senha (/static/esqueci-senha.html)
│   └─> Reset Senha (/static/reset-senha.html?token=...)
└─> Calendário (/static/calendario-unificado.html)
    ├─> Dashboard (/static/dashboard.html)
    ├─> Minha Agenda (/static/minha-agenda.html)
    ├─> Configurações (/static/configuracao-agenda.html)
    ├─> **Perfil (/static/perfil.html)**  ← NOVO
    └─> Sair (logout)
```

## Melhorias Futuras

### Funcionalidades Adicionais
- [ ] Verificação de email (enviar link de confirmação)
- [ ] Login social (Google, Facebook)
- [ ] Autenticação de 2 fatores (2FA)
- [ ] Histórico de alterações de perfil
- [ ] Permissões granulares (roles e permissions)
- [ ] API para importar procedimentos de catálogo
- [ ] Validação de CRM via API oficial
- [ ] Limite de tentativas de login (rate limiting)
- [ ] Notificação de login suspeito

### Melhorias de Segurança
- [ ] Política de senha mais forte (maiúsculas, números, símbolos)
- [ ] Expiração de tokens JWT configurável
- [ ] Logout de todas as sessões
- [ ] Logs de auditoria de ações sensíveis
- [ ] CAPTCHA em formulários públicos
- [ ] Validação de força de senha em tempo real
- [ ] Bloqueio de conta após N tentativas falhas

### Melhorias de UX
- [ ] Crop de imagem antes do upload
- [ ] Preview de procedimentos antes de salvar
- [ ] Autocompletar especialidades
- [ ] Máscaras de input para telefone e CRM
- [ ] Validação de email em tempo real
- [ ] Progress bar de upload de foto
- [ ] Dark mode

## Manutenção

### Logs
Todas as operações geram logs em `/var/log/sistema_agendamento.log`:
- ✅ Cadastro realizado
- ✅ Token de recuperação gerado
- ✅ Senha redefinida
- ✅ Perfil atualizado
- ✅ Foto atualizada
- ❌ Erros de validação
- ❌ Falhas de autenticação

### Limpeza de Tokens Expirados

Criar cron job para limpar tokens expirados:

```sql
-- Executar diariamente
UPDATE medicos
SET recovery_token = NULL, recovery_token_expires = NULL
WHERE recovery_token_expires < NOW();

UPDATE usuarios
SET recovery_token = NULL, recovery_token_expires = NULL
WHERE recovery_token_expires < NOW();
```

### Backup

Dados críticos para backup:
- Tabela `medicos` (incluindo procedimentos JSONB)
- Tabela `usuarios`
- Fotos de perfil (se armazenadas em disco)
- Logs de auditoria

## Suporte

### Problemas Comuns

**1. Email não chega**
- Verificar configuração SMTP
- Verificar spam/lixo eletrônico
- Validar credenciais Gmail App Password
- Verificar logs do sistema

**2. Token expirado**
- Token expira em 1 hora
- Solicitar novo token de recuperação
- Verificar timezone do servidor

**3. Foto muito grande**
- Limite: 2MB
- Comprimir imagem antes do upload
- Usar ferramentas online de compressão

**4. Erro ao salvar procedimentos**
- Validar formato JSON
- Verificar campos obrigatórios: nome, duracao_minutos, valor
- Verificar logs do backend

## Conclusão

Este sistema fornece uma base sólida e profissional para gestão de usuários no Horário Inteligente SaaS. Com autenticação segura, recuperação de senha via email, e gestão completa de perfis, os médicos e secretárias podem gerenciar suas informações de forma autônoma e segura.

Para questões ou sugestões, consulte o desenvolvedor responsável.
