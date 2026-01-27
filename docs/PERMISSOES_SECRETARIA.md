# Sistema de Permissões da Secretária

## Visão Geral

O sistema permite que secretárias gerenciem a agenda e configurações do médico vinculado, com acesso restrito a funcionalidades específicas.

## Estrutura do Banco de Dados

### Campo `medico_vinculado_id`

Secretárias estão na tabela `medicos` com:
- `is_secretaria = true`
- `medico_vinculado_id` = ID do médico que ela atende

```sql
ALTER TABLE medicos ADD COLUMN medico_vinculado_id INTEGER REFERENCES medicos(id);
```

### Exemplo

| id | nome | is_secretaria | medico_vinculado_id |
|----|------|---------------|---------------------|
| 31 | Dr. João da Silva | false | NULL |
| 32 | Ana Santos | true | 31 |

## Credenciais de Teste

| Usuário | Email | Senha | Tipo |
|---------|-------|-------|------|
| Dr. João | drjoao@teste.com | teste123 | Médico |
| Ana | ana@teste.com | teste123 | Secretária |

## Fluxo de Acesso

### Login
1. Secretária faz login com email/senha
2. API retorna `is_secretaria: true` e `medico_vinculado_id: 31`
3. Redireciona para `/static/conversas.html`

### Páginas Acessíveis

| Página | Funcionalidade |
|--------|----------------|
| `conversas.html` | Painel de conversas WhatsApp (página inicial) |
| `calendario-unificado.html` | Ver e agendar consultas do médico |
| `configuracoes.html` | Horários, Bloqueios, Lembretes |
| `alterar-senha.html` | Alterar própria senha |

### Páginas Bloqueadas

| Página | Redirecionamento |
|--------|------------------|
| `dashboard.html` | → `conversas.html` |
| `perfil.html` | → `alterar-senha.html` |

### Abas em Configurações

| Aba | Acesso |
|-----|--------|
| Horários | Pode visualizar e editar |
| Bloqueios | Pode adicionar férias, folgas |
| Lembretes | Pode ajustar configurações |
| Valores | Oculta (preços/convênios) |
| Assinatura | Oculta (plano/pagamento) |

## Navegação

A secretária tem acesso aos seguintes botões em todas as páginas:

| Ícone | Descrição | Destino |
|-------|-----------|---------|
| 📅 | Calendário | `calendario-unificado.html` |
| 💬 | WhatsApp | `conversas.html` |
| ⚙️ | Configurações | `configuracoes.html` |
| 🔑 | Alterar Senha | `alterar-senha.html` |
| 🚪 | Sair | Logout |

## API

### Login (`POST /api/auth/login`)

Retorna dados adicionais para secretária:

```json
{
  "access_token": "...",
  "user": {
    "id": 32,
    "nome": "Ana Santos",
    "tipo": "secretaria",
    "is_secretaria": true,
    "medico_vinculado_id": 31
  }
}
```

### Perfil (`GET /api/auth/me`)

Retorna `medico_vinculado_id` para secretária usar nas requisições de configuração.

### Alterar Senha (`POST /api/perfil/alterar-senha`)

Funciona para tipo `secretaria` (busca na tabela `medicos`).

```json
{
  "senha_atual": "teste123",
  "nova_senha": "novaSenha456"
}
```

## Arquivos Modificados

### Backend
- `app/models/medico.py` - Campo `medico_vinculado_id`
- `app/api/auth.py` - Retorna `medico_vinculado_id` no login
- `app/api/user_management.py` - Alteração de senha para secretária

### Frontend
- `static/login.html` - Redirecionamento para conversas
- `static/conversas.html` - Navegação da secretária
- `static/calendario-unificado.html` - Suporte para secretária
- `static/configuracoes.html` - Abas restritas e navegação
- `static/alterar-senha.html` - Nova página de alteração de senha
- `static/perfil.html` - Bloqueio de acesso
- `static/dashboard.html` - Bloqueio de acesso

## Verificação

### Testar Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -d 'username=ana@teste.com&password=teste123'
```

### Verificar Vínculo
```bash
# Deve retornar medico_vinculado_id: 31
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/auth/me
```

### Testar Acesso às Configurações
```bash
# Secretária acessa configurações do médico vinculado
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/configuracao/intervalos/31
```
