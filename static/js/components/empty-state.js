/**
 * HORÁRIO INTELIGENTE - Empty States
 * Componente para exibir estados vazios de forma amigável
 *
 * Uso:
 *   // Criar estado vazio
 *   const emptyState = HiEmptyState.create({
 *     icon: 'fa-calendar',
 *     title: 'Nenhum agendamento hoje',
 *     description: 'Aproveite para organizar sua agenda',
 *     action: {
 *       text: 'Novo Agendamento',
 *       onClick: () => { ... }
 *     }
 *   });
 *
 *   // Inserir no DOM
 *   document.getElementById('container').appendChild(emptyState);
 *
 *   // Ou usar os presets
 *   HiEmptyState.noAppointments(container);
 *   HiEmptyState.noPatients(container);
 *   HiEmptyState.noResults(container, 'paciente');
 */

(function(global) {
  'use strict';

  /**
   * Configurações de presets
   */
  const PRESETS = {
    noAppointments: {
      icon: 'fa-calendar-check',
      title: 'Nenhum agendamento',
      description: 'Sua agenda está livre. Que tal adicionar um novo agendamento?',
      actionText: 'Novo Agendamento',
      actionIcon: 'fa-plus'
    },
    noAppointmentsToday: {
      icon: 'fa-calendar-day',
      title: 'Nenhum agendamento hoje',
      description: 'Você não tem consultas agendadas para hoje.',
      actionText: 'Ver Calendário',
      actionIcon: 'fa-calendar'
    },
    noPatients: {
      icon: 'fa-users',
      title: 'Nenhum paciente cadastrado',
      description: 'Comece cadastrando seu primeiro paciente.',
      actionText: 'Cadastrar Paciente',
      actionIcon: 'fa-user-plus'
    },
    noResults: {
      icon: 'fa-search',
      title: 'Nenhum resultado encontrado',
      description: 'Tente ajustar os filtros ou termos de busca.',
      actionText: 'Limpar Filtros',
      actionIcon: 'fa-times'
    },
    noNotifications: {
      icon: 'fa-bell',
      title: 'Nenhuma notificação',
      description: 'Você está em dia! Sem novas notificações.',
      actionText: null
    },
    noMessages: {
      icon: 'fa-comments',
      title: 'Nenhuma mensagem',
      description: 'Sua caixa de entrada está vazia.',
      actionText: null
    },
    error: {
      icon: 'fa-exclamation-triangle',
      title: 'Algo deu errado',
      description: 'Não foi possível carregar os dados. Tente novamente.',
      actionText: 'Tentar Novamente',
      actionIcon: 'fa-redo'
    },
    offline: {
      icon: 'fa-wifi',
      title: 'Sem conexão',
      description: 'Verifique sua conexão com a internet e tente novamente.',
      actionText: 'Tentar Novamente',
      actionIcon: 'fa-redo'
    },
    loading: {
      icon: 'fa-spinner fa-spin',
      title: 'Carregando...',
      description: 'Aguarde enquanto buscamos os dados.',
      actionText: null
    },
    noData: {
      icon: 'fa-inbox',
      title: 'Sem dados',
      description: 'Não há dados para exibir no momento.',
      actionText: null
    },
    noFinancial: {
      icon: 'fa-chart-line',
      title: 'Sem dados financeiros',
      description: 'Registre consultas para visualizar relatórios financeiros.',
      actionText: 'Ver Agenda',
      actionIcon: 'fa-calendar'
    },
    noPendingConfirmations: {
      icon: 'fa-check-circle',
      title: 'Tudo confirmado!',
      description: 'Não há agendamentos pendentes de confirmação.',
      actionText: null
    },
    // Demo-specific presets
    demoWelcome: {
      icon: 'fa-rocket',
      title: 'Bem-vindo à Demo!',
      description: 'Este é um ambiente de demonstração. Explore as funcionalidades sem compromisso.',
      actionText: 'Iniciar Tour',
      actionIcon: 'fa-play'
    },
    demoAgendaEmpty: {
      icon: 'fa-calendar-plus',
      title: 'Agenda em branco',
      description: 'Na versão real, aqui aparecerão os agendamentos feitos via WhatsApp automaticamente.',
      actionText: 'Simular Agendamento',
      actionIcon: 'fa-magic'
    },
    demoPacientesEmpty: {
      icon: 'fa-user-plus',
      title: 'Cadastro de pacientes',
      description: 'Pacientes são cadastrados automaticamente ao agendar pelo WhatsApp.',
      actionText: 'Testar WhatsApp',
      actionIcon: 'fa-whatsapp'
    },
    demoRelatoriosEmpty: {
      icon: 'fa-chart-pie',
      title: 'Relatórios disponíveis',
      description: 'Conforme os agendamentos são realizados, gráficos e métricas aparecem aqui.',
      actionText: 'Ver Exemplos',
      actionIcon: 'fa-chart-bar'
    },
    noBlockedPeriods: {
      icon: 'fa-calendar-times',
      title: 'Nenhum bloqueio',
      description: 'Você não tem períodos bloqueados. Bloqueie férias, feriados ou congressos.',
      actionText: 'Bloquear Período',
      actionIcon: 'fa-ban'
    },
    successAgendamento: {
      icon: 'fa-check-circle',
      title: 'Agendamento confirmado!',
      description: 'O paciente receberá uma confirmação automática via WhatsApp.',
      actionText: 'Ver na Agenda',
      actionIcon: 'fa-calendar'
    },
    successCancellation: {
      icon: 'fa-times-circle',
      title: 'Agendamento cancelado',
      description: 'O horário foi liberado e o paciente foi notificado.',
      actionText: 'Ver Agenda',
      actionIcon: 'fa-calendar'
    },
    freeSlot: {
      icon: 'fa-clock',
      title: 'Horário disponível',
      description: 'Este horário está livre para agendamento.',
      actionText: 'Agendar Agora',
      actionIcon: 'fa-plus'
    },
    noReviews: {
      icon: 'fa-star',
      title: 'Sem avaliações',
      description: 'Pacientes poderão avaliar o atendimento após a consulta.',
      actionText: null
    },
    maintenance: {
      icon: 'fa-tools',
      title: 'Em manutenção',
      description: 'Esta funcionalidade está temporariamente indisponível. Tente novamente em breve.',
      actionText: 'Atualizar',
      actionIcon: 'fa-sync'
    },
    comingSoon: {
      icon: 'fa-clock',
      title: 'Em breve!',
      description: 'Esta funcionalidade está sendo desenvolvida e estará disponível em breve.',
      actionText: null
    }
  };

  /**
   * Cria o elemento HTML do empty state
   */
  function createElement(options) {
    const {
      icon = 'fa-inbox',
      title = 'Sem dados',
      description = '',
      action = null,
      size = 'md', // sm, md, lg
      className = ''
    } = options;

    const container = document.createElement('div');
    container.className = `hi-empty-state hi-empty-state--${size} ${className}`.trim();

    let html = `
      <div class="hi-empty-state__icon">
        <i class="fas ${icon}" aria-hidden="true"></i>
      </div>
      <h3 class="hi-empty-state__title">${escapeHtml(title)}</h3>
    `;

    if (description) {
      html += `<p class="hi-empty-state__description">${escapeHtml(description)}</p>`;
    }

    if (action && action.text) {
      const buttonIcon = action.icon ? `<i class="fas ${action.icon}" aria-hidden="true"></i>` : '';
      html += `
        <button type="button" class="hi-btn hi-btn--primary hi-empty-state__action">
          ${buttonIcon}
          ${escapeHtml(action.text)}
        </button>
      `;
    }

    container.innerHTML = html;

    // Adiciona evento ao botão se existir
    if (action && action.onClick) {
      const button = container.querySelector('.hi-empty-state__action');
      if (button) {
        button.addEventListener('click', action.onClick);
      }
    }

    return container;
  }

  /**
   * Escapa HTML para prevenir XSS
   */
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Renderiza empty state em um container
   */
  function renderInContainer(container, options) {
    if (typeof container === 'string') {
      container = document.querySelector(container);
    }

    if (!container) {
      console.error('Container não encontrado');
      return null;
    }

    const element = createElement(options);
    container.innerHTML = '';
    container.appendChild(element);
    return element;
  }

  /**
   * API pública
   */
  const HiEmptyState = {
    /**
     * Cria um elemento empty state
     * @param {object} options - Opções de configuração
     * @returns {HTMLElement}
     */
    create(options) {
      return createElement(options);
    },

    /**
     * Renderiza em um container
     * @param {string|HTMLElement} container - Container ou seletor
     * @param {object} options - Opções de configuração
     * @returns {HTMLElement}
     */
    render(container, options) {
      return renderInContainer(container, options);
    },

    /**
     * Usa um preset
     * @param {string} presetName - Nome do preset
     * @param {object} [overrides] - Sobrescreve opções do preset
     * @returns {HTMLElement}
     */
    preset(presetName, overrides = {}) {
      const preset = PRESETS[presetName];
      if (!preset) {
        console.warn(`Preset '${presetName}' não encontrado`);
        return createElement(overrides);
      }
      return createElement({ ...preset, ...overrides });
    },

    /**
     * Renderiza um preset em um container
     * @param {string|HTMLElement} container - Container ou seletor
     * @param {string} presetName - Nome do preset
     * @param {object} [overrides] - Sobrescreve opções do preset
     * @returns {HTMLElement}
     */
    renderPreset(container, presetName, overrides = {}) {
      const preset = PRESETS[presetName];
      if (!preset) {
        console.warn(`Preset '${presetName}' não encontrado`);
        return renderInContainer(container, overrides);
      }
      return renderInContainer(container, { ...preset, ...overrides });
    },

    // ===== Métodos de conveniência para presets comuns =====

    /**
     * Estado vazio: Nenhum agendamento
     */
    noAppointments(container, onAction) {
      return this.renderPreset(container, 'noAppointments', {
        action: onAction ? { text: PRESETS.noAppointments.actionText, icon: PRESETS.noAppointments.actionIcon, onClick: onAction } : null
      });
    },

    /**
     * Estado vazio: Nenhum agendamento hoje
     */
    noAppointmentsToday(container, onAction) {
      return this.renderPreset(container, 'noAppointmentsToday', {
        action: onAction ? { text: PRESETS.noAppointmentsToday.actionText, icon: PRESETS.noAppointmentsToday.actionIcon, onClick: onAction } : null
      });
    },

    /**
     * Estado vazio: Nenhum paciente
     */
    noPatients(container, onAction) {
      return this.renderPreset(container, 'noPatients', {
        action: onAction ? { text: PRESETS.noPatients.actionText, icon: PRESETS.noPatients.actionIcon, onClick: onAction } : null
      });
    },

    /**
     * Estado vazio: Nenhum resultado de busca
     */
    noResults(container, searchTerm, onClear) {
      const description = searchTerm
        ? `Nenhum resultado encontrado para "${searchTerm}". Tente ajustar os filtros.`
        : PRESETS.noResults.description;

      return this.renderPreset(container, 'noResults', {
        description,
        action: onClear ? { text: PRESETS.noResults.actionText, icon: PRESETS.noResults.actionIcon, onClick: onClear } : null
      });
    },

    /**
     * Estado de erro
     */
    error(container, message, onRetry) {
      return this.renderPreset(container, 'error', {
        description: message || PRESETS.error.description,
        action: onRetry ? { text: PRESETS.error.actionText, icon: PRESETS.error.actionIcon, onClick: onRetry } : null
      });
    },

    /**
     * Estado offline
     */
    offline(container, onRetry) {
      return this.renderPreset(container, 'offline', {
        action: onRetry ? { text: PRESETS.offline.actionText, icon: PRESETS.offline.actionIcon, onClick: onRetry } : null
      });
    },

    /**
     * Estado de carregamento
     */
    loading(container, message) {
      return this.renderPreset(container, 'loading', {
        title: message || PRESETS.loading.title
      });
    },

    /**
     * Estado genérico sem dados
     */
    noData(container, title, description) {
      return this.renderPreset(container, 'noData', {
        title: title || PRESETS.noData.title,
        description: description || PRESETS.noData.description
      });
    },

    /**
     * Adiciona um novo preset
     * @param {string} name - Nome do preset
     * @param {object} config - Configuração do preset
     */
    addPreset(name, config) {
      PRESETS[name] = config;
    },

    /**
     * Obtém a lista de presets disponíveis
     * @returns {string[]}
     */
    getPresetNames() {
      return Object.keys(PRESETS);
    }
  };

  // Expõe globalmente
  global.HiEmptyState = HiEmptyState;

  // Também expõe como módulo ES6 se suportado
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = HiEmptyState;
  }

})(typeof window !== 'undefined' ? window : this);
