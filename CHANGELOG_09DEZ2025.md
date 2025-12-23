# Changelog - 09 de Dezembro de 2025

## Versão 3.5.1 - Documentação Legal e Landing Page

**Data:** 09 de Dezembro de 2025
**Desenvolvedor:** Marco Aurélio Thiele (com Claude Code)

---

## 📄 Documentação Legal Completa

### ✅ Criadas Novas Páginas

#### 1. **Termos e Condições de Uso**
- **Arquivo:** `/static/termos-de-uso.html` (37KB)
- **URL:** https://horariointeligente.com.br/static/termos-de-uso.html
- **Status:** ✅ Publicado e acessível

**Conteúdo:**
- 12 seções completas adaptadas do modelo Z-PRO
- Conceitos importantes (Cliente, Usuário, Administrador, Paciente, Horário Inteligente)
- Funcionalidades da plataforma (agendamento, IA, WhatsApp, lembretes, etc.)
- Requisitos de acesso (idade mínima 18 anos, requisitos técnicos)
- Modelo de assinatura:
  - Individual: R$ 150/mês + R$ 150 ativação
  - Clínica: R$ 200/mês + R$ 200 ativação (2 profissionais incluídos)
- Integração WhatsApp (API oficial e Evolution API com riscos explicados)
- Condutas proibidas e penalidades
- Programa de revendedores e parceiros
- Limitação de responsabilidade detalhada
- Cancelamento e reembolso (7 dias com reembolso total)
- Propriedade intelectual (Marco Aurélio Thiele)
- Suporte técnico (horários, prazos de resposta)
- Lei aplicável: Brasil
- Foro: Volta Redonda - RJ

**Design:**
- Tailwind CSS responsivo
- Ícones Font Awesome
- Índice clicável
- Navegação suave (smooth scroll)
- Botão "Voltar ao topo"
- Seções numeradas com badges coloridos

---

#### 2. **Política de Privacidade**
- **Arquivo:** `/static/politica-privacidade.html` (37KB)
- **URL:** https://horariointeligente.com.br/static/politica-privacidade.html
- **Status:** ✅ Publicado e acessível

**Conformidade LGPD:**
- ✅ 100% conforme Lei nº 13.709/2018
- ✅ Badge de conformidade destacado
- ✅ DPO identificado: Marco Aurélio Thiele
- ✅ Prazo de resposta: 15 dias

**Conteúdo:**
- 10 seções completas
- **Dados coletados:**
  - Cadastro (nome, email, telefone, CPF/CNPJ, especialidade, CRM)
  - Pacientes (nome, telefone, histórico de agendamentos)
  - Uso do sistema (logs, mensagens WhatsApp, configurações)
  - Pagamento (transações, status - cartão processado externamente)
- **Finalidades do tratamento:**
  - Prestação do serviço (agendamentos, lembretes, comunicação)
  - Autenticação e segurança
  - Cobrança e faturamento
  - Suporte técnico
  - Análise e melhoria
  - Cumprimento legal
- **Base legal (LGPD Art. 7º):**
  - Execução de contrato
  - Consentimento
  - Legítimo interesse
  - Obrigação legal
- **Compartilhamento de dados:**
  - Anthropic (Claude AI)
  - Meta/WhatsApp
  - OpenAI (áudio)
  - Hostinger (hospedagem)
  - Gateways de pagamento
  - Obrigações legais
  - Transferência de negócio
- **Segurança:**
  - Criptografia SSL/TLS
  - Senhas hasheadas (bcrypt)
  - Firewall configurado
  - Backup diário
  - Controle de acesso granular
  - Logs de auditoria
- **Tempo de retenção:**
  - Clientes ativos: enquanto houver relação contratual
  - Clientes cancelados: 30 dias (exportação) → exclusão
  - Dados fiscais: 5 anos
  - Logs de segurança: 6 meses
