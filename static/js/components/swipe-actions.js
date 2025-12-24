/**
 * HORÁRIO INTELIGENTE - Swipe Actions
 * Sistema de gestos para interações móveis naturais
 *
 * Uso:
 *   HiSwipeActions.attach(element, {
 *     leftAction: { icon: 'fa-check', color: '#10b981', label: 'Confirmar', onAction: () => {} },
 *     rightAction: { icon: 'fa-times', color: '#ef4444', label: 'Cancelar', onAction: () => {} },
 *     threshold: 80
 *   });
 *
 *   // Para listas
 *   HiSwipeActions.attachToList('#agenda-list', '.agenda-item', {
 *     leftAction: { ... },
 *     rightAction: { ... }
 *   });
 */

(function(global) {
  'use strict';

  const instances = new WeakMap();
  const VELOCITY_THRESHOLD = 0.3; // pixels per ms

  /**
   * Classe para gerenciar swipe em um elemento
   */
  class SwipeHandler {
    constructor(element, options) {
      this.element = element;
      this.options = {
        threshold: 80,
        maxSwipe: 120,
        resistance: 0.5,
        snapBack: true,
        hapticFeedback: true,
        ...options
      };

      this.startX = 0;
      this.startY = 0;
      this.currentX = 0;
      this.startTime = 0;
      this.isTracking = false;
      this.direction = null;
      this.actionTriggered = false;

      this.init();
    }

    init() {
      // Cria estrutura do swipe
      this.createStructure();

      // Event listeners
      this.element.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
      this.element.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
      this.element.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });

      // Mouse events para desktop testing
      this.element.addEventListener('mousedown', this.handleMouseDown.bind(this));
    }

    createStructure() {
      // Wrapper
      const wrapper = document.createElement('div');
      wrapper.className = 'hi-swipe-wrapper';

      // Ações esquerda (aparecem ao arrastar para direita)
      if (this.options.leftAction) {
        const leftAction = document.createElement('div');
        leftAction.className = 'hi-swipe-action hi-swipe-action--left';
        leftAction.style.setProperty('--action-color', this.options.leftAction.color || '#10b981');
        leftAction.innerHTML = `
          <i class="fas ${this.options.leftAction.icon}" aria-hidden="true"></i>
          <span class="hi-swipe-action__label">${this.options.leftAction.label || ''}</span>
        `;
        wrapper.appendChild(leftAction);
        this.leftActionEl = leftAction;
      }

      // Ações direita (aparecem ao arrastar para esquerda)
      if (this.options.rightAction) {
        const rightAction = document.createElement('div');
        rightAction.className = 'hi-swipe-action hi-swipe-action--right';
        rightAction.style.setProperty('--action-color', this.options.rightAction.color || '#ef4444');
        rightAction.innerHTML = `
          <i class="fas ${this.options.rightAction.icon}" aria-hidden="true"></i>
          <span class="hi-swipe-action__label">${this.options.rightAction.label || ''}</span>
        `;
        wrapper.appendChild(rightAction);
        this.rightActionEl = rightAction;
      }

      // Conteúdo principal
      const content = document.createElement('div');
      content.className = 'hi-swipe-content';

      // Move conteúdo original para dentro
      while (this.element.firstChild) {
        content.appendChild(this.element.firstChild);
      }

      wrapper.appendChild(content);
      this.element.appendChild(wrapper);
      this.element.classList.add('hi-swipe-item');

      this.wrapper = wrapper;
      this.content = content;
    }

    handleTouchStart(e) {
      if (e.touches.length > 1) return;

      const touch = e.touches[0];
      this.startX = touch.clientX;
      this.startY = touch.clientY;
      this.currentX = 0;
      this.startTime = Date.now();
      this.isTracking = true;
      this.direction = null;
      this.actionTriggered = false;

      this.content.style.transition = 'none';
    }

    handleTouchMove(e) {
      if (!this.isTracking) return;

      const touch = e.touches[0];
      const deltaX = touch.clientX - this.startX;
      const deltaY = touch.clientY - this.startY;

      // Determina direção no início
      if (this.direction === null) {
        if (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10) {
          this.direction = Math.abs(deltaX) > Math.abs(deltaY) ? 'horizontal' : 'vertical';
        }
      }

      // Só processa swipe horizontal
      if (this.direction !== 'horizontal') return;

      e.preventDefault();

      // Verifica se a direção é permitida
      const canSwipeRight = deltaX > 0 && this.options.leftAction;
      const canSwipeLeft = deltaX < 0 && this.options.rightAction;

      if (!canSwipeRight && !canSwipeLeft) {
        this.currentX = 0;
        this.updatePosition();
        return;
      }

      // Aplica resistência após o threshold
      let translateX = deltaX;
      const absTranslate = Math.abs(translateX);

      if (absTranslate > this.options.threshold) {
        const overflow = absTranslate - this.options.threshold;
        const dampedOverflow = overflow * this.options.resistance;
        translateX = (translateX > 0 ? 1 : -1) * (this.options.threshold + dampedOverflow);
      }

      // Limita ao máximo
      translateX = Math.max(-this.options.maxSwipe, Math.min(this.options.maxSwipe, translateX));

      this.currentX = translateX;
      this.updatePosition();

      // Feedback tátil ao atingir threshold
      if (!this.actionTriggered && Math.abs(this.currentX) >= this.options.threshold) {
        this.actionTriggered = true;
        if (this.options.hapticFeedback && navigator.vibrate) {
          navigator.vibrate(10);
        }
      } else if (this.actionTriggered && Math.abs(this.currentX) < this.options.threshold) {
        this.actionTriggered = false;
      }
    }

    handleTouchEnd(e) {
      if (!this.isTracking || this.direction !== 'horizontal') {
        this.isTracking = false;
        return;
      }

      this.isTracking = false;

      const endTime = Date.now();
      const duration = endTime - this.startTime;
      const velocity = Math.abs(this.currentX) / duration;

      // Verifica se atingiu threshold ou velocidade suficiente
      const passedThreshold = Math.abs(this.currentX) >= this.options.threshold;
      const fastSwipe = velocity > VELOCITY_THRESHOLD && Math.abs(this.currentX) > 40;

      if (passedThreshold || fastSwipe) {
        this.triggerAction();
      } else {
        this.snapBack();
      }
    }

    handleMouseDown(e) {
      // Simulação para desktop
      this.startX = e.clientX;
      this.startY = e.clientY;
      this.currentX = 0;
      this.startTime = Date.now();
      this.isTracking = true;
      this.direction = null;
      this.actionTriggered = false;

      this.content.style.transition = 'none';

      const handleMouseMove = (e) => {
        if (!this.isTracking) return;

        const deltaX = e.clientX - this.startX;
        const deltaY = e.clientY - this.startY;

        if (this.direction === null) {
          if (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10) {
            this.direction = Math.abs(deltaX) > Math.abs(deltaY) ? 'horizontal' : 'vertical';
          }
        }

        if (this.direction !== 'horizontal') return;

        e.preventDefault();

        const canSwipeRight = deltaX > 0 && this.options.leftAction;
        const canSwipeLeft = deltaX < 0 && this.options.rightAction;

        if (!canSwipeRight && !canSwipeLeft) {
          this.currentX = 0;
          this.updatePosition();
          return;
        }

        let translateX = deltaX;
        const absTranslate = Math.abs(translateX);

        if (absTranslate > this.options.threshold) {
          const overflow = absTranslate - this.options.threshold;
          const dampedOverflow = overflow * this.options.resistance;
          translateX = (translateX > 0 ? 1 : -1) * (this.options.threshold + dampedOverflow);
        }

        translateX = Math.max(-this.options.maxSwipe, Math.min(this.options.maxSwipe, translateX));

        this.currentX = translateX;
        this.updatePosition();

        if (!this.actionTriggered && Math.abs(this.currentX) >= this.options.threshold) {
          this.actionTriggered = true;
        } else if (this.actionTriggered && Math.abs(this.currentX) < this.options.threshold) {
          this.actionTriggered = false;
        }
      };

      const handleMouseUp = () => {
        if (!this.isTracking) return;

        this.isTracking = false;

        const passedThreshold = Math.abs(this.currentX) >= this.options.threshold;

        if (passedThreshold && this.direction === 'horizontal') {
          this.triggerAction();
        } else {
          this.snapBack();
        }

        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    updatePosition() {
      this.content.style.transform = `translateX(${this.currentX}px)`;

      // Atualiza aparência das ações
      const progress = Math.min(Math.abs(this.currentX) / this.options.threshold, 1);

      if (this.currentX > 0 && this.leftActionEl) {
        this.leftActionEl.style.opacity = progress;
        this.leftActionEl.classList.toggle('hi-swipe-action--ready', progress >= 1);
      } else if (this.leftActionEl) {
        this.leftActionEl.style.opacity = 0;
        this.leftActionEl.classList.remove('hi-swipe-action--ready');
      }

      if (this.currentX < 0 && this.rightActionEl) {
        this.rightActionEl.style.opacity = progress;
        this.rightActionEl.classList.toggle('hi-swipe-action--ready', progress >= 1);
      } else if (this.rightActionEl) {
        this.rightActionEl.style.opacity = 0;
        this.rightActionEl.classList.remove('hi-swipe-action--ready');
      }
    }

    triggerAction() {
      const isLeft = this.currentX > 0;
      const action = isLeft ? this.options.leftAction : this.options.rightAction;
      const actionEl = isLeft ? this.leftActionEl : this.rightActionEl;

      if (!action) {
        this.snapBack();
        return;
      }

      // Animação de confirmação
      this.content.style.transition = 'transform 200ms ease-out';

      if (action.fullSwipe !== false) {
        // Swipe completo - elemento sai da tela
        const direction = isLeft ? 1 : -1;
        this.content.style.transform = `translateX(${direction * window.innerWidth}px)`;

        // Callback
        setTimeout(() => {
          if (typeof action.onAction === 'function') {
            action.onAction(this.element, action);
          }

          // Dispara evento
          this.element.dispatchEvent(new CustomEvent('hi:swipe-action', {
            bubbles: true,
            detail: { action: action.id || (isLeft ? 'left' : 'right'), element: this.element }
          }));

          // Reset se não foi removido
          if (this.element.parentNode) {
            this.reset();
          }
        }, 200);
      } else {
        // Swipe parcial - snap back após ação
        if (typeof action.onAction === 'function') {
          action.onAction(this.element, action);
        }

        this.element.dispatchEvent(new CustomEvent('hi:swipe-action', {
          bubbles: true,
          detail: { action: action.id || (isLeft ? 'left' : 'right'), element: this.element }
        }));

        this.snapBack();
      }
    }

    snapBack() {
      this.content.style.transition = 'transform 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94)';
      this.content.style.transform = 'translateX(0)';

      if (this.leftActionEl) {
        this.leftActionEl.style.opacity = 0;
        this.leftActionEl.classList.remove('hi-swipe-action--ready');
      }
      if (this.rightActionEl) {
        this.rightActionEl.style.opacity = 0;
        this.rightActionEl.classList.remove('hi-swipe-action--ready');
      }
    }

    reset() {
      this.content.style.transition = 'none';
      this.content.style.transform = 'translateX(0)';
      this.currentX = 0;

      if (this.leftActionEl) {
        this.leftActionEl.style.opacity = 0;
        this.leftActionEl.classList.remove('hi-swipe-action--ready');
      }
      if (this.rightActionEl) {
        this.rightActionEl.style.opacity = 0;
        this.rightActionEl.classList.remove('hi-swipe-action--ready');
      }
    }

    destroy() {
      this.element.classList.remove('hi-swipe-item');

      // Restaura conteúdo original
      if (this.content) {
        while (this.content.firstChild) {
          this.element.appendChild(this.content.firstChild);
        }
      }

      if (this.wrapper && this.wrapper.parentNode) {
        this.wrapper.parentNode.removeChild(this.wrapper);
      }

      instances.delete(this.element);
    }
  }

  /**
   * API pública
   */
  const HiSwipeActions = {
    /**
     * Anexa swipe actions a um elemento
     */
    attach(element, options = {}) {
      const el = typeof element === 'string' ? document.querySelector(element) : element;
      if (!el) return null;

      // Remove instância anterior se existir
      if (instances.has(el)) {
        instances.get(el).destroy();
      }

      const handler = new SwipeHandler(el, options);
      instances.set(el, handler);

      return handler;
    },

    /**
     * Anexa a múltiplos elementos de uma lista
     */
    attachToList(container, itemSelector, options = {}) {
      const containerEl = typeof container === 'string' ? document.querySelector(container) : container;
      if (!containerEl) return [];

      const items = containerEl.querySelectorAll(itemSelector);
      const handlers = [];

      items.forEach(item => {
        handlers.push(this.attach(item, options));
      });

      // Observer para novos itens
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === 1 && node.matches(itemSelector)) {
              handlers.push(this.attach(node, options));
            }
          });
        });
      });

      observer.observe(containerEl, { childList: true, subtree: true });

      return handlers;
    },

    /**
     * Remove swipe de um elemento
     */
    detach(element) {
      const el = typeof element === 'string' ? document.querySelector(element) : element;
      if (!el || !instances.has(el)) return;

      instances.get(el).destroy();
    },

    /**
     * Reseta posição de um elemento
     */
    reset(element) {
      const el = typeof element === 'string' ? document.querySelector(element) : element;
      if (!el || !instances.has(el)) return;

      instances.get(el).reset();
    },

    /**
     * Presets para casos comuns
     */
    presets: {
      // Confirmar/Cancelar agendamento
      appointment: {
        leftAction: {
          id: 'confirm',
          icon: 'fa-check',
          color: '#10b981',
          label: 'Confirmar'
        },
        rightAction: {
          id: 'cancel',
          icon: 'fa-times',
          color: '#ef4444',
          label: 'Cancelar'
        }
      },

      // Aprovar/Rejeitar
      approval: {
        leftAction: {
          id: 'approve',
          icon: 'fa-thumbs-up',
          color: '#10b981',
          label: 'Aprovar'
        },
        rightAction: {
          id: 'reject',
          icon: 'fa-thumbs-down',
          color: '#ef4444',
          label: 'Rejeitar'
        }
      },

      // Arquivar/Deletar
      archive: {
        leftAction: {
          id: 'archive',
          icon: 'fa-archive',
          color: '#f59e0b',
          label: 'Arquivar'
        },
        rightAction: {
          id: 'delete',
          icon: 'fa-trash',
          color: '#ef4444',
          label: 'Excluir'
        }
      },

      // Apenas deletar (swipe único)
      deleteOnly: {
        rightAction: {
          id: 'delete',
          icon: 'fa-trash',
          color: '#ef4444',
          label: 'Excluir'
        }
      },

      // Favoritar/Deletar
      favorite: {
        leftAction: {
          id: 'favorite',
          icon: 'fa-star',
          color: '#f59e0b',
          label: 'Favorito'
        },
        rightAction: {
          id: 'delete',
          icon: 'fa-trash',
          color: '#ef4444',
          label: 'Excluir'
        }
      }
    }
  };

  // Estilos do componente
  const styles = document.createElement('style');
  styles.textContent = `
    /* Swipe Item */
    .hi-swipe-item {
      position: relative;
      overflow: hidden;
      touch-action: pan-y;
      -webkit-user-select: none;
      user-select: none;
    }

    .hi-swipe-wrapper {
      position: relative;
      width: 100%;
    }

    .hi-swipe-content {
      position: relative;
      background-color: var(--hi-bg-primary, #ffffff);
      z-index: 1;
      will-change: transform;
    }

    /* Ações */
    .hi-swipe-action {
      position: absolute;
      top: 0;
      bottom: 0;
      display: flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      padding: 0 var(--hi-space-5, 20px);
      color: white;
      font-weight: var(--hi-font-weight-medium, 500);
      opacity: 0;
      transition: opacity 100ms;
    }

    .hi-swipe-action--left {
      left: 0;
      background-color: var(--action-color, #10b981);
      justify-content: flex-start;
    }

    .hi-swipe-action--right {
      right: 0;
      background-color: var(--action-color, #ef4444);
      justify-content: flex-end;
    }

    .hi-swipe-action i {
      font-size: 1.25rem;
      transition: transform 150ms;
    }

    .hi-swipe-action--ready i {
      transform: scale(1.2);
    }

    .hi-swipe-action__label {
      font-size: var(--hi-font-size-sm, 0.875rem);
      white-space: nowrap;
    }

    /* Indicador visual de ação pronta */
    .hi-swipe-action--ready::after {
      content: '';
      position: absolute;
      width: 100%;
      height: 100%;
      background: rgba(255, 255, 255, 0.1);
      animation: swipePulse 500ms ease-in-out;
    }

    @keyframes swipePulse {
      0% { opacity: 0; }
      50% { opacity: 1; }
      100% { opacity: 0; }
    }

    /* Desabilita swipe quando há modais abertos */
    body.hi-modal-open .hi-swipe-item {
      touch-action: none;
    }

    /* Acessibilidade - mostra ações em hover para desktop */
    @media (hover: hover) and (pointer: fine) {
      .hi-swipe-item:hover .hi-swipe-action {
        opacity: 0.3;
      }
    }

    /* Ajustes para landscape */
    @media (max-height: 500px) and (orientation: landscape) {
      .hi-swipe-action {
        padding: 0 var(--hi-space-3, 12px);
      }

      .hi-swipe-action__label {
        display: none;
      }
    }
  `;
  document.head.appendChild(styles);

  // Expõe globalmente
  global.HiSwipeActions = HiSwipeActions;

})(typeof window !== 'undefined' ? window : this);
