# Sistema de Autenticação Web - ProSaúde

**Data:** 28 de novembro de 2025
**Autor:** Marco com assistência do Claude Code

## 📋 Resumo das Alterações

Implementado sistema completo de autenticação para a interface web do calendário, garantindo que apenas usuários autenticados possam acessar o sistema.

---

## ✅ Alterações Implementadas

### 1. Página de Login (`/static/login.html`)

**Arquivo criado:** `/root/sistema_agendamento/static/login.html`

**Funcionalidades:**
- ✅ Interface moderna e responsiva com Tailwind CSS
- ✅ Formulário de login com email e senha
- ✅ Validação em tempo real
- ✅ Exibição de erros de autenticação
- ✅ Toggle de visualização de senha
- ✅ Armazenamento seguro do token JWT no localStorage
- ✅ Redirecionamento automático se já estiver logado
- ✅ Verificação de validade do token ao carregar

**Credenciais de acesso:**
```
Email: admin@prosaude.com
Senha: admin123
```

**Funcionalidades técnicas:**
- Integração com `/api/auth/login`
- Verificação de token via `/api/auth/verify-token`
- Armazenamento de dados do usuário no localStorage
- Redirecionamento para calendário após login bem-sucedido

---

### 2. Proteção do Calendário (`/static/calendario-unificado.html`)

**Arquivo modificado:** `/root/sistema_agendamento/static/calendario-unificado.html`

**Alterações realizadas:**

#### a) Verificação de Autenticação
```javascript
// Função auto-executável que verifica autenticação ao carregar
(function checkAuth() {
    authToken = localStorage.getItem('authToken');

    if (!authToken) {
        window.location.href = '/static/login.html';
        return;
    }

    // Verifica validade do token via API
    fetch('/api/auth/verify-token', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authToken}` }
    })
    .then(response => {
        if (!response.ok) throw new Error('Token inválido');
        return response.json();
    })
    .catch(error => {
        // Token inválido, redirecionar para login
        localStorage.removeItem('authToken');
        localStorage.removeItem('userData');
        window.location.href = '/static/login.html';
    });
})();
```

#### b) Função de Logout
```javascript
function logout() {
    if (confirm('Deseja realmente sair do sistema?')) {
        localStorage.removeItem('authToken');
        localStorage.removeItem('userData');
        window.location.href = '/static/login.html';
    }
}
```

#### c) Função para Requisições Autenticadas
```javascript
async function fetchAuth(url, options = {}) {
    const token = localStorage.getItem('authToken');

    if (!token) {
        window.location.href = '/static/login.html';
        return;
    }

    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`
    };

    const response = await fetch(url, options);

    if (response.status === 401) {
        localStorage.removeItem('authToken');
        localStorage.removeItem('userData');
        window.location.href = '/static/login.html';
        return;
    }

    return response;
}
```

#### d) Header com Informações do Usuário
```html
<div class="flex items-center space-x-4">
    <!-- Informações do usuário logado -->
    <span id="userInfo" class="text-sm text-gray-600 mr-2">
        <i class="fas fa-user-circle mr-1"></i>
        <span id="userName"></span>
    </span>

    <!-- Botão de logout -->
    <button onclick="logout()" class="px-4 py-2 text-sm bg-red-100 text-red-700 rounded-lg hover:bg-red-200">
        <i class="fas fa-sign-out-alt mr-2"></i>
        Sair
    </button>
</div>
```

---

### 3. Página de Redirecionamento (`/static/index.html`)

**Arquivo criado:** `/root/sistema_agendamento/static/index.html`

**Funcionalidade:**
- Verifica se há token no localStorage
- Redireciona para calendário se autenticado
- Redireciona para login se não autenticado

---

## 🔒 Fluxo de Autenticação

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Usuário acessa /static/index.html ou /static/calendario  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Tem token no  │
                 │ localStorage? │
                 └───────┬───────┘
                         │
            ┌────────────┴────────────┐
            │ NÃO                SIM │
            ▼                         ▼
    ┌──────────────┐        ┌────────────────┐
    │ Redirecionar │        │ Verificar se   │
    │ para login   │        │ token é válido │
    └──────────────┘        └────────┬───────┘
                                     │
                        ┌────────────┴────────────┐
                        │ VÁLIDO         INVÁLIDO │
                        ▼                         ▼
              ┌──────────────────┐    ┌──────────────────┐
              │ Carregar         │    │ Limpar storage   │
              │ calendário       │    │ Redirecionar     │
              │                  │    │ para login       │
              └──────────────────┘    └──────────────────┘
```

---

## 🔑 API de Autenticação

### Login
```bash
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin@prosaude.com
password=admin123
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "nome": "Administrador",
    "email": "admin@prosaude.com",
    "tipo": "secretaria",
    "especialidade": "Administração"
  }
}
```

### Verificar Token
```bash
POST /api/auth/verify-token
Authorization: Bearer <token>
```

**Resposta:**
```json
{
  "valid": true,
  "user_id": 1,
  "user_type": "secretaria",
  "email": "admin@prosaude.com"
}
```

### Obter Usuário Atual
```bash
GET /api/auth/me
Authorization: Bearer <token>
```

### Logout
```bash
POST /api/auth/logout
Authorization: Bearer <token>
```

---

## 🧪 Como Testar

### 1. Testar Login via API
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -F "username=admin@prosaude.com" \
  -F "password=admin123"
```