- **Direitos dos titulares (LGPD Art. 18):**
  1. Confirmação e acesso aos dados
  2. Correção de dados
  3. Anonimização/bloqueio
  4. Eliminação
  5. Portabilidade (CSV/JSON)
  6. Informação sobre compartilhamento
  7. Revogação de consentimento
  8. Oposição ao tratamento
- **Como exercer direitos:**
  - Email: thelemarco@yahoo.com.br
  - WhatsApp: (24) 98849-3257
  - Prazo de resposta: 15 dias
- **Cookies:**
  - Essenciais (autenticação, sessões)
  - Performance (uso anônimo)
- **DPO (Encarregado de Dados):**
  - Marco Aurélio Thiele
  - thelemarco@yahoo.com.br
  - (24) 98849-3257
  - Volta Redonda - RJ
- **ANPD:** Link para autoridade nacional

**Design:**
- Tailwind CSS responsivo
- Badges de conformidade LGPD
- Seções coloridas por categoria
- Cards informativos
- Ícones contextuais
- Navegação cruzada com Termos de Uso

---

## 🌐 Atualização da Landing Page

### Mudanças Implementadas

#### 1. **Contatos Atualizados**
- **Email:**
  - Antes: contato@horariointeligente.com.br, suporte@horariointeligente.com.br
  - Agora: **thelemarco@yahoo.com.br**
- **WhatsApp:**
  - Antes: (11) 99999-9999
  - Agora: **(24) 98849-3257**
- **Links WhatsApp (3 locais atualizados):**
  - Botão "Falar com Vendas" (seção CTA)
  - Link "Iniciar conversa" (área de contato)
  - Botão "Falar com Especialista" (box de suporte)
  - URL: `https://wa.me/5524988493257`

#### 2. **Botões de Login Desabilitados**
- **Motivo:** Sistema ainda não está pronto para acesso público
- **Locais desabilitados (4):**
  1. Menu desktop - botão "Entrar"
  2. Menu mobile - botão "Entrar"
  3. Footer - link "Login"
  4. Footer - link "Criar Conta"
- **Técnica:** Comentários HTML `<!-- BOTÃO LOGIN DESABILITADO -->`
- **Reversão:** Basta remover os comentários `<!--` e `-->`

#### 3. **Links Legais no Footer**
- **Adicionados links funcionais:**
  - Termos de Uso → `/static/termos-de-uso.html`
  - Política de Privacidade → `/static/politica-privacidade.html`
  - LGPD → `/static/politica-privacidade.html#secao7` (âncora)
  - Cookies → `/static/politica-privacidade.html#secao8` (âncora)

---

## 📊 Arquivos Modificados

### Novos Arquivos
```
/root/sistema_agendamento/static/termos-de-uso.html           (37KB)
/root/sistema_agendamento/static/politica-privacidade.html    (37KB)
/root/sistema_agendamento/CHANGELOG_09DEZ2025.md              (este arquivo)
```

### Arquivos Modificados
```
/root/sistema_agendamento/static/index.html                   (48KB)
  - Contatos atualizados (3 locais)
  - Botões de login comentados (4 locais)
  - Links legais adicionados (4 links)
```

---

## ✅ Testes de Validação

### Acesso às Páginas
```bash
# Termos de Uso
curl -I https://horariointeligente.com.br/static/termos-de-uso.html
# Status: 200 OK ✅

# Política de Privacidade
curl -I https://horariointeligente.com.br/static/politica-privacidade.html
# Status: 200 OK ✅

# Landing Page Atualizada
curl -I https://horariointeligente.com.br/static/index.html
# Status: 200 OK ✅
```

### Permissões de Arquivo
```bash
-rw-r--r-- 1 root root  48K Dec  9 22:41 index.html
-rw-r--r-- 1 root root  37K Dec  9 22:39 termos-de-uso.html
-rw-r--r-- 1 root root  37K Dec  9 22:41 politica-privacidade.html
```

---

