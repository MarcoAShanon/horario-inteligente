/**
 * HORÁRIO INTELIGENTE - Bottom Navigation
 * Barra de navegação inferior para dispositivos móveis
 *
 * Uso:
 *   HiBottomNav.init({
 *     items: [
 *       { id: 'agenda', label: 'Agenda', icon: 'fa-calendar', href: '/static/calendario-unificado.html' },
 *       { id: 'config', label: 'Horários', icon: 'fa-clock', href: '/static/configuracao-agenda.html' },
 *       { id: 'novo', label: 'Novo', icon: 'fa-plus', primary: true, onClick: () => {} },
 *       { id: 'dashboard', label: 'Dashboard', icon: 'fa-chart-line', href: '/static/dashboard.html' },
 *       { id: 'perfil', label: 'Perfil', icon: 'fa-user', href: '/static/perfil.html' }
 *     ],
 *     activeId: 'agenda'
 *   });
 */

(function(global) {
  'use strict';

  let navElement = null;
  let currentOptions = {};
  let isVisible = true;
  let lastScrollY = 0;
  let hideOnScroll = false;

  // Configuração padrão para médicos
  const DEFAULT_ITEMS = [
    {
      id: 'agenda',
      label: 'Agenda',
      icon: 'fa-calendar-alt',
      href: '/static/calendario-unificado.html'
    },
    {
      id: 'config',
      label: 'Horários',
      icon: 'fa-clock',
      onClick: () => {
        if (typeof HiScheduleSettings !== 'undefined') {
          HiScheduleSettings.show({});
        } else {
          window.location.href = '/static/configuracao-agenda.html';
        }
      }
    },
    {
      id: 'novo',
      label: 'Novo',
      icon: 'fa-plus',
      primary: true,
      onClick: () => {
        // Dispara evento customizado
        document.dispatchEvent(new CustomEvent('hi:new-appointment'));
      }
    },
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: 'fa-chart-line',
      href: '/static/dashboard.html'
    },
    {
      id: 'perfil',
      label: 'Perfil',
      icon: 'fa-user',
      href: '/static/perfil.html'
    }
  ];

  /**
   * Detecta a página atual
   */
  function detectCurrentPage() {
    const path = window.location.pathname;

    if (path.includes('calendario') || path.includes('agenda')) return 'agenda';
    if (path.includes('configuracao')) return 'config';
    if (path.includes('dashboard')) return 'dashboard';
    if (path.includes('perfil')) return 'perfil';

    return 'agenda'; // default
  }

  /**
   * Cria o HTML da navegação
   */
  function createNavHtml(items, activeId) {
    return `
      <nav class="hi-bottom-nav" role="navigation" aria-label="Navegação principal">
        ${items.map(item => {
          const isActive = item.id === activeId;
          const isPrimary = item.primary;

          return `
            <${item.href ? 'a' : 'button'}
              ${item.href ? `href="${item.href}"` : 'type="button"'}
              class="hi-bottom-nav__item ${isActive ? 'hi-bottom-nav__item--active' : ''} ${isPrimary ? 'hi-bottom-nav__item--primary' : ''}"
              data-nav-id="${item.id}"
              ${isActive ? 'aria-current="page"' : ''}
              aria-label="${item.label}"
            >
              <span class="hi-bottom-nav__icon">
                <i class="fas ${item.icon}" aria-hidden="true"></i>
              </span>
              <span class="hi-bottom-nav__label">${item.label}</span>
              ${item.badge ? `<span class="hi-bottom-nav__badge">${item.badge}</span>` : ''}
            </${item.href ? 'a' : 'button'}>
          `;
        }).join('')}
      </nav>
    `;
  }

  /**
   * Configura event listeners
   */
  function setupListeners() {
    if (!navElement) return;

    // Click handlers
    navElement.addEventListener('click', (e) => {
      const item = e.target.closest('.hi-bottom-nav__item');
      if (!item) return;

      const navId = item.dataset.navId;
      const itemConfig = currentOptions.items.find(i => i.id === navId);

      if (itemConfig && typeof itemConfig.onClick === 'function') {
        e.preventDefault();
        itemConfig.onClick(itemConfig);
      }

      // Feedback tátil (se suportado)
      if (navigator.vibrate) {
        navigator.vibrate(10);
      }
    });

    // Esconder ao rolar (opcional)
    if (hideOnScroll) {
      let ticking = false;

      window.addEventListener('scroll', () => {
        if (!ticking) {
          window.requestAnimationFrame(() => {
            handleScroll();
            ticking = false;
          });
          ticking = true;
        }
      }, { passive: true });
    }
  }

  /**
   * Lida com scroll para esconder/mostrar nav
   */
  function handleScroll() {
    const currentScrollY = window.scrollY;
    const scrollDiff = currentScrollY - lastScrollY;

    // Só age se rolou mais de 10px
    if (Math.abs(scrollDiff) < 10) return;

    if (scrollDiff > 0 && isVisible && currentScrollY > 100) {
      // Rolando para baixo - esconde
      hide();
    } else if (scrollDiff < 0 && !isVisible) {
      // Rolando para cima - mostra
      show();
    }

    lastScrollY = currentScrollY;
  }

  /**
   * Mostra a navegação
   */
  function show() {
    if (navElement) {
      navElement.classList.remove('hi-bottom-nav--hidden');
      isVisible = true;
    }
  }

  /**
   * Esconde a navegação
   */
  function hide() {
    if (navElement) {
      navElement.classList.add('hi-bottom-nav--hidden');
      isVisible = false;
    }
  }

  /**
   * Atualiza badge de um item
   */
  function updateBadge(itemId, count) {
    if (!navElement) return;

    const item = navElement.querySelector(`[data-nav-id="${itemId}"]`);
    if (!item) return;

    let badge = item.querySelector('.hi-bottom-nav__badge');

    if (count > 0) {
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'hi-bottom-nav__badge';
        item.querySelector('.hi-bottom-nav__icon').appendChild(badge);
      }
      badge.textContent = count > 99 ? '99+' : count;
    } else if (badge) {
      badge.remove();
    }
  }

  /**
   * API pública
   */
  const HiBottomNav = {
    /**
     * Inicializa a navegação
     */
    init(options = {}) {
      // Remove navegação existente se houver
      this.destroy();

      const {
        items = DEFAULT_ITEMS,
        activeId = detectCurrentPage(),
        container = document.body,
        hideOnScrollEnabled = false
      } = options;

      currentOptions = { items, activeId };
      hideOnScroll = hideOnScrollEnabled;

      // Cria o elemento
      const wrapper = document.createElement('div');
      wrapper.innerHTML = createNavHtml(items, activeId);
      navElement = wrapper.firstElementChild;

      // Adiciona ao DOM
      const containerEl = typeof container === 'string'
        ? document.querySelector(container)
        : container;

      containerEl.appendChild(navElement);

      // Adiciona classe ao body para padding
      document.body.classList.add('hi-has-bottom-nav');

      // Configura listeners
      setupListeners();

      return this;
    },

    /**
     * Usa configuração padrão para médicos
     */
    initDefault(activeId) {
      return this.init({
        items: DEFAULT_ITEMS,
        activeId: activeId || detectCurrentPage()
      });
    },

    /**
     * Atualiza o item ativo
     */
    setActive(itemId) {
      if (!navElement) return;

      navElement.querySelectorAll('.hi-bottom-nav__item').forEach(item => {
        const isActive = item.dataset.navId === itemId;
        item.classList.toggle('hi-bottom-nav__item--active', isActive);
        item.setAttribute('aria-current', isActive ? 'page' : '');
      });

      currentOptions.activeId = itemId;
    },

    /**
     * Atualiza badge
     */
    setBadge(itemId, count) {
      updateBadge(itemId, count);
    },

    /**
     * Mostra a navegação
     */
    show() {
      show();
    },

    /**
     * Esconde a navegação
     */
    hide() {
      hide();
    },

    /**
     * Verifica se está visível
     */
    isVisible() {
      return isVisible;
    },

    /**
     * Destrói a navegação
     */
    destroy() {
      if (navElement && navElement.parentNode) {
        navElement.parentNode.removeChild(navElement);
      }
      navElement = null;
      document.body.classList.remove('hi-has-bottom-nav');
    },

    /**
     * Obtém itens padrão
     */
    getDefaultItems() {
      return [...DEFAULT_ITEMS];
    }
  };

  // Estilos do componente
  const styles = document.createElement('style');
  styles.textContent = `
    /* Bottom Navigation */
    .hi-bottom-nav {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      display: flex;
      align-items: stretch;
      background-color: var(--hi-bg-primary, #ffffff);
      border-top: 1px solid var(--hi-border-light, #e5e7eb);
      box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.08);
      z-index: var(--hi-z-sticky, 200);
      padding-bottom: env(safe-area-inset-bottom, 0);
      transition: transform var(--hi-transition-normal, 200ms);
    }

    .hi-bottom-nav--hidden {
      transform: translateY(100%);
    }

    /* Só mostra em mobile/tablet */
    @media (min-width: 1024px) {
      .hi-bottom-nav {
        display: none;
      }

      .hi-has-bottom-nav {
        padding-bottom: 0 !important;
      }
    }

    /* Padding no body */
    .hi-has-bottom-nav {
      padding-bottom: calc(64px + env(safe-area-inset-bottom, 0));
    }

    /* Item da navegação */
    .hi-bottom-nav__item {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 2px;
      min-height: 64px;
      padding: 8px 4px;
      background: none;
      border: none;
      color: var(--hi-text-muted, #9ca3af);
      text-decoration: none;
      cursor: pointer;
      transition: all var(--hi-transition-fast, 150ms);
      position: relative;
      -webkit-tap-highlight-color: transparent;
    }

    .hi-bottom-nav__item:hover {
      color: var(--hi-text-secondary, #6b7280);
    }

    .hi-bottom-nav__item--active {
      color: var(--hi-primary, #3b82f6);
    }

    .hi-bottom-nav__item:focus-visible {
      outline: none;
      background-color: var(--hi-gray-100, #f3f4f6);
    }

    /* Ícone */
    .hi-bottom-nav__icon {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      font-size: 1.25rem;
    }

    .hi-bottom-nav__item--active .hi-bottom-nav__icon {
      transform: scale(1.1);
    }

    /* Label */
    .hi-bottom-nav__label {
      font-size: 0.625rem;
      font-weight: var(--hi-font-weight-medium, 500);
      text-transform: uppercase;
      letter-spacing: 0.02em;
      line-height: 1;
    }

    /* Badge */
    .hi-bottom-nav__badge {
      position: absolute;
      top: -4px;
      right: -8px;
      min-width: 18px;
      height: 18px;
      padding: 0 5px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: var(--hi-error, #ef4444);
      color: white;
      font-size: 0.625rem;
      font-weight: var(--hi-font-weight-bold, 700);
      border-radius: 9px;
      line-height: 1;
    }

    /* Item primário (central) */
    .hi-bottom-nav__item--primary {
      position: relative;
    }

    .hi-bottom-nav__item--primary .hi-bottom-nav__icon {
      width: 48px;
      height: 48px;
      margin-top: -16px;
      background: linear-gradient(135deg, var(--hi-primary, #3b82f6), var(--hi-primary-dark, #2563eb));
      border-radius: 50%;
      color: white;
      font-size: 1.25rem;
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
      transition: all var(--hi-transition-fast, 150ms);
    }

    .hi-bottom-nav__item--primary:hover .hi-bottom-nav__icon,
    .hi-bottom-nav__item--primary:active .hi-bottom-nav__icon {
      transform: scale(1.1);
      box-shadow: 0 6px 16px rgba(59, 130, 246, 0.5);
    }

    .hi-bottom-nav__item--primary .hi-bottom-nav__label {
      color: var(--hi-primary, #3b82f6);
    }

    /* Indicador de página ativa */
    .hi-bottom-nav__item--active::before {
      content: '';
      position: absolute;
      top: 0;
      left: 50%;
      transform: translateX(-50%);
      width: 32px;
      height: 3px;
      background-color: var(--hi-primary, #3b82f6);
      border-radius: 0 0 3px 3px;
    }

    .hi-bottom-nav__item--primary::before {
      display: none;
    }

    /* Ripple effect */
    .hi-bottom-nav__item::after {
      content: '';
      position: absolute;
      inset: 0;
      background: radial-gradient(circle at center, var(--hi-primary-100, #dbeafe) 0%, transparent 70%);
      opacity: 0;
      transition: opacity var(--hi-transition-fast, 150ms);
      pointer-events: none;
    }

    .hi-bottom-nav__item:active::after {
      opacity: 1;
    }

    /* Landscape mode adjustments */
    @media (max-height: 500px) and (orientation: landscape) {
      .hi-bottom-nav {
        flex-direction: row;
      }

      .hi-bottom-nav__item {
        min-height: 48px;
        flex-direction: row;
        gap: 8px;
      }

      .hi-bottom-nav__item--primary .hi-bottom-nav__icon {
        margin-top: 0;
        width: 40px;
        height: 40px;
      }

      .hi-has-bottom-nav {
        padding-bottom: 48px;
      }
    }

    /* Modo escuro (futuro) */
    @media (prefers-color-scheme: dark) {
      .hi-bottom-nav {
        background-color: var(--hi-gray-900, #111827);
        border-top-color: var(--hi-gray-800, #1f2937);
      }

      .hi-bottom-nav__item:focus-visible {
        background-color: var(--hi-gray-800, #1f2937);
      }
    }
  `;
  document.head.appendChild(styles);

  // Expõe globalmente
  global.HiBottomNav = HiBottomNav;

  // Auto-inicializa em mobile se configurado
  if (typeof window !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
      // Verifica se há um atributo data-hi-bottom-nav no body
      if (document.body.hasAttribute('data-hi-bottom-nav')) {
        HiBottomNav.initDefault();
      }
    });
  }

})(typeof window !== 'undefined' ? window : this);
