/**
 * HORÁRIO INTELIGENTE - Atalhos Rápidos
 * Barra de ações rápidas para médicos/profissionais
 *
 * Uso:
 *   HiQuickActions.render('#actions-container', {
 *     onScheduleSettings: () => { ... },
 *     onBlockPeriod: () => { ... },
 *     onDashboard: () => { ... },
 *     onNewAppointment: () => { ... }
 *   });
 *
 *   // Ou usar atalhos padrão
 *   HiQuickActions.setupDefaults();
 */

(function(global) {
  'use strict';

  // Ações padrão
  const DEFAULT_ACTIONS = [
    {
      id: 'schedule-settings',
      label: 'Meus Horários',
      icon: 'fa-clock',
      color: '#3b82f6',
      description: 'Configurar dias e horários de atendimento'
    },
    {
      id: 'block-period',
      label: 'Bloquear Período',
      icon: 'fa-calendar-times',
      color: '#ef4444',
      description: 'Férias, feriados, congressos'
    },
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: 'fa-chart-line',
      color: '#10b981',
      description: 'Ver métricas e relatórios'
    },
    {
      id: 'new-appointment',
      label: 'Novo Agendamento',
      icon: 'fa-plus',
      color: '#8b5cf6',
      description: 'Agendar nova consulta',
      primary: true
    }
  ];

  let container = null;
  let currentOptions = {};

  /**
   * Cria HTML das ações
   */
  function createActionsHtml(actions, layout = 'horizontal') {
    const isVertical = layout === 'vertical';

    return `
      <div class="hi-quick-actions hi-quick-actions--${layout}">
        ${actions.map(action => `
          <button
            type="button"
            class="hi-quick-action ${action.primary ? 'hi-quick-action--primary' : ''}"
            data-action="${action.id}"
            style="--action-color: ${action.color}"
            aria-label="${action.description || action.label}"
            title="${action.description || action.label}"
          >
            <span class="hi-quick-action__icon">
              <i class="fas ${action.icon}" aria-hidden="true"></i>
            </span>
            <span class="hi-quick-action__label">${action.label}</span>
          </button>
        `).join('')}
      </div>
    `;
  }

  /**
   * Cria floating action button (FAB) para mobile
   */
  function createFAB(actions) {
    const primaryAction = actions.find(a => a.primary) || actions[0];
    const otherActions = actions.filter(a => a.id !== primaryAction.id);

    return `
      <div class="hi-fab-container">
        <div class="hi-fab-menu" id="fabMenu">
          ${otherActions.map(action => `
            <button
              type="button"
              class="hi-fab-item"
              data-action="${action.id}"
              style="--action-color: ${action.color}"
              aria-label="${action.label}"
            >
              <span class="hi-fab-item__tooltip">${action.label}</span>
              <i class="fas ${action.icon}" aria-hidden="true"></i>
            </button>
          `).join('')}
        </div>
        <button
          type="button"
          class="hi-fab hi-fab--primary"
          id="fabToggle"
          aria-label="Menu de ações"
          aria-expanded="false"
          style="--action-color: ${primaryAction.color}"
        >
          <i class="fas fa-plus hi-fab__icon--default" aria-hidden="true"></i>
          <i class="fas fa-times hi-fab__icon--close" aria-hidden="true"></i>
        </button>
      </div>
    `;
  }

  /**
   * Configura event listeners
   */
  function setupListeners() {
    if (!container) return;

    // Clique em ações
    container.addEventListener('click', (e) => {
      const actionBtn = e.target.closest('[data-action]');
      if (!actionBtn) return;

      const actionId = actionBtn.dataset.action;
      triggerAction(actionId);

      // Fecha FAB menu se estiver aberto
      const fabMenu = container.querySelector('#fabMenu');
      const fabToggle = container.querySelector('#fabToggle');
      if (fabMenu && fabToggle) {
        fabMenu.classList.remove('hi-fab-menu--open');
        fabToggle.setAttribute('aria-expanded', 'false');
      }
    });

    // Toggle FAB menu
    const fabToggle = container.querySelector('#fabToggle');
    if (fabToggle) {
      fabToggle.addEventListener('click', () => {
        const fabMenu = container.querySelector('#fabMenu');
        const isOpen = fabMenu.classList.toggle('hi-fab-menu--open');
        fabToggle.setAttribute('aria-expanded', isOpen.toString());
      });
    }
  }

  /**
   * Dispara ação
   */
  function triggerAction(actionId) {
    const handlers = {
      'schedule-settings': () => {
        if (typeof currentOptions.onScheduleSettings === 'function') {
          currentOptions.onScheduleSettings();
        } else if (typeof HiScheduleSettings !== 'undefined') {
          HiScheduleSettings.show({
            onSave: async (config) => {
              console.log('Configurações salvas:', config);
              // Aqui você pode fazer a chamada à API
            }
          });
        }
      },
      'block-period': () => {
        if (typeof currentOptions.onBlockPeriod === 'function') {
          currentOptions.onBlockPeriod();
        } else if (typeof HiBlockPeriod !== 'undefined') {
          HiBlockPeriod.show({
            onSave: async (bloqueio) => {
              console.log('Bloqueio criado:', bloqueio);
              // Aqui você pode fazer a chamada à API
            }
          });
        }
      },
      'dashboard': () => {
        if (typeof currentOptions.onDashboard === 'function') {
          currentOptions.onDashboard();
        } else {
          window.location.href = '/static/dashboard.html';
        }
      },
      'new-appointment': () => {
        if (typeof currentOptions.onNewAppointment === 'function') {
          currentOptions.onNewAppointment();
        }
      }
    };

    const handler = handlers[actionId];
    if (handler) {
      handler();
    }

    // Dispara evento customizado
    document.dispatchEvent(new CustomEvent('hi:quick-action', {
      detail: { actionId }
    }));
  }

  /**
   * API pública
   */
  const HiQuickActions = {
    /**
     * Renderiza barra de ações
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
      const {
        actions = DEFAULT_ACTIONS,
        layout = 'horizontal', // horizontal, vertical, fab
        showOnMobile = true
      } = options;

      if (layout === 'fab') {
        container.innerHTML = createFAB(actions);
      } else {
        container.innerHTML = createActionsHtml(actions, layout);
      }

      setupListeners();
    },

    /**
     * Configura atalhos padrão (adiciona FAB no mobile)
     */
    setupDefaults(options = {}) {
      currentOptions = options;

      // Cria container para FAB se não existir
      let fabContainer = document.querySelector('.hi-quick-actions-fab');
      if (!fabContainer) {
        fabContainer = document.createElement('div');
        fabContainer.className = 'hi-quick-actions-fab';
        document.body.appendChild(fabContainer);
      }

      container = fabContainer;
      container.innerHTML = createFAB(DEFAULT_ACTIONS);
      setupListeners();
    },

    /**
     * Obtém ações padrão
     */
    getDefaultActions() {
      return [...DEFAULT_ACTIONS];
    },

    /**
     * Dispara uma ação manualmente
     */
    trigger(actionId) {
      triggerAction(actionId);
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
    /* Barra horizontal */
    .hi-quick-actions--horizontal {
      display: flex;
      flex-wrap: wrap;
      gap: var(--hi-space-3, 12px);
    }

    .hi-quick-actions--vertical {
      display: flex;
      flex-direction: column;
      gap: var(--hi-space-2, 8px);
    }

    .hi-quick-action {
      display: flex;
      align-items: center;
      gap: var(--hi-space-3, 12px);
      padding: var(--hi-space-3, 12px) var(--hi-space-4, 16px);
      background-color: white;
      border: 2px solid var(--hi-border-light, #e5e7eb);
      border-radius: var(--hi-radius-lg, 12px);
      cursor: pointer;
      transition: all var(--hi-transition-fast, 150ms);
      font-family: inherit;
      font-size: var(--hi-font-size-sm, 0.875rem);
      font-weight: var(--hi-font-weight-medium, 500);
      color: var(--hi-text-primary, #1f2937);
      text-align: left;
      min-height: var(--hi-touch-target-min, 44px);
    }

    .hi-quick-action:hover {
      border-color: var(--action-color, var(--hi-primary));
      background-color: color-mix(in srgb, var(--action-color) 5%, white);
    }

    .hi-quick-action:focus-visible {
      outline: 2px solid var(--action-color, var(--hi-primary));
      outline-offset: 2px;
    }

    .hi-quick-action--primary {
      background-color: var(--action-color, var(--hi-primary));
      border-color: var(--action-color, var(--hi-primary));
      color: white;
    }

    .hi-quick-action--primary:hover {
      background-color: color-mix(in srgb, var(--action-color) 90%, black);
      border-color: color-mix(in srgb, var(--action-color) 90%, black);
    }

    .hi-quick-action__icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      background-color: color-mix(in srgb, var(--action-color) 10%, white);
      border-radius: var(--hi-radius-md, 8px);
      color: var(--action-color);
      font-size: 0.875rem;
    }

    .hi-quick-action--primary .hi-quick-action__icon {
      background-color: rgba(255, 255, 255, 0.2);
      color: white;
    }

    .hi-quick-action__label {
      white-space: nowrap;
    }

    /* FAB - Floating Action Button */
    .hi-quick-actions-fab {
      position: fixed;
      bottom: var(--hi-space-6, 24px);
      right: var(--hi-space-6, 24px);
      z-index: var(--hi-z-sticky, 200);
    }

    @media (max-width: 768px) {
      .hi-quick-actions-fab {
        bottom: calc(var(--hi-space-6, 24px) + 70px); /* Above bottom nav */
      }
    }

    .hi-fab-container {
      position: relative;
    }

    .hi-fab {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 56px;
      height: 56px;
      background: linear-gradient(135deg, var(--action-color), color-mix(in srgb, var(--action-color) 80%, black));
      border: none;
      border-radius: 50%;
      color: white;
      font-size: 1.25rem;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      transition: all var(--hi-transition-fast, 150ms);
    }

    .hi-fab:hover {
      transform: scale(1.05);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
    }

    .hi-fab:focus-visible {
      outline: 2px solid white;
      outline-offset: 2px;
    }

    .hi-fab__icon--close {
      display: none;
    }

    .hi-fab[aria-expanded="true"] .hi-fab__icon--default {
      display: none;
    }

    .hi-fab[aria-expanded="true"] .hi-fab__icon--close {
      display: block;
    }

    .hi-fab[aria-expanded="true"] {
      transform: rotate(45deg);
    }

    /* FAB Menu */
    .hi-fab-menu {
      position: absolute;
      bottom: 64px;
      right: 4px;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: var(--hi-space-3, 12px);
      opacity: 0;
      visibility: hidden;
      transform: translateY(10px);
      transition: all var(--hi-transition-fast, 150ms);
    }

    .hi-fab-menu--open {
      opacity: 1;
      visibility: visible;
      transform: translateY(0);
    }

    .hi-fab-item {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      background-color: white;
      border: none;
      border-radius: 50%;
      color: var(--action-color, var(--hi-primary));
      font-size: 1rem;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      transition: all var(--hi-transition-fast, 150ms);
      position: relative;
    }

    .hi-fab-item:hover {
      transform: scale(1.1);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }

    .hi-fab-item__tooltip {
      position: absolute;
      right: 56px;
      background-color: var(--hi-gray-800, #1f2937);
      color: white;
      padding: var(--hi-space-2, 8px) var(--hi-space-3, 12px);
      border-radius: var(--hi-radius-md, 8px);
      font-size: var(--hi-font-size-sm, 0.875rem);
      font-weight: var(--hi-font-weight-medium, 500);
      white-space: nowrap;
      opacity: 0;
      visibility: hidden;
      transition: all var(--hi-transition-fast, 150ms);
      pointer-events: none;
    }

    .hi-fab-item:hover .hi-fab-item__tooltip {
      opacity: 1;
      visibility: visible;
    }

    /* Animação de entrada dos itens */
    .hi-fab-menu--open .hi-fab-item:nth-child(1) { transition-delay: 0ms; }
    .hi-fab-menu--open .hi-fab-item:nth-child(2) { transition-delay: 50ms; }
    .hi-fab-menu--open .hi-fab-item:nth-child(3) { transition-delay: 100ms; }
    .hi-fab-menu--open .hi-fab-item:nth-child(4) { transition-delay: 150ms; }

    /* Responsivo */
    @media (max-width: 640px) {
      .hi-quick-actions--horizontal {
        flex-direction: column;
      }

      .hi-quick-action {
        width: 100%;
      }
    }
  `;
  document.head.appendChild(styles);

  // Expõe globalmente
  global.HiQuickActions = HiQuickActions;

})(typeof window !== 'undefined' ? window : this);