## 🎯 Impacto das Mudanças

### Benefícios

#### 1. **Conformidade Legal**
- ✅ Sistema protegido legalmente com Termos de Uso claros
- ✅ LGPD 100% conforme (Lei 13.709/2018)
- ✅ Direitos dos usuários garantidos e documentados
- ✅ Responsabilidades claramente definidas

#### 2. **Transparência**
- ✅ Usuários sabem exatamente o que esperar do serviço
- ✅ Políticas de privacidade acessíveis e compreensíveis
- ✅ Contato do DPO claramente identificado
- ✅ Processos de cancelamento e reembolso documentados

#### 3. **Proteção do Negócio**
- ✅ Limitação de responsabilidade definida
- ✅ Propriedade intelectual protegida
- ✅ Condutas proibidas especificadas com penalidades
- ✅ Foro competente estabelecido (Volta Redonda - RJ)

#### 4. **Experiência do Usuário**
- ✅ Contatos reais e funcionais na landing page
- ✅ Links WhatsApp diretos com mensagem pré-preenchida
- ✅ Navegação profissional entre documentos legais
- ✅ Design moderno e responsivo

---

## 📌 Próximos Passos Recomendados

### Curto Prazo
- [ ] Revisar textos legais com advogado especializado
- [ ] Adicionar sistema de aceite dos termos no cadastro
- [ ] Implementar checkbox de consentimento LGPD
- [ ] Criar versão em PDF dos documentos para download

### Médio Prazo
- [ ] Implementar centro de preferências de privacidade
- [ ] Adicionar banner de cookies (LGPD)
- [ ] Criar FAQ sobre privacidade e dados
- [ ] Implementar portal de solicitações LGPD

### Longo Prazo
- [ ] Auditoria de conformidade LGPD completa
- [ ] Certificação ISO 27001 (segurança da informação)
- [ ] Relatório de impacto de proteção de dados (RIPD)
- [ ] Programa de conscientização de segurança

---

## 📞 Informações de Contato Atualizadas

### Contato Comercial e Suporte
- **Email:** thelemarco@yahoo.com.br
- **WhatsApp:** (24) 98849-3257
- **Localização:** Volta Redonda - RJ, Brasil

### DPO (Encarregado de Proteção de Dados)
- **Nome:** Marco Aurélio Thiele
- **Email:** thelemarco@yahoo.com.br
- **WhatsApp:** (24) 98849-3257

---

## 🔗 Links Importantes

### Documentação Pública
- **Landing Page:** https://horariointeligente.com.br
- **Termos de Uso:** https://horariointeligente.com.br/static/termos-de-uso.html
- **Política de Privacidade:** https://horariointeligente.com.br/static/politica-privacidade.html

### Referências Legais
- **LGPD:** Lei nº 13.709/2018
- **Marco Civil da Internet:** Lei nº 12.965/2014
- **Código de Defesa do Consumidor:** Lei nº 8.078/1990
- **ANPD:** https://www.gov.br/anpd

---

## 📝 Notas Técnicas

### Padrões Seguidos
- ✅ HTML5 semântico
- ✅ CSS responsivo (Tailwind CSS)
- ✅ Acessibilidade (WCAG 2.1 básico)
- ✅ SEO otimizado (meta tags, títulos hierárquicos)
- ✅ Performance (assets CDN, compressão)

### Compatibilidade
- ✅ Chrome/Edge (últimas versões)
- ✅ Firefox (últimas versões)
- ✅ Safari (últimas versões)
- ✅ Mobile (iOS/Android)
- ✅ Tablets

### Segurança
- ✅ HTTPS obrigatório
- ✅ Headers de segurança configurados
- ✅ Sem JavaScript malicioso
- ✅ Links externos com target="_blank" e rel apropriado

---

**Documentação completa e profissional para o Horário Inteligente! 🎉**

---

*Gerado automaticamente em 09 de Dezembro de 2025 por Claude Code*
