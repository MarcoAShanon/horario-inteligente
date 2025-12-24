/**
 * HORÁRIO INTELIGENTE - Design System
 * Arquivo principal que inicializa todos os componentes
 *
 * Uso no HTML:
 *   <link rel="stylesheet" href="/static/css/design-system.css">
 *   <script src="/static/js/hi-design-system.js"></script>
 *
 * Depois de carregar:
 *   HI.toast.success('Sucesso!');
 *   HI.modal.confirm('Título', 'Mensagem');
 *   HI.validation.init('#form', { ... });
 *   HI.emptyState.noAppointments('#container');
 */

(function(global) {
  'use strict';

  // Carrega os componentes dinamicamente se ainda não estiverem disponíveis
  const componentsToLoad = [
    { name: 'HiToast', path: '/static/js/components/toast.js' },
    { name: 'HiModal', path: '/static/js/components/modal.js' },
    { name: 'HiEmptyState', path: '/static/js/components/empty-state.js' },
    { name: 'HiValidation', path: '/static/js/utils/validation.js' }
  ];

  /**
   * Carrega um script dinamicamente
   */
  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) {
        resolve();
        return;
      }

      const script = document.createElement('script');
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  /**
   * Inicializa funcionalidades globais
   */
  function initGlobalFeatures() {
    // Adiciona classe ao body para bottom nav
    if (window.innerWidth <= 768) {
      document.body.classList.add('has-bottom-nav');
    }

    window.addEventListener('resize', () => {
      if (window.innerWidth <= 768) {
        document.body.classList.add('has-bottom-nav');
      } else {
        document.body.classList.remove('has-bottom-nav');
      }
    });

    // Fecha dropdowns ao clicar fora
    document.addEventListener('click', (e) => {
      if (!e.target.closest('[data-dropdown]')) {
        document.querySelectorAll('[data-dropdown-content].hi-visible').forEach(el => {
          el.classList.remove('hi-visible');
        });
      }
    });

    // Inicializa tooltips
    initTooltips();

    // Inicializa detecção de conexão
    initConnectionDetection();
  }

  /**
   * Inicializa tooltips
   */
  function initTooltips() {
    document.querySelectorAll('[data-tooltip]').forEach(el => {
      el.addEventListener('mouseenter', showTooltip);
      el.addEventListener('mouseleave', hideTooltip);
      el.addEventListener('focus', showTooltip);
      el.addEventListener('blur', hideTooltip);
    });
  }

  let activeTooltip = null;

  function showTooltip(e) {
    const text = e.target.dataset.tooltip;
    if (!text) return;

    hideTooltip();

    const tooltip = document.createElement('div');
    tooltip.className = 'hi-tooltip hi-animate-fade-in';
    tooltip.textContent = text;
    tooltip.style.cssText = `
      position: fixed;
      background: var(--hi-gray-800, #1f2937);
      color: white;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      z-index: var(--hi-z-tooltip, 600);
      pointer-events: none;
      max-width: 200px;
      text-align: center;
    `;

    document.body.appendChild(tooltip);

    const rect = e.target.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();

    let top = rect.top - tooltipRect.height - 8;
    let left = rect.left + (rect.width - tooltipRect.width) / 2;

    // Ajusta se sair da tela
    if (top < 0) {
      top = rect.bottom + 8;
    }
    if (left < 8) {
      left = 8;
    }
    if (left + tooltipRect.width > window.innerWidth - 8) {
      left = window.innerWidth - tooltipRect.width - 8;
    }

    tooltip.style.top = `${top}px`;
    tooltip.style.left = `${left}px`;

    activeTooltip = tooltip;
  }

  function hideTooltip() {
    if (activeTooltip) {
      activeTooltip.remove();
      activeTooltip = null;
    }
  }

  /**
   * Detecta estado de conexão
   */
  function initConnectionDetection() {
    function updateOnlineStatus() {
      if (!navigator.onLine) {
        if (global.HiToast) {
          global.HiToast.warning('Sem conexão', 'Você está offline. Algumas funcionalidades podem não funcionar.');
        }
        document.body.classList.add('hi-offline');
      } else {
        document.body.classList.remove('hi-offline');
      }
    }

    window.addEventListener('online', () => {
      document.body.classList.remove('hi-offline');
      if (global.HiToast) {
        global.HiToast.success('Conexão restaurada');
      }
    });

    window.addEventListener('offline', updateOnlineStatus);

    // Verifica estado inicial
    if (!navigator.onLine) {
      document.body.classList.add('hi-offline');
    }
  }

  /**
   * Utilitários
   */
  const utils = {
    /**
     * Debounce
     */
    debounce(func, wait) {
      let timeout;
      return function executedFunction(...args) {
        const later = () => {
          clearTimeout(timeout);
          func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
      };
    },

    /**
     * Throttle
     */
    throttle(func, limit) {
      let inThrottle;
      return function(...args) {
        if (!inThrottle) {
          func.apply(this, args);
          inThrottle = true;
          setTimeout(() => inThrottle = false, limit);
        }
      };
    },

    /**
     * Formata data para exibição
     */
    formatDate(date, format = 'DD/MM/YYYY') {
      const d = new Date(date);
      const day = String(d.getDate()).padStart(2, '0');
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const year = d.getFullYear();
      const hours = String(d.getHours()).padStart(2, '0');
      const minutes = String(d.getMinutes()).padStart(2, '0');

      return format
        .replace('DD', day)
        .replace('MM', month)
        .replace('YYYY', year)
        .replace('HH', hours)
        .replace('mm', minutes);
    },

    /**
     * Formata moeda
     */
    formatCurrency(value) {
      return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
      }).format(value);
    },

    /**
     * Copia texto para clipboard
     */
    async copyToClipboard(text) {
      try {
        await navigator.clipboard.writeText(text);
        if (global.HiToast) {
          global.HiToast.success('Copiado!');
        }
        return true;
      } catch (err) {
        console.error('Falha ao copiar:', err);
        return false;
      }
    },

    /**
     * Scroll suave para elemento
     */
    scrollTo(element, offset = 0) {
      const el = typeof element === 'string' ? document.querySelector(element) : element;
      if (!el) return;

      const top = el.getBoundingClientRect().top + window.pageYOffset - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    },

    /**
     * Detecta se é mobile
     */
    isMobile() {
      return window.innerWidth <= 768;
    },

    /**
     * Gera ID único
     */
    generateId(prefix = 'hi') {
      return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
  };

  /**
   * API principal do Design System
   */
  const HI = {
    // Versão
    version: '1.0.0',

    // Referências aos componentes (preenchidas após carregamento)
    toast: null,
    modal: null,
    emptyState: null,
    validation: null,

    // Utilitários
    utils,

    /**
     * Inicializa o design system
     */
    async init() {
      // Carrega componentes
      for (const component of componentsToLoad) {
        if (!global[component.name]) {
          try {
            await loadScript(component.path);
          } catch (err) {
            console.warn(`Falha ao carregar ${component.name}:`, err);
          }
        }
      }

      // Mapeia referências
      this.toast = global.HiToast || null;
      this.modal = global.HiModal || null;
      this.emptyState = global.HiEmptyState || null;
      this.validation = global.HiValidation || null;

      // Inicializa features globais
      initGlobalFeatures();

      // Dispara evento de pronto
      document.dispatchEvent(new CustomEvent('hi:ready', { detail: this }));

      return this;
    },

    /**
     * Reinicializa tooltips (útil após carregar conteúdo dinâmico)
     */
    refreshTooltips() {
      initTooltips();
    },

    /**
     * Verifica se está online
     */
    isOnline() {
      return navigator.onLine;
    },

    /**
     * Adiciona loading overlay a um elemento
     */
    showLoading(element, message = 'Carregando...') {
      const el = typeof element === 'string' ? document.querySelector(element) : element;
      if (!el) return;

      el.style.position = 'relative';

      const overlay = document.createElement('div');
      overlay.className = 'hi-loading-overlay';
      overlay.innerHTML = `
        <div class="hi-flex hi-flex-col hi-items-center hi-gap-3">
          <div class="hi-spinner hi-spinner--lg"></div>
          <span class="hi-text-secondary">${message}</span>
        </div>
      `;
      overlay.dataset.hiLoading = 'true';

      el.appendChild(overlay);
      return overlay;
    },

    /**
     * Remove loading overlay
     */
    hideLoading(element) {
      const el = typeof element === 'string' ? document.querySelector(element) : element;
      if (!el) return;

      const overlay = el.querySelector('[data-hi-loading]');
      if (overlay) {
        overlay.remove();
      }
    },

    /**
     * Cria um skeleton loading
     */
    createSkeleton(type = 'text', count = 3) {
      const container = document.createElement('div');

      for (let i = 0; i < count; i++) {
        const skeleton = document.createElement('div');
        skeleton.className = `hi-skeleton hi-skeleton--${type}`;

        if (type === 'text') {
          skeleton.style.width = i === count - 1 ? '70%' : '100%';
          skeleton.style.height = '1em';
          skeleton.style.marginBottom = '0.5rem';
        } else if (type === 'card') {
          skeleton.style.height = '120px';
          skeleton.style.marginBottom = '1rem';
        } else if (type === 'circle') {
          skeleton.style.width = '48px';
          skeleton.style.height = '48px';
          skeleton.style.borderRadius = '50%';
        }

        container.appendChild(skeleton);
      }

      return container;
    }
  };

  // Expõe globalmente
  global.HI = HI;

  // Auto-inicializa quando o DOM estiver pronto
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => HI.init());
  } else {
    HI.init();
  }

})(typeof window !== 'undefined' ? window : this);