### 2. Verificar Token
```bash
TOKEN="<seu_token_aqui>"
curl -X POST http://localhost:8000/api/auth/verify-token \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Testar Acesso às Páginas

**Sem autenticação:**
- Acessar: `http://localhost:8000/static/calendario-unificado.html`
- Resultado esperado: Redirecionamento para `/static/login.html`

**Com autenticação:**
1. Acessar: `http://localhost:8000/static/login.html`
2. Fazer login com credenciais padrão
3. Resultado esperado: Redirecionamento para `/static/calendario-unificado.html`
4. Verificar que o nome do usuário aparece no header
5. Clicar em "Sair" deve redirecionar para login

---

## 📂 Arquivos Alterados

```
sistema_agendamento/
├── static/
│   ├── login.html                    # ✅ NOVO - Página de login
│   ├── index.html                    # ✅ NOVO - Redirecionamento
│   └── calendario-unificado.html     # ✏️ MODIFICADO - Proteção adicionada
└── AUTENTICACAO_WEB.md              # ✅ NOVO - Esta documentação
```

---

## 🔐 Segurança Implementada

1. **Verificação no Frontend:**
   - Token armazenado em localStorage
   - Verificação automática ao carregar cada página
   - Redirecionamento automático se não autenticado

2. **Verificação no Backend:**
   - Token JWT com expiração de 8 horas
   - Validação de assinatura JWT
   - Verificação de expiração do token

3. **Proteção Contra Acesso Não Autorizado:**
   - Redirecionamento automático para login
   - Limpeza de storage em caso de token inválido
   - Verificação em todas as requisições (via fetchAuth)

---

## ⚠️ Notas Importantes

1. **Armazenamento do Token:**
   - Token armazenado em localStorage
   - Em produção, considerar usar httpOnly cookies para maior segurança

2. **Credenciais Padrão:**
   - Email: `admin@prosaude.com`
   - Senha: `admin123`
   - ⚠️ **Alterar em produção!**

3. **Validade do Token:**
   - Expiração: 8 horas (480 minutos)
   - Após expiração, usuário deve fazer login novamente

4. **Próximas Melhorias:**
   - [ ] Implementar refresh token
   - [ ] Adicionar rate limiting no login
   - [ ] Hash de senhas com bcrypt
   - [ ] Proteção contra ataques de força bruta
   - [ ] Implementar 2FA (autenticação de dois fatores)

---

## 🎯 Páginas do Sistema

| URL | Descrição | Protegido |
|-----|-----------|-----------|
| `/static/index.html` | Redirecionamento inicial | ✅ Sim |
| `/static/login.html` | Página de login | ❌ Público |
| `/static/calendario-unificado.html` | Calendário de agendamentos | ✅ Sim |
| `/static/dashboard.html` | Dashboard com login próprio | ✅ Sim |

---

## ✅ Status Final

- ✅ Página de login criada e funcional
- ✅ Verificação de autenticação implementada
- ✅ Redirecionamento automático funcionando
- ✅ Exibição do nome do usuário no header
- ✅ Botão de logout implementado
- ✅ Sistema testado e operacional

**Sistema de autenticação web totalmente implementado e funcional!**
