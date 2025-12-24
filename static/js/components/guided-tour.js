/**
 * HORÁRIO INTELIGENTE - Guided Tour
 * Tour guiado otimizado para demo com suporte mobile
 *
 * Uso:
 *   HiGuidedTour.start({
 *     steps: [
 *       { element: '#header', title: 'Cabeçalho', content: 'Aqui você encontra...' },
 *       ...
 *     ],
 *     onComplete: () => {},
 *     onExit: () => {}
 *   });
 *
 *   // Ou usar steps pré-definidos para demo
 *   HiGuidedTour.startDemo();
 */

(function(global) {
  'use strict';

  let overlay = null;
  let tooltip = null;
  let currentStep = 0;
  let steps = [];
  let callbacks = {};
  let isRunning = false;

  // Steps padrão da demo
  const DEFAULT_DEMO_STEPS = [
    {
      element: '[data-tour="header"]',
      title: 'Bem-vindo ao Horário Inteligente!',
      content: 'Este é o sistema de agendamento mais intuitivo para profissionais de saúde. Vamos fazer um tour rápido?',
      position: 'bottom'
    },
    {
      element: '[data-tour="stats"]',
      title: 'Visão Geral',
      content: 'Aqui você vê as métricas do dia: consultas agendadas, confirmadas e pendentes. Tudo em um relance!',
      position: 'bottom'
    },
    {
      element: '[data-tour="agenda"]',
      title: 'Sua Agenda',
      content: 'Lista completa dos agendamentos do dia. Clique em qualquer consulta para ver detalhes ou gerenciar.',
      position: 'top'
    },
    {
      element: '[data-tour="quick-actions"]',
      title: 'Ações Rápidas',
      content: 'Acesse as funcionalidades mais usadas: novo agendamento, WhatsApp, relatórios e configurações.',
      position: 'left'
    },
    {
      element: '[data-tour="whatsapp"]',
      title: 'Integração WhatsApp',
      content: 'Seus pacientes agendam diretamente pelo WhatsApp! A IA responde 24/7 e confirma automaticamente.',
      position: 'top'
    },
    {
      element: '[data-tour="notifications"]',
      title: 'Notificações',
      content: 'Receba alertas de novos agendamentos, confirmações e lembretes importantes.',
      position: 'bottom'
    }
  ];

  /**
   * Cria overlay de fundo
   */
  function createOverlay() {
    if (overlay) return;

    overlay = document.createElement('div');
    overlay.className = 'hi-tour-overlay';
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        exit();
      }
    });
    document.body.appendChild(overlay);
  }

  /**
   * Cria tooltip
   */
  function createTooltip() {
    if (tooltip) return;

    tooltip = document.createElement('div');
    tooltip.className = 'hi-tour-tooltip';
    tooltip.innerHTML = `
      <button class="hi-tour-close" aria-label="Fechar tour">
        <i class="fas fa-times"></i>
      </button>
      <div class="hi-tour-header">
        <span class="hi-tour-step-indicator"></span>
        <h3 class="hi-tour-title"></h3>
      </div>
      <div class="hi-tour-content"></div>
      <div class="hi-tour-footer">
        <button class="hi-tour-btn hi-tour-btn--skip">Pular</button>
        <div class="hi-tour-nav">
          <button class="hi-tour-btn hi-tour-btn--prev">
            <i class="fas fa-chevron-left"></i>
            Anterior
          </button>
          <button class="hi-tour-btn hi-tour-btn--next">
            Próximo
            <i class="fas fa-chevron-right"></i>
          </button>
        </div>
      </div>
    `;

    // Event listeners
    tooltip.querySelector('.hi-tour-close').addEventListener('click', exit);
    tooltip.querySelector('.hi-tour-btn--skip').addEventListener('click', exit);
    tooltip.querySelector('.hi-tour-btn--prev').addEventListener('click', prevStep);
    tooltip.querySelector('.hi-tour-btn--next').addEventListener('click', nextStep);

    document.body.appendChild(tooltip);
  }

  /**
   * Destaca o elemento atual
   */
  function highlightElement(element) {
    // Remove destaque anterior
    document.querySelectorAll('.hi-tour-highlight').forEach(el => {
      el.classList.remove('hi-tour-highlight');
    });

    if (element) {
      element.classList.add('hi-tour-highlight');
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  /**
   * Posiciona o tooltip
   */
  function positionTooltip(element, position = 'bottom') {
    if (!element || !tooltip) return;

    const rect = element.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    const padding = 16;

    let top, left;
    let arrowClass = '';

    // Calcula posição baseada na preferência e espaço disponível
    switch (position) {
      case 'top':
        top = rect.top - tooltipRect.height - padding;
        left = rect.left + (rect.width - tooltipRect.width) / 2;
        arrowClass = 'hi-tour-tooltip--arrow-bottom';
        break;
      case 'bottom':
        top = rect.bottom + padding;
        left = rect.left + (rect.width - tooltipRect.width) / 2;
        arrowClass = 'hi-tour-tooltip--arrow-top';
        break;
      case 'left':
        top = rect.top + (rect.height - tooltipRect.height) / 2;
        left = rect.left - tooltipRect.width - padding;
        arrowClass = 'hi-tour-tooltip--arrow-right';
        break;
      case 'right':
        top = rect.top + (rect.height - tooltipRect.height) / 2;
        left = rect.right + padding;
        arrowClass = 'hi-tour-tooltip--arrow-left';
        break;
      default:
        top = rect.bottom + padding;
        left = rect.left + (rect.width - tooltipRect.width) / 2;
        arrowClass = 'hi-tour-tooltip--arrow-top';
    }

    // Ajusta se sair da tela
    const maxLeft = window.innerWidth - tooltipRect.width - padding;
    const maxTop = window.innerHeight - tooltipRect.height - padding;

    left = Math.max(padding, Math.min(left, maxLeft));
    top = Math.max(padding, Math.min(top, maxTop));

    // Remove todas as classes de seta
    tooltip.classList.remove(
      'hi-tour-tooltip--arrow-top',
      'hi-tour-tooltip--arrow-bottom',
      'hi-tour-tooltip--arrow-left',
      'hi-tour-tooltip--arrow-right'
    );
    tooltip.classList.add(arrowClass);

    tooltip.style.top = `${top}px`;
    tooltip.style.left = `${left}px`;
  }

  /**
   * Atualiza o conteúdo do tooltip
   */
  function updateTooltip(step) {
    if (!tooltip) return;

    const stepIndicator = tooltip.querySelector('.hi-tour-step-indicator');
    const title = tooltip.querySelector('.hi-tour-title');
    const content = tooltip.querySelector('.hi-tour-content');
    const prevBtn = tooltip.querySelector('.hi-tour-btn--prev');
    const nextBtn = tooltip.querySelector('.hi-tour-btn--next');

    stepIndicator.textContent = `${currentStep + 1} de ${steps.length}`;
    title.textContent = step.title || '';
    content.innerHTML = step.content || '';

    // Atualiza botões
    prevBtn.style.display = currentStep === 0 ? 'none' : '';
    nextBtn.textContent = currentStep === steps.length - 1 ? 'Concluir' : 'Próximo';
    if (currentStep < steps.length - 1) {
      nextBtn.innerHTML = 'Próximo <i class="fas fa-chevron-right"></i>';
    } else {
      nextBtn.innerHTML = '<i class="fas fa-check"></i> Concluir';
    }
  }

  /**
   * Mostra um step
   */
  function showStep(index) {
    if (index < 0 || index >= steps.length) return;

    currentStep = index;
    const step = steps[index];

    // Encontra o elemento
    const element = step.element ? document.querySelector(step.element) : null;

    // Destaca elemento
    highlightElement(element);

    // Atualiza tooltip
    updateTooltip(step);

    // Posiciona tooltip
    setTimeout(() => {
      if (element) {
        positionTooltip(element, step.position);
      } else {
        // Centraliza se não houver elemento
        tooltip.style.top = '50%';
        tooltip.style.left = '50%';
        tooltip.style.transform = 'translate(-50%, -50%)';
      }
    }, 100);
  }

  /**
   * Próximo step
   */
  function nextStep() {
    if (currentStep < steps.length - 1) {
      showStep(currentStep + 1);
    } else {
      complete();
    }
  }

  /**
   * Step anterior
   */
  function prevStep() {
    if (currentStep > 0) {
      showStep(currentStep - 1);
    }
  }

  /**
   * Completa o tour
   */
  function complete() {
    if (typeof callbacks.onComplete === 'function') {
      callbacks.onComplete();
    }
    cleanup();

    // Mostra toast de conclusão
    if (typeof HiToast !== 'undefined') {
      HiToast.success('Tour concluído! Explore o sistema à vontade.');
    }
  }

  /**
   * Sai do tour
   */
  function exit() {
    if (typeof callbacks.onExit === 'function') {
      callbacks.onExit();
    }
    cleanup();
  }

  /**
   * Limpa elementos do tour
   */
  function cleanup() {
    isRunning = false;

    // Remove destaque
    document.querySelectorAll('.hi-tour-highlight').forEach(el => {
      el.classList.remove('hi-tour-highlight');
    });

    // Remove overlay
    if (overlay && overlay.parentNode) {
      overlay.classList.add('hi-tour-overlay--exiting');
      setTimeout(() => {
        if (overlay && overlay.parentNode) {
          overlay.parentNode.removeChild(overlay);
        }
        overlay = null;
      }, 300);
    }

    // Remove tooltip
    if (tooltip && tooltip.parentNode) {
      tooltip.classList.add('hi-tour-tooltip--exiting');
      setTimeout(() => {
        if (tooltip && tooltip.parentNode) {
          tooltip.parentNode.removeChild(tooltip);
        }
        tooltip = null;
      }, 300);
    }

    // Remove classe do body
    document.body.classList.remove('hi-tour-active');
  }

  /**
   * Inicia o tour
   */
  function start(options = {}) {
    if (isRunning) return;

    steps = options.steps || DEFAULT_DEMO_STEPS;
    callbacks = {
      onComplete: options.onComplete,
      onExit: options.onExit
    };
    currentStep = 0;
    isRunning = true;

    document.body.classList.add('hi-tour-active');

    createOverlay();
    createTooltip();

    // Anima entrada
    requestAnimationFrame(() => {
      overlay.classList.add('hi-tour-overlay--visible');
      tooltip.classList.add('hi-tour-tooltip--visible');
      showStep(0);
    });
  }

  /**
   * API pública
   */
  const HiGuidedTour = {
    start,
    startDemo(options = {}) {
      start({
        steps: DEFAULT_DEMO_STEPS,
        ...options
      });
    },
    next: nextStep,
    prev: prevStep,
    exit,
    isRunning() {
      return isRunning;
    }
  };

  // Estilos do componente
  const styles = document.createElement('style');
  styles.textContent = `
    /* Tour Active State */
    body.hi-tour-active {
      overflow: hidden;
    }

    /* Overlay */
    .hi-tour-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      z-index: var(--hi-z-overlay, 500);
      opacity: 0;
      transition: opacity 300ms;
    }

    .hi-tour-overlay--visible {
      opacity: 1;
    }

    .hi-tour-overlay--exiting {
      opacity: 0;
    }

    /* Highlighted Element */
    .hi-tour-highlight {
      position: relative;
      z-index: calc(var(--hi-z-overlay, 500) + 1) !important;
      box-shadow: 0 0 0 4px var(--hi-primary, #3b82f6), 0 0 0 9999px rgba(0, 0, 0, 0.5);
      border-radius: var(--hi-radius-lg, 12px);
    }

    /* Tooltip */
    .hi-tour-tooltip {
      position: fixed;
      max-width: 340px;
      width: calc(100vw - 32px);
      background: white;
      border-radius: var(--hi-radius-xl, 16px);
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
      z-index: calc(var(--hi-z-overlay, 500) + 2);
      opacity: 0;
      transform: translateY(10px);
      transition: all 300ms;
    }

    .hi-tour-tooltip--visible {
      opacity: 1;
      transform: translateY(0);
    }

    .hi-tour-tooltip--exiting {
      opacity: 0;
      transform: translateY(10px);
    }

    /* Tooltip Arrow */
    .hi-tour-tooltip::before {
      content: '';
      position: absolute;
      width: 16px;
      height: 16px;
      background: white;
      transform: rotate(45deg);
    }

    .hi-tour-tooltip--arrow-top::before {
      top: -8px;
      left: 50%;
      margin-left: -8px;
    }

    .hi-tour-tooltip--arrow-bottom::before {
      bottom: -8px;
      left: 50%;
      margin-left: -8px;
    }

    .hi-tour-tooltip--arrow-left::before {
      left: -8px;
      top: 50%;
      margin-top: -8px;
    }

    .hi-tour-tooltip--arrow-right::before {
      right: -8px;
      top: 50%;
      margin-top: -8px;
    }

    /* Close Button */
    .hi-tour-close {
      position: absolute;
      top: 12px;
      right: 12px;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: none;
      border: none;
      color: var(--hi-text-muted, #9ca3af);
      cursor: pointer;
      border-radius: var(--hi-radius-md, 8px);
      transition: all var(--hi-transition-fast, 150ms);
    }

    .hi-tour-close:hover {
      background: var(--hi-gray-100, #f3f4f6);
      color: var(--hi-text-primary, #1f2937);
    }

    /* Header */
    .hi-tour-header {
      padding: 20px 20px 0;
    }

    .hi-tour-step-indicator {
      display: inline-block;
      padding: 4px 10px;
      background: var(--hi-primary-100, #dbeafe);
      color: var(--hi-primary, #3b82f6);
      font-size: var(--hi-font-size-xs, 0.75rem);
      font-weight: var(--hi-font-weight-medium, 500);
      border-radius: var(--hi-radius-full, 9999px);
      margin-bottom: 8px;
    }

    .hi-tour-title {
      font-size: 1.125rem;
      font-weight: var(--hi-font-weight-bold, 700);
      color: var(--hi-text-primary, #1f2937);
      margin: 0;
      padding-right: 32px;
    }

    /* Content */
    .hi-tour-content {
      padding: 12px 20px 20px;
      font-size: var(--hi-font-size-sm, 0.875rem);
      color: var(--hi-text-secondary, #6b7280);
      line-height: 1.6;
    }

    /* Footer */
    .hi-tour-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 20px;
      border-top: 1px solid var(--hi-border-light, #e5e7eb);
      background: var(--hi-gray-50, #f9fafb);
      border-radius: 0 0 var(--hi-radius-xl, 16px) var(--hi-radius-xl, 16px);
    }

    .hi-tour-nav {
      display: flex;
      gap: 8px;
    }

    .hi-tour-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      font-size: var(--hi-font-size-sm, 0.875rem);
      font-weight: var(--hi-font-weight-medium, 500);
      border-radius: var(--hi-radius-md, 8px);
      cursor: pointer;
      transition: all var(--hi-transition-fast, 150ms);
      border: none;
      min-height: var(--hi-touch-target-min, 44px);
    }

    .hi-tour-btn--skip {
      background: none;
      color: var(--hi-text-muted, #9ca3af);
    }

    .hi-tour-btn--skip:hover {
      color: var(--hi-text-secondary, #6b7280);
    }

    .hi-tour-btn--prev {
      background: var(--hi-gray-100, #f3f4f6);
      color: var(--hi-text-secondary, #6b7280);
    }

    .hi-tour-btn--prev:hover {
      background: var(--hi-gray-200, #e5e7eb);
    }

    .hi-tour-btn--next {
      background: var(--hi-primary, #3b82f6);
      color: white;
    }

    .hi-tour-btn--next:hover {
      background: var(--hi-primary-dark, #2563eb);
    }

    /* Mobile adjustments */
    @media (max-width: 640px) {
      .hi-tour-tooltip {
        max-width: none;
        width: calc(100vw - 32px);
        left: 16px !important;
        right: 16px;
        bottom: 16px !important;
        top: auto !important;
        transform: none !important;
      }

      .hi-tour-tooltip--visible {
        transform: none !important;
      }

      .hi-tour-tooltip::before {
        display: none;
      }

      .hi-tour-footer {
        flex-direction: column;
        gap: 12px;
      }

      .hi-tour-nav {
        width: 100%;
      }

      .hi-tour-btn {
        flex: 1;
        justify-content: center;
      }

      .hi-tour-btn--skip {
        order: 1;
      }
    }
  `;
  document.head.appendChild(styles);

  // Expõe globalmente
  global.HiGuidedTour = HiGuidedTour;

})(typeof window !== 'undefined' ? window : this);
