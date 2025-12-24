/**
 * HORÁRIO INTELIGENTE - Toast Notifications
 * Sistema de notificações visuais para feedback do usuário
 *
 * Uso:
 *   HiToast.success('Agendamento confirmado!');
 *   HiToast.error('Erro ao salvar', 'Tente novamente mais tarde');
 *   HiToast.warning('Atenção', 'Horário quase esgotado');
 *   HiToast.info('Dica', 'Você pode arrastar os eventos');
 */

(function(global) {
  'use strict';

  // Configurações padrão
  const DEFAULT_OPTIONS = {
    duration: 4000,        // Duração em ms (0 = não fecha automaticamente)
    position: 'top-right', // top-right, top-left, bottom-right, bottom-left
    maxToasts: 5,          // Máximo de toasts simultâneos
    pauseOnHover: true,    // Pausa o timer ao passar o mouse
  };

  // Ícones por tipo
  const ICONS = {
    success: '<i class="fas fa-check-circle" aria-hidden="true"></i>',
    error: '<i class="fas fa-times-circle" aria-hidden="true"></i>',
    warning: '<i class="fas fa-exclamation-triangle" aria-hidden="true"></i>',
    info: '<i class="fas fa-info-circle" aria-hidden="true"></i>',
  };

  // Container dos toasts
  let container = null;
  let toastQueue = [];
  let activeToasts = [];

  /**
   * Cria o container de toasts se não existir
   */
  function ensureContainer() {
    if (container && document.body.contains(container)) {
      return container;
    }

    container = document.createElement('div');
    container.className = 'hi-toast-container';
    container.setAttribute('role', 'alert');
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-atomic', 'true');
    document.body.appendChild(container);

    return container;
  }

  /**
   * Cria um elemento toast
   */
  function createToastElement(type, title, message, options) {
    const toast = document.createElement('div');
    toast.className = `hi-toast hi-toast--${type}`;
    toast.setAttribute('role', 'alert');

    const icon = ICONS[type] || ICONS.info;

    let html = `
      <div class="hi-toast__icon">${icon}</div>
      <div class="hi-toast__content">
    `;

    if (title) {
      html += `<div class="hi-toast__title">${escapeHtml(title)}</div>`;
    }

    if (message) {
      html += `<div class="hi-toast__message">${escapeHtml(message)}</div>`;
    }

    html += `
      </div>
      <button type="button" class="hi-toast__close" aria-label="Fechar notificação">
        <i class="fas fa-times" aria-hidden="true"></i>
      </button>
    `;

    toast.innerHTML = html;

    return toast;
  }

  /**
   * Escapa HTML para prevenir XSS
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Remove um toast com animação
   */
  function removeToast(toast, toastData) {
    if (toastData.removed) return;
    toastData.removed = true;

    // Limpa o timer
    if (toastData.timerId) {
      clearTimeout(toastData.timerId);
    }

    // Adiciona classe de saída
    toast.classList.add('hi-toast--exiting');

    // Remove após animação
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }

      // Remove da lista de ativos
      const index = activeToasts.indexOf(toastData);
      if (index > -1) {
        activeToasts.splice(index, 1);
      }

      // Processa fila se houver
      processQueue();
    }, 300);
  }

  /**
   * Processa a fila de toasts
   */
  function processQueue() {
    while (toastQueue.length > 0 && activeToasts.length < DEFAULT_OPTIONS.maxToasts) {
      const next = toastQueue.shift();
      showToastInternal(next.type, next.title, next.message, next.options);
    }
  }

  /**
   * Mostra um toast internamente
   */
  function showToastInternal(type, title, message, options) {
    const mergedOptions = { ...DEFAULT_OPTIONS, ...options };
    const container = ensureContainer();
    const toast = createToastElement(type, title, message, mergedOptions);

    const toastData = {
      element: toast,
      options: mergedOptions,
      removed: false,
      timerId: null,
      remainingTime: mergedOptions.duration,
      pausedAt: null,
    };

    // Adiciona ao container
    container.appendChild(toast);
    activeToasts.push(toastData);

    // Configura o botão de fechar
    const closeBtn = toast.querySelector('.hi-toast__close');
    closeBtn.addEventListener('click', () => removeToast(toast, toastData));

    // Configura auto-close
    if (mergedOptions.duration > 0) {
      toastData.startTime = Date.now();
      toastData.timerId = setTimeout(() => {
        removeToast(toast, toastData);
      }, mergedOptions.duration);

      // Pausa ao passar o mouse
      if (mergedOptions.pauseOnHover) {
        toast.addEventListener('mouseenter', () => {
          if (toastData.timerId) {
            clearTimeout(toastData.timerId);
            toastData.remainingTime -= (Date.now() - toastData.startTime);
          }
        });

        toast.addEventListener('mouseleave', () => {
          if (!toastData.removed && toastData.remainingTime > 0) {
            toastData.startTime = Date.now();
            toastData.timerId = setTimeout(() => {
              removeToast(toast, toastData);
            }, toastData.remainingTime);
          }
        });
      }
    }

    // Permite fechar com ESC quando focado
    toast.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        removeToast(toast, toastData);
      }
    });

    // Torna focável para acessibilidade
    toast.setAttribute('tabindex', '0');

    return toast;
  }

  /**
   * Mostra um toast
   */
  function show(type, title, message, options = {}) {
    // Se atingiu o máximo, adiciona à fila
    if (activeToasts.length >= DEFAULT_OPTIONS.maxToasts) {
      toastQueue.push({ type, title, message, options });
      return;
    }

    return showToastInternal(type, title, message, options);
  }

  /**
   * API pública
   */
  const HiToast = {
    /**
     * Toast de sucesso
     * @param {string} title - Título ou mensagem principal
     * @param {string} [message] - Mensagem secundária (opcional)
     * @param {object} [options] - Opções adicionais
     */
    success(title, message, options) {
      return show('success', title, message, options);
    },

    /**
     * Toast de erro
     * @param {string} title - Título ou mensagem principal
     * @param {string} [message] - Mensagem secundária (opcional)
     * @param {object} [options] - Opções adicionais
     */
    error(title, message, options) {
      // Erros ficam mais tempo na tela por padrão
      return show('error', title, message, { duration: 6000, ...options });
    },

    /**
     * Toast de aviso
     * @param {string} title - Título ou mensagem principal
     * @param {string} [message] - Mensagem secundária (opcional)
     * @param {object} [options] - Opções adicionais
     */
    warning(title, message, options) {
      return show('warning', title, message, { duration: 5000, ...options });
    },

    /**
     * Toast de informação
     * @param {string} title - Título ou mensagem principal
     * @param {string} [message] - Mensagem secundária (opcional)
     * @param {object} [options] - Opções adicionais
     */
    info(title, message, options) {
      return show('info', title, message, options);
    },

    /**
     * Toast personalizado
     * @param {string} type - Tipo: success, error, warning, info
     * @param {string} title - Título
     * @param {string} [message] - Mensagem
     * @param {object} [options] - Opções
     */
    show(type, title, message, options) {
      return show(type, title, message, options);
    },

    /**
     * Remove todos os toasts ativos
     */
    clearAll() {
      toastQueue = [];
      [...activeToasts].forEach(toastData => {
        removeToast(toastData.element, toastData);
      });
    },

    /**
     * Configura opções globais
     * @param {object} options - Novas opções padrão
     */
    configure(options) {
      Object.assign(DEFAULT_OPTIONS, options);
    }
  };

  // Expõe globalmente
  global.HiToast = HiToast;

  // Também expõe como módulo ES6 se suportado
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = HiToast;
  }

})(typeof window !== 'undefined' ? window : this);
