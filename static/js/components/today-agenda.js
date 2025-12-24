/**
 * HORÁRIO INTELIGENTE - Agenda de Hoje
 * Componente de visão rápida da agenda do dia para médicos
 *
 * Uso:
 *   // Renderizar no container
 *   HiTodayAgenda.render('#agenda-container', {
 *     agendamentos: [...],
 *     onClickItem: (agendamento) => { ... },
 *     onConfirm: (agendamento) => { ... }
 *   });
 *
 *   // Atualizar dados
 *   HiTodayAgenda.update(novosDados);
 */

(function(global) {
  'use strict';

  let container = null;
  let currentOptions = {};

  /**
   * Formata hora para exibição
   */
  function formatTime(time) {
    if (!time) return '';
    return time.substring(0, 5);
  }

  /**
   * Obtém saudação baseada na hora
   */
  function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return 'Bom dia';
    if (hour < 18) return 'Boa tarde';
    return 'Boa noite';
  }

  /**
   * Formata data de hoje
   */
  function getTodayFormatted() {
    const today = new Date();
    const options = { weekday: 'long', day: 'numeric', month: 'long' };
    return today.toLocaleDateString('pt-BR', options);
  }

  /**
   * Calcula tempo até o próximo agendamento
   */
  function getTimeUntil(time) {
    const now = new Date();
    const [hours, minutes] = time.split(':').map(Number);
    const target = new Date();
    target.setHours(hours, minutes, 0, 0);

    const diff = target - now;
    if (diff < 0) return null; // Já passou

    const diffMinutes = Math.floor(diff / 60000);
    if (diffMinutes < 60) {
      return `em ${diffMinutes} min`;
    }

    const diffHours = Math.floor(diffMinutes / 60);
    const remainingMinutes = diffMinutes % 60;
    if (remainingMinutes === 0) {
      return `em ${diffHours}h`;
    }
    return `em ${diffHours}h ${remainingMinutes}min`;
  }

  /**
   * Obtém classe CSS do status
   */
  function getStatusClass(status) {
    const classes = {
      'confirmado': 'hi-status--success',
      'pendente': 'hi-status--warning',
      'cancelado': 'hi-status--error',
      'realizado': 'hi-status--info',
      'em_atendimento': 'hi-status--primary'
    };
    return classes[status?.toLowerCase()] || 'hi-status--default';
  }

  /**
   * Obtém ícone do status
   */
  function getStatusIcon(status) {
    const icons = {
      'confirmado': 'fa-check-circle',
      'pendente': 'fa-clock',
      'cancelado': 'fa-times-circle',
      'realizado': 'fa-check-double',
      'em_atendimento': 'fa-user-md'
    };
    return icons[status?.toLowerCase()] || 'fa-circle';
  }

  /**
   * Escapa HTML
   */
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Cria HTML de um item da agenda
   */
  function createAgendaItem(agendamento, isNext = false) {
    const timeUntil = getTimeUntil(agendamento.hora);
    const statusClass = getStatusClass(agendamento.status);
    const statusIcon = getStatusIcon(agendamento.status);
    const isPast = !timeUntil && agendamento.status !== 'em_atendimento';

    return `
      <div class="hi-agenda-item ${isNext ? 'hi-agenda-item--next' : ''} ${isPast ? 'hi-agenda-item--past' : ''}"
           data-id="${agendamento.id}"
           role="button"
           tabindex="0"
           aria-label="Agendamento de ${escapeHtml(agendamento.paciente?.nome)} às ${formatTime(agendamento.hora)}">

        <div class="hi-agenda-item__time">
          <span class="hi-time">${formatTime(agendamento.hora)}</span>
          ${timeUntil ? `<span class="hi-time-until">${timeUntil}</span>` : ''}
        </div>

        <div class="hi-agenda-item__content">
          <div class="hi-agenda-item__header">
            <span class="hi-patient-name">${escapeHtml(agendamento.paciente?.nome || 'Paciente')}</span>
            <span class="hi-status ${statusClass}">
              <i class="fas ${statusIcon}" aria-hidden="true"></i>
            </span>
          </div>
          <div class="hi-agenda-item__details">
            ${agendamento.tipo ? `<span class="hi-detail"><i class="fas fa-stethoscope" aria-hidden="true"></i> ${escapeHtml(agendamento.tipo)}</span>` : ''}
            ${agendamento.convenio ? `<span class="hi-detail"><i class="fas fa-id-card" aria-hidden="true"></i> ${escapeHtml(agendamento.convenio)}</span>` : ''}
          </div>
        </div>

        ${agendamento.status === 'pendente' ? `
          <button class="hi-agenda-item__action hi-btn--confirm"
                  data-action="confirm"
                  data-id="${agendamento.id}"
                  aria-label="Confirmar presença"
                  title="Confirmar presença">
            <i class="fas fa-check" aria-hidden="true"></i>
          </button>
        ` : ''}
      </div>
    `;
  }

  /**
   * Cria o próximo atendimento destacado
   */
  function createNextAppointment(agendamento) {
    if (!agendamento) return '';

    const timeUntil = getTimeUntil(agendamento.hora);

    return `
      <div class="hi-next-appointment">
        <div class="hi-next-header">
          <span class="hi-next-label">
            <i class="fas fa-bell" aria-hidden="true"></i>
            Próximo Atendimento
          </span>
          ${timeUntil ? `<span class="hi-next-time">${timeUntil}</span>` : ''}
        </div>

        <div class="hi-next-content" data-id="${agendamento.id}" role="button" tabindex="0">
          <div class="hi-next-time-big">${formatTime(agendamento.hora)}</div>
          <div class="hi-next-info">
            <span class="hi-next-patient">${escapeHtml(agendamento.paciente?.nome)}</span>
            <span class="hi-next-details">
              ${agendamento.tipo || 'Consulta'}
              ${agendamento.convenio ? ` • ${agendamento.convenio}` : ''}
            </span>
            ${agendamento.paciente?.telefone ? `
              <span class="hi-next-phone">
                <i class="fas fa-phone" aria-hidden="true"></i>
                ${escapeHtml(agendamento.paciente.telefone)}
              </span>
            ` : ''}
          </div>
        </div>

        <div class="hi-next-actions">
          <button class="hi-btn hi-btn--secondary hi-btn--sm" data-action="view" data-id="${agendamento.id}">
            <i class="fas fa-eye" aria-hidden="true"></i>
            Ver Detalhes
          </button>
          ${agendamento.status === 'pendente' ? `
            <button class="hi-btn hi-btn--success hi-btn--sm" data-action="confirm" data-id="${agendamento.id}">
              <i class="fas fa-check" aria-hidden="true"></i>
              Confirmar
            </button>
          ` : ''}
        </div>
      </div>
    `;
  }

  /**
   * Cria resumo de estatísticas
   */
  function createStats(agendamentos) {
    const total = agendamentos.length;
    const confirmados = agendamentos.filter(a => a.status === 'confirmado').length;
    const pendentes = agendamentos.filter(a => a.status === 'pendente').length;
    const realizados = agendamentos.filter(a => a.status === 'realizado').length;

    return `
      <div class="hi-agenda-stats">
        <div class="hi-stat">
          <span class="hi-stat-value">${total}</span>
          <span class="hi-stat-label">Total</span>
        </div>
        <div class="hi-stat hi-stat--success">
          <span class="hi-stat-value">${confirmados}</span>
          <span class="hi-stat-label">Confirmados</span>
        </div>
        <div class="hi-stat hi-stat--warning">
          <span class="hi-stat-value">${pendentes}</span>
          <span class="hi-stat-label">Pendentes</span>
        </div>
        <div class="hi-stat hi-stat--info">
          <span class="hi-stat-value">${realizados}</span>
          <span class="hi-stat-label">Realizados</span>
        </div>
      </div>
    `;
  }

  /**
   * Renderiza a agenda completa
   */
  function render(agendamentos, options = {}) {
    const { medicoNome = 'Doutor(a)', onClickItem, onConfirm, showStats = true } = options;

    // Encontra o próximo agendamento (não realizado e não cancelado)
    const now = new Date();
    const currentTimeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    const futureAgendamentos = agendamentos.filter(a => {
      return a.hora >= currentTimeStr &&
             a.status !== 'cancelado' &&
             a.status !== 'realizado';
    }).sort((a, b) => a.hora.localeCompare(b.hora));

    const nextAppointment = futureAgendamentos[0];
    const otherAgendamentos = agendamentos.filter(a => a.id !== nextAppointment?.id);

    let html = `
      <div class="hi-today-agenda">
        <!-- Header -->
        <div class="hi-agenda-header">
          <div class="hi-greeting">
            <h2>${getGreeting()}, ${escapeHtml(medicoNome)}!</h2>
            <p class="hi-today-date">
              <i class="fas fa-calendar-day" aria-hidden="true"></i>
              ${getTodayFormatted()}
            </p>
          </div>
        </div>

        ${showStats ? createStats(agendamentos) : ''}

        ${nextAppointment ? createNextAppointment(nextAppointment) : ''}

        <!-- Lista de agendamentos -->
        <div class="hi-agenda-list">
          <h3 class="hi-list-title">
            <i class="fas fa-list" aria-hidden="true"></i>
            Agenda de Hoje
          </h3>

          ${otherAgendamentos.length > 0 ? `
            <div class="hi-agenda-items">
              ${otherAgendamentos.map(a => createAgendaItem(a)).join('')}
            </div>
          ` : `
            <div class="hi-empty-agenda">
              <i class="fas fa-calendar-check" aria-hidden="true"></i>
              <p>Nenhum outro agendamento para hoje</p>
            </div>
          `}
        </div>
      </div>
    `;

    return html;
  }

  /**
   * Configura event listeners
   */
  function setupListeners() {
    if (!container) return;

    // Click em item da agenda
    container.addEventListener('click', (e) => {
      const item = e.target.closest('.hi-agenda-item, .hi-next-content');
      const actionBtn = e.target.closest('[data-action]');

      if (actionBtn) {
        e.stopPropagation();
        const action = actionBtn.dataset.action;
        const id = actionBtn.dataset.id;

        if (action === 'confirm' && typeof currentOptions.onConfirm === 'function') {
          currentOptions.onConfirm({ id });
        } else if (action === 'view' && typeof currentOptions.onClickItem === 'function') {
          currentOptions.onClickItem({ id });
        }
        return;
      }

      if (item && typeof currentOptions.onClickItem === 'function') {
        const id = item.dataset.id;
        currentOptions.onClickItem({ id });
      }
    });

    // Keyboard navigation
    container.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        const item = e.target.closest('.hi-agenda-item, .hi-next-content');
        if (item) {
          e.preventDefault();
          item.click();
        }
      }
    });
  }

  /**
   * API pública
   */
  const HiTodayAgenda = {
    /**
     * Renderiza a agenda em um container
     */
    render(containerEl, options = {}) {
      container = typeof containerEl === 'string'
        ? document.querySelector(containerEl)
        : containerEl;

      if (!container) {
        console.error('Container não encontrado');
        return;
      }

      currentOptions = options;
      const { agendamentos = [] } = options;

      container.innerHTML = render(agendamentos, options);
      setupListeners();
    },

    /**
     * Atualiza os dados da agenda
     */
    update(agendamentos) {
      if (!container) return;

      currentOptions.agendamentos = agendamentos;
      container.innerHTML = render(agendamentos, currentOptions);
    },

    /**
     * Obtém o container atual
     */
    getContainer() {
      return container;
    },

    /**
     * Destrói o componente
     */
    destroy() {
      if (container) {
        container.innerHTML = '';
        container = null;
      }
      currentOptions = {};
    }
  };

  // Estilos do componente
  const styles = document.createElement('style');
  styles.textContent = `
    .hi-today-agenda {
      display: flex;
      flex-direction: column;
      gap: var(--hi-space-6, 24px);
    }

    /* Header */
    .hi-agenda-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .hi-greeting h2 {
      font-size: var(--hi-font-size-2xl, 1.5rem);
      font-weight: var(--hi-font-weight-bold, 700);
      color: var(--hi-text-primary, #1f2937);
      margin: 0 0 var(--hi-space-1, 4px) 0;
    }

    .hi-today-date {
      display: flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      color: var(--hi-text-secondary, #6b7280);
      font-size: var(--hi-font-size-sm, 0.875rem);
      margin: 0;
      text-transform: capitalize;
    }

    /* Stats */
    .hi-agenda-stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: var(--hi-space-3, 12px);
    }

    @media (max-width: 480px) {
      .hi-agenda-stats {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    .hi-stat {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: var(--hi-space-3, 12px);
      background-color: var(--hi-gray-50, #f9fafb);
      border-radius: var(--hi-radius-lg, 12px);
    }

    .hi-stat-value {
      font-size: var(--hi-font-size-2xl, 1.5rem);
      font-weight: var(--hi-font-weight-bold, 700);
      color: var(--hi-text-primary, #1f2937);
    }

    .hi-stat-label {
      font-size: var(--hi-font-size-xs, 0.75rem);
      color: var(--hi-text-secondary, #6b7280);
    }

    .hi-stat--success .hi-stat-value { color: var(--hi-success, #10b981); }
    .hi-stat--warning .hi-stat-value { color: var(--hi-warning, #f59e0b); }
    .hi-stat--info .hi-stat-value { color: var(--hi-info, #3b82f6); }

    /* Próximo atendimento */
    .hi-next-appointment {
      background: linear-gradient(135deg, var(--hi-primary, #3b82f6), var(--hi-secondary, #6366f1));
      border-radius: var(--hi-radius-xl, 16px);
      padding: var(--hi-space-4, 16px);
      color: white;
    }

    .hi-next-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: var(--hi-space-3, 12px);
    }

    .hi-next-label {
      display: flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      font-size: var(--hi-font-size-sm, 0.875rem);
      font-weight: var(--hi-font-weight-medium, 500);
      opacity: 0.9;
    }

    .hi-next-time {
      background-color: rgba(255, 255, 255, 0.2);
      padding: var(--hi-space-1, 4px) var(--hi-space-3, 12px);
      border-radius: var(--hi-radius-full, 9999px);
      font-size: var(--hi-font-size-sm, 0.875rem);
      font-weight: var(--hi-font-weight-semibold, 600);
    }

    .hi-next-content {
      display: flex;
      gap: var(--hi-space-4, 16px);
      padding: var(--hi-space-3, 12px);
      background-color: rgba(255, 255, 255, 0.1);
      border-radius: var(--hi-radius-lg, 12px);
      cursor: pointer;
      transition: background-color var(--hi-transition-fast, 150ms);
    }

    .hi-next-content:hover {
      background-color: rgba(255, 255, 255, 0.2);
    }

    .hi-next-time-big {
      font-size: var(--hi-font-size-3xl, 1.875rem);
      font-weight: var(--hi-font-weight-bold, 700);
      line-height: 1;
    }

    .hi-next-info {
      display: flex;
      flex-direction: column;
      gap: var(--hi-space-1, 4px);
    }

    .hi-next-patient {
      font-size: var(--hi-font-size-lg, 1.125rem);
      font-weight: var(--hi-font-weight-semibold, 600);
    }

    .hi-next-details {
      font-size: var(--hi-font-size-sm, 0.875rem);
      opacity: 0.8;
    }

    .hi-next-phone {
      display: flex;
      align-items: center;
      gap: var(--hi-space-1, 4px);
      font-size: var(--hi-font-size-sm, 0.875rem);
      opacity: 0.8;
    }

    .hi-next-actions {
      display: flex;
      gap: var(--hi-space-2, 8px);
      margin-top: var(--hi-space-3, 12px);
    }

    .hi-next-actions .hi-btn {
      flex: 1;
    }

    .hi-next-actions .hi-btn--secondary {
      background-color: rgba(255, 255, 255, 0.2);
      border-color: transparent;
      color: white;
    }

    .hi-next-actions .hi-btn--secondary:hover {
      background-color: rgba(255, 255, 255, 0.3);
    }

    /* Lista de agendamentos */
    .hi-list-title {
      display: flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      font-size: var(--hi-font-size-base, 1rem);
      font-weight: var(--hi-font-weight-semibold, 600);
      color: var(--hi-text-primary, #1f2937);
      margin: 0 0 var(--hi-space-4, 16px) 0;
    }

    .hi-list-title i {
      color: var(--hi-primary, #3b82f6);
    }

    .hi-agenda-items {
      display: flex;
      flex-direction: column;
      gap: var(--hi-space-2, 8px);
    }

    .hi-agenda-item {
      display: flex;
      align-items: center;
      gap: var(--hi-space-3, 12px);
      padding: var(--hi-space-3, 12px);
      background-color: white;
      border: 1px solid var(--hi-border-light, #e5e7eb);
      border-radius: var(--hi-radius-lg, 12px);
      cursor: pointer;
      transition: all var(--hi-transition-fast, 150ms);
    }

    .hi-agenda-item:hover {
      border-color: var(--hi-primary-light, #60a5fa);
      box-shadow: var(--hi-shadow-sm, 0 1px 2px rgba(0,0,0,0.05));
    }

    .hi-agenda-item:focus-visible {
      outline: 2px solid var(--hi-primary, #3b82f6);
      outline-offset: 2px;
    }

    .hi-agenda-item--past {
      opacity: 0.6;
    }

    .hi-agenda-item__time {
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 60px;
    }

    .hi-time {
      font-size: var(--hi-font-size-lg, 1.125rem);
      font-weight: var(--hi-font-weight-bold, 700);
      color: var(--hi-text-primary, #1f2937);
    }

    .hi-time-until {
      font-size: var(--hi-font-size-xs, 0.75rem);
      color: var(--hi-primary, #3b82f6);
    }

    .hi-agenda-item__content {
      flex: 1;
      min-width: 0;
    }

    .hi-agenda-item__header {
      display: flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
    }

    .hi-patient-name {
      font-size: var(--hi-font-size-base, 1rem);
      font-weight: var(--hi-font-weight-medium, 500);
      color: var(--hi-text-primary, #1f2937);
    }

    .hi-status {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      font-size: 10px;
    }

    .hi-status--success { color: var(--hi-success, #10b981); }
    .hi-status--warning { color: var(--hi-warning, #f59e0b); }
    .hi-status--error { color: var(--hi-error, #ef4444); }
    .hi-status--info { color: var(--hi-info, #3b82f6); }
    .hi-status--primary { color: var(--hi-primary, #3b82f6); }

    .hi-agenda-item__details {
      display: flex;
      flex-wrap: wrap;
      gap: var(--hi-space-3, 12px);
      margin-top: var(--hi-space-1, 4px);
    }

    .hi-detail {
      display: flex;
      align-items: center;
      gap: var(--hi-space-1, 4px);
      font-size: var(--hi-font-size-sm, 0.875rem);
      color: var(--hi-text-secondary, #6b7280);
    }

    .hi-detail i {
      font-size: 0.75rem;
    }

    .hi-agenda-item__action {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      background-color: var(--hi-success-bg, #ecfdf5);
      color: var(--hi-success, #10b981);
      border: none;
      border-radius: var(--hi-radius-full, 9999px);
      cursor: pointer;
      transition: all var(--hi-transition-fast, 150ms);
    }

    .hi-agenda-item__action:hover {
      background-color: var(--hi-success, #10b981);
      color: white;
    }

    /* Empty state */
    .hi-empty-agenda {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: var(--hi-space-8, 32px);
      color: var(--hi-text-muted, #9ca3af);
      text-align: center;
    }

    .hi-empty-agenda i {
      font-size: 2rem;
      margin-bottom: var(--hi-space-3, 12px);
    }

    .hi-empty-agenda p {
      margin: 0;
      font-size: var(--hi-font-size-sm, 0.875rem);
    }
  `;
  document.head.appendChild(styles);

  // Expõe globalmente
  global.HiTodayAgenda = HiTodayAgenda;

})(typeof window !== 'undefined' ? window : this);
