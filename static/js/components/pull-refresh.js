/**
 * HORÁRIO INTELIGENTE - Pull to Refresh
 * Componente para atualização via gesto de puxar
 *
 * Uso:
 *   HiPullRefresh.init({
 *     container: '#main-content',
 *     onRefresh: async () => {
 *       await fetchNewData();
 *     }
 *   });
 */

(function(global) {
  'use strict';

  // Estado
  let instance = null;
  let isInitialized = false;

  // Configurações padrão
  const DEFAULTS = {
    threshold: 80,        // Distância para ativar refresh
    maxPull: 120,         // Distância máxima de pull
    resistance: 0.4,      // Resistência ao pull
    refreshTimeout: 10000 // Timeout do refresh em ms
  };

  /**
   * Classe principal
   */
  class PullRefreshHandler {
    constructor(options = {}) {
      this.options = { ...DEFAULTS, ...options };

      this.container = typeof options.container === 'string'
        ? document.querySelector(options.container)
        : options.container || document.body;

      this.startY = 0;
      this.currentY = 0;
      this.isPulling = false;
      this.isRefreshing = false;
      this.canPull = false;

      this.init();
    }

    init() {
      this.createIndicator();
      this.attachEvents();
    }

    createIndicator() {
      // Remove indicador existente
      const existing = document.querySelector('.hi-pull-refresh');
      if (existing) existing.remove();

      // Cria indicador
      this.indicator = document.createElement('div');
      this.indicator.className = 'hi-pull-refresh';
      this.indicator.innerHTML = `
        <div class="hi-pull-refresh__content">
          <div class="hi-pull-refresh__icon">
            <svg class="hi-pull-refresh__arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="7 13 12 18 17 13"></polyline>
              <polyline points="7 6 12 11 17 6"></polyline>
            </svg>
            <svg class="hi-pull-refresh__spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12a9 9 0 11-6.219-8.56"></path>
            </svg>
            <svg class="hi-pull-refresh__check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
          <span class="hi-pull-refresh__text">Puxe para atualizar</span>
        </div>
      `;

      // Insere no topo do container ou body
      if (this.container === document.body) {
        document.body.insertBefore(this.indicator, document.body.firstChild);
      } else {
        this.container.insertBefore(this.indicator, this.container.firstChild);
      }

      this.arrow = this.indicator.querySelector('.hi-pull-refresh__arrow');
      this.spinner = this.indicator.querySelector('.hi-pull-refresh__spinner');
      this.check = this.indicator.querySelector('.hi-pull-refresh__check');
      this.text = this.indicator.querySelector('.hi-pull-refresh__text');
    }

    attachEvents() {
      // Touch events
      this.container.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
      this.container.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
      this.container.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });
    }

    handleTouchStart(e) {
      if (this.isRefreshing) return;

      // Só permite pull se estiver no topo
      const scrollTop = window.scrollY || document.documentElement.scrollTop;
      this.canPull = scrollTop <= 0;

      if (this.canPull) {
        this.startY = e.touches[0].clientY;
        this.isPulling = false;
      }
    }

    handleTouchMove(e) {
      if (!this.canPull || this.isRefreshing) return;

      const currentY = e.touches[0].clientY;
      const deltaY = currentY - this.startY;

      // Só processa se estiver puxando para baixo
      if (deltaY <= 0) {
        this.currentY = 0;
        this.updateIndicator(0);
        return;
      }

      // Verifica se ainda está no topo
      const scrollTop = window.scrollY || document.documentElement.scrollTop;
      if (scrollTop > 0) {
        this.canPull = false;
        return;
      }

      e.preventDefault();
      this.isPulling = true;

      // Aplica resistência
      let pullDistance = deltaY * this.options.resistance;
      pullDistance = Math.min(pullDistance, this.options.maxPull);

      this.currentY = pullDistance;
      this.updateIndicator(pullDistance);
    }

    handleTouchEnd() {
      if (!this.isPulling) return;

      this.isPulling = false;

      if (this.currentY >= this.options.threshold) {
        this.triggerRefresh();
      } else {
        this.reset();
      }
    }

    updateIndicator(distance) {
      const progress = Math.min(distance / this.options.threshold, 1);

      // Posiciona o indicador
      this.indicator.style.transform = `translateY(${distance - 60}px)`;
      this.indicator.style.opacity = Math.min(progress * 1.5, 1);

      // Rotaciona a seta baseado no progresso
      const rotation = progress * 180;
      this.arrow.style.transform = `rotate(${rotation}deg)`;

      // Atualiza texto
      if (progress >= 1) {
        this.text.textContent = 'Solte para atualizar';
        this.indicator.classList.add('hi-pull-refresh--ready');
      } else {
        this.text.textContent = 'Puxe para atualizar';
        this.indicator.classList.remove('hi-pull-refresh--ready');
      }

      // Feedback tátil ao atingir threshold
      if (progress >= 1 && !this.indicator.dataset.vibrated) {
        this.indicator.dataset.vibrated = 'true';
        if (navigator.vibrate) {
          navigator.vibrate(10);
        }
      } else if (progress < 1) {
        delete this.indicator.dataset.vibrated;
      }
    }

    async triggerRefresh() {
      this.isRefreshing = true;

      // Atualiza visual
      this.indicator.classList.remove('hi-pull-refresh--ready');
      this.indicator.classList.add('hi-pull-refresh--refreshing');
      this.indicator.style.transform = 'translateY(0)';
      this.text.textContent = 'Atualizando...';

      // Haptic feedback
      if (navigator.vibrate) {
        navigator.vibrate(15);
      }

      try {
        // Executa callback
        if (typeof this.options.onRefresh === 'function') {
          const refreshPromise = this.options.onRefresh();

          // Timeout
          const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Timeout')), this.options.refreshTimeout);
          });

          await Promise.race([refreshPromise, timeoutPromise]);
        }

        // Sucesso
        this.showSuccess();
      } catch (error) {
        console.error('Erro no refresh:', error);
        this.showError();
      }
    }

    showSuccess() {
      this.indicator.classList.remove('hi-pull-refresh--refreshing');
      this.indicator.classList.add('hi-pull-refresh--success');
      this.text.textContent = 'Atualizado!';

      if (navigator.vibrate) {
        navigator.vibrate([10, 50, 10]);
      }

      setTimeout(() => {
        this.reset();
      }, 1000);
    }

    showError() {
      this.indicator.classList.remove('hi-pull-refresh--refreshing');
      this.indicator.classList.add('hi-pull-refresh--error');
      this.text.textContent = 'Erro ao atualizar';

      if (navigator.vibrate) {
        navigator.vibrate([50, 50, 50]);
      }

      setTimeout(() => {
        this.reset();
      }, 2000);
    }

    reset() {
      this.isRefreshing = false;
      this.currentY = 0;

      this.indicator.style.transition = 'all 300ms cubic-bezier(0.25, 0.46, 0.45, 0.94)';
      this.indicator.style.transform = 'translateY(-60px)';
      this.indicator.style.opacity = '0';

      setTimeout(() => {
        this.indicator.style.transition = '';
        this.indicator.classList.remove(
          'hi-pull-refresh--ready',
          'hi-pull-refresh--refreshing',
          'hi-pull-refresh--success',
          'hi-pull-refresh--error'
        );
        this.text.textContent = 'Puxe para atualizar';
        this.arrow.style.transform = '';
      }, 300);
    }

    destroy() {
      if (this.indicator && this.indicator.parentNode) {
        this.indicator.parentNode.removeChild(this.indicator);
      }
    }
  }

  /**
   * API pública
   */
  const HiPullRefresh = {
    /**
     * Inicializa o pull to refresh
     */
    init(options = {}) {
      // Destrói instância anterior
      if (instance) {
        instance.destroy();
      }

      instance = new PullRefreshHandler(options);
      isInitialized = true;

      return instance;
    },

    /**
     * Dispara refresh manualmente
     */
    async refresh() {
      if (instance && !instance.isRefreshing) {
        instance.indicator.style.transform = 'translateY(0)';
        instance.indicator.style.opacity = '1';
        await instance.triggerRefresh();
      }
    },

    /**
     * Verifica se está refreshing
     */
    isRefreshing() {
      return instance ? instance.isRefreshing : false;
    },

    /**
     * Reseta o indicador
     */
    reset() {
      if (instance) {
        instance.reset();
      }
    },

    /**
     * Destrói a instância
     */
    destroy() {
      if (instance) {
        instance.destroy();
        instance = null;
        isInitialized = false;
      }
    }
  };

  // Estilos do componente
  const styles = document.createElement('style');
  styles.textContent = `
    /* Pull Refresh Container */
    .hi-pull-refresh {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 60px;
      background: transparent;
      z-index: var(--hi-z-tooltip, 300);
      transform: translateY(-60px);
      opacity: 0;
      pointer-events: none;
    }

    .hi-pull-refresh__content {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--hi-space-1, 4px);
      padding: var(--hi-space-2, 8px) var(--hi-space-4, 16px);
      background-color: var(--hi-bg-primary, #ffffff);
      border-radius: var(--hi-radius-full, 9999px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    /* Icon Container */
    .hi-pull-refresh__icon {
      position: relative;
      width: 24px;
      height: 24px;
    }

    .hi-pull-refresh__icon svg {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      transition: opacity var(--hi-transition-fast, 150ms);
    }

    /* Arrow */
    .hi-pull-refresh__arrow {
      color: var(--hi-primary, #3b82f6);
      transition: transform 100ms;
    }

    .hi-pull-refresh--ready .hi-pull-refresh__arrow {
      color: var(--hi-success, #10b981);
    }

    /* Spinner */
    .hi-pull-refresh__spinner {
      opacity: 0;
      color: var(--hi-primary, #3b82f6);
    }

    .hi-pull-refresh--refreshing .hi-pull-refresh__arrow {
      opacity: 0;
    }

    .hi-pull-refresh--refreshing .hi-pull-refresh__spinner {
      opacity: 1;
      animation: pullRefreshSpin 1s linear infinite;
    }

    @keyframes pullRefreshSpin {
      to { transform: rotate(360deg); }
    }

    /* Check */
    .hi-pull-refresh__check {
      opacity: 0;
      color: var(--hi-success, #10b981);
    }

    .hi-pull-refresh--success .hi-pull-refresh__arrow,
    .hi-pull-refresh--success .hi-pull-refresh__spinner {
      opacity: 0;
    }

    .hi-pull-refresh--success .hi-pull-refresh__check {
      opacity: 1;
      animation: pullRefreshCheck 300ms ease-out;
    }

    @keyframes pullRefreshCheck {
      0% {
        transform: scale(0);
        opacity: 0;
      }
      50% {
        transform: scale(1.2);
      }
      100% {
        transform: scale(1);
        opacity: 1;
      }
    }

    /* Error State */
    .hi-pull-refresh--error .hi-pull-refresh__content {
      background-color: var(--hi-error-50, #fef2f2);
    }

    .hi-pull-refresh--error .hi-pull-refresh__text {
      color: var(--hi-error, #ef4444);
    }

    /* Text */
    .hi-pull-refresh__text {
      font-size: var(--hi-font-size-xs, 0.75rem);
      font-weight: var(--hi-font-weight-medium, 500);
      color: var(--hi-text-secondary, #6b7280);
      white-space: nowrap;
    }

    .hi-pull-refresh--ready .hi-pull-refresh__text {
      color: var(--hi-success, #10b981);
    }

    .hi-pull-refresh--refreshing .hi-pull-refresh__text {
      color: var(--hi-primary, #3b82f6);
    }

    .hi-pull-refresh--success .hi-pull-refresh__text {
      color: var(--hi-success, #10b981);
    }

    /* Safe area for notched devices */
    @supports (padding-top: env(safe-area-inset-top)) {
      .hi-pull-refresh {
        padding-top: env(safe-area-inset-top);
      }
    }

    /* Dark mode */
    @media (prefers-color-scheme: dark) {
      .hi-pull-refresh__content {
        background-color: var(--hi-gray-800, #1f2937);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
      }

      .hi-pull-refresh__text {
        color: var(--hi-gray-300, #d1d5db);
      }
    }
  `;
  document.head.appendChild(styles);

  // Expõe globalmente
  global.HiPullRefresh = HiPullRefresh;

})(typeof window !== 'undefined' ? window : this);
