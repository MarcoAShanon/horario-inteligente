/**
 * HORÁRIO INTELIGENTE - Hero Demo Component
 * Componente de Hero otimizado para a página demo
 *
 * Uso:
 *   HiHeroDemo.render('#hero-container', {
 *     title: 'Bem-vindo ao Horário Inteligente',
 *     subtitle: 'Sua agenda sob controle',
 *     features: [...]
 *   });
 */

(function(global) {
  'use strict';

  /**
   * Renderiza o Hero da demo
   */
  function render(container, options = {}) {
    const containerEl = typeof container === 'string'
      ? document.querySelector(container)
      : container;

    if (!containerEl) return;

    const {
      userName = 'Dr. Carlos',
      clinicName = 'Clínica Demonstração',
      todayStats = { consultas: 8, confirmados: 5, pendentes: 3 },
      nextAppointment = null,
      onStartTour,
      onNewAppointment,
      onViewAgenda
    } = options;

    // Gera saudação baseada na hora
    const hour = new Date().getHours();
    let greeting = 'Bom dia';
    if (hour >= 12 && hour < 18) greeting = 'Boa tarde';
    else if (hour >= 18) greeting = 'Boa noite';

    // Data formatada
    const today = new Date();
    const dateFormatted = today.toLocaleDateString('pt-BR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long'
    });

    containerEl.innerHTML = `
      <div class="hi-hero-demo">
        <!-- Mobile-first greeting -->
        <div class="hi-hero-demo__greeting">
          <div class="hi-hero-demo__greeting-content">
            <h1 class="hi-hero-demo__title">${greeting}, ${userName}!</h1>
            <p class="hi-hero-demo__date">
              <i class="fas fa-calendar-day" aria-hidden="true"></i>
              ${dateFormatted.charAt(0).toUpperCase() + dateFormatted.slice(1)}
            </p>
          </div>
          <button class="hi-hero-demo__tour-btn" id="startTourBtn" aria-label="Iniciar tour guiado">
            <i class="fas fa-question-circle" aria-hidden="true"></i>
            <span class="hi-hero-demo__tour-btn-text">Tour</span>
          </button>
        </div>

        <!-- Quick Stats - Horizontal scroll on mobile -->
        <div class="hi-hero-demo__stats-scroll">
          <div class="hi-hero-demo__stats">
            <div class="hi-hero-demo__stat hi-hero-demo__stat--primary">
              <div class="hi-hero-demo__stat-icon">
                <i class="fas fa-calendar-check" aria-hidden="true"></i>
              </div>
              <div class="hi-hero-demo__stat-content">
                <span class="hi-hero-demo__stat-value">${todayStats.consultas}</span>
                <span class="hi-hero-demo__stat-label">Consultas Hoje</span>
              </div>
            </div>

            <div class="hi-hero-demo__stat hi-hero-demo__stat--success">
              <div class="hi-hero-demo__stat-icon">
                <i class="fas fa-check-circle" aria-hidden="true"></i>
              </div>
              <div class="hi-hero-demo__stat-content">
                <span class="hi-hero-demo__stat-value">${todayStats.confirmados}</span>
                <span class="hi-hero-demo__stat-label">Confirmados</span>
              </div>
            </div>

            <div class="hi-hero-demo__stat hi-hero-demo__stat--warning">
              <div class="hi-hero-demo__stat-icon">
                <i class="fas fa-clock" aria-hidden="true"></i>
              </div>
              <div class="hi-hero-demo__stat-content">
                <span class="hi-hero-demo__stat-value">${todayStats.pendentes}</span>
                <span class="hi-hero-demo__stat-label">Pendentes</span>
              </div>
            </div>
          </div>
        </div>

        ${nextAppointment ? `
        <!-- Next Appointment Card -->
        <div class="hi-hero-demo__next-appointment" id="nextAppointmentCard">
          <div class="hi-hero-demo__next-header">
            <span class="hi-hero-demo__next-badge">
              <i class="fas fa-clock" aria-hidden="true"></i>
              Próximo em ${nextAppointment.timeUntil}
            </span>
          </div>
          <div class="hi-hero-demo__next-content">
            <div class="hi-hero-demo__next-avatar">
              ${nextAppointment.paciente.charAt(0).toUpperCase()}
            </div>
            <div class="hi-hero-demo__next-info">
              <h3 class="hi-hero-demo__next-name">${nextAppointment.paciente}</h3>
              <p class="hi-hero-demo__next-details">
                <i class="fas fa-stethoscope" aria-hidden="true"></i>
                ${nextAppointment.tipo} - ${nextAppointment.hora}
              </p>
              ${nextAppointment.telefone ? `
              <p class="hi-hero-demo__next-phone">
                <i class="fas fa-phone" aria-hidden="true"></i>
                ${nextAppointment.telefone}
              </p>
              ` : ''}
            </div>
          </div>
          <div class="hi-hero-demo__next-actions">
            <a href="tel:${nextAppointment.telefone || ''}" class="hi-hero-demo__action-btn hi-hero-demo__action-btn--call">
              <i class="fas fa-phone" aria-hidden="true"></i>
            </a>
            <a href="https://wa.me/55${(nextAppointment.telefone || '').replace(/\D/g, '')}"
               target="_blank"
               class="hi-hero-demo__action-btn hi-hero-demo__action-btn--whatsapp">
              <i class="fab fa-whatsapp" aria-hidden="true"></i>
            </a>
          </div>
        </div>
        ` : `
        <!-- Empty state when no appointments -->
        <div class="hi-hero-demo__empty">
          <div class="hi-hero-demo__empty-icon">
            <i class="fas fa-calendar-check" aria-hidden="true"></i>
          </div>
          <h3 class="hi-hero-demo__empty-title">Agenda livre!</h3>
          <p class="hi-hero-demo__empty-text">Nenhuma consulta agendada para hoje.</p>
        </div>
        `}

        <!-- Quick Actions - Sticky on mobile -->
        <div class="hi-hero-demo__actions">
          <button class="hi-hero-demo__action hi-hero-demo__action--primary" id="newAppointmentBtn">
            <i class="fas fa-plus" aria-hidden="true"></i>
            <span>Novo Agendamento</span>
          </button>
          <button class="hi-hero-demo__action hi-hero-demo__action--secondary" id="viewAgendaBtn">
            <i class="fas fa-calendar-alt" aria-hidden="true"></i>
            <span>Ver Agenda</span>
          </button>
        </div>
      </div>
    `;

    // Event listeners
    const tourBtn = containerEl.querySelector('#startTourBtn');
    if (tourBtn && typeof onStartTour === 'function') {
      tourBtn.addEventListener('click', onStartTour);
    }

    const newAppBtn = containerEl.querySelector('#newAppointmentBtn');
    if (newAppBtn && typeof onNewAppointment === 'function') {
      newAppBtn.addEventListener('click', onNewAppointment);
    }

    const viewAgendaBtn = containerEl.querySelector('#viewAgendaBtn');
    if (viewAgendaBtn && typeof onViewAgenda === 'function') {
      viewAgendaBtn.addEventListener('click', onViewAgenda);
    }
  }

  /**
   * API pública
   */
  const HiHeroDemo = {
    render
  };

  // Estilos do componente
  const styles = document.createElement('style');
  styles.textContent = `
    /* Hero Demo Component */
    .hi-hero-demo {
      padding: var(--hi-space-4, 16px);
      background: linear-gradient(135deg, var(--hi-primary, #3b82f6) 0%, var(--hi-primary-dark, #2563eb) 100%);
      color: white;
      border-radius: 0 0 var(--hi-radius-xl, 16px) var(--hi-radius-xl, 16px);
      margin-bottom: var(--hi-space-4, 16px);
    }

    /* Greeting Section */
    .hi-hero-demo__greeting {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: var(--hi-space-4, 16px);
    }

    .hi-hero-demo__title {
      font-size: 1.5rem;
      font-weight: var(--hi-font-weight-bold, 700);
      margin: 0 0 var(--hi-space-1, 4px) 0;
    }

    .hi-hero-demo__date {
      font-size: var(--hi-font-size-sm, 0.875rem);
      opacity: 0.9;
      display: flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
    }

    .hi-hero-demo__tour-btn {
      display: flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      padding: var(--hi-space-2, 8px) var(--hi-space-3, 12px);
      background: rgba(255, 255, 255, 0.2);
      border: 1px solid rgba(255, 255, 255, 0.3);
      border-radius: var(--hi-radius-full, 9999px);
      color: white;
      font-size: var(--hi-font-size-sm, 0.875rem);
      cursor: pointer;
      transition: all var(--hi-transition-fast, 150ms);
      min-height: var(--hi-touch-target-min, 44px);
    }

    .hi-hero-demo__tour-btn:hover {
      background: rgba(255, 255, 255, 0.3);
    }

    /* Stats Section */
    .hi-hero-demo__stats-scroll {
      overflow-x: auto;
      margin: 0 calc(var(--hi-space-4, 16px) * -1);
      padding: 0 var(--hi-space-4, 16px);
      scrollbar-width: none;
      -ms-overflow-style: none;
    }

    .hi-hero-demo__stats-scroll::-webkit-scrollbar {
      display: none;
    }

    .hi-hero-demo__stats {
      display: flex;
      gap: var(--hi-space-3, 12px);
      padding-bottom: var(--hi-space-2, 8px);
    }

    .hi-hero-demo__stat {
      flex: 0 0 auto;
      min-width: 120px;
      display: flex;
      align-items: center;
      gap: var(--hi-space-3, 12px);
      padding: var(--hi-space-3, 12px);
      background: rgba(255, 255, 255, 0.15);
      border-radius: var(--hi-radius-lg, 12px);
      backdrop-filter: blur(4px);
    }

    .hi-hero-demo__stat-icon {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.2);
      border-radius: var(--hi-radius-md, 8px);
      font-size: 1.125rem;
    }

    .hi-hero-demo__stat-content {
      display: flex;
      flex-direction: column;
    }

    .hi-hero-demo__stat-value {
      font-size: 1.25rem;
      font-weight: var(--hi-font-weight-bold, 700);
      line-height: 1.2;
    }

    .hi-hero-demo__stat-label {
      font-size: var(--hi-font-size-xs, 0.75rem);
      opacity: 0.9;
    }

    /* Next Appointment Card */
    .hi-hero-demo__next-appointment {
      margin-top: var(--hi-space-4, 16px);
      padding: var(--hi-space-4, 16px);
      background: white;
      border-radius: var(--hi-radius-lg, 12px);
      color: var(--hi-text-primary, #1f2937);
    }

    .hi-hero-demo__next-header {
      margin-bottom: var(--hi-space-3, 12px);
    }

    .hi-hero-demo__next-badge {
      display: inline-flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      padding: var(--hi-space-1, 4px) var(--hi-space-3, 12px);
      background: var(--hi-warning-100, #fef3c7);
      color: var(--hi-warning-700, #b45309);
      font-size: var(--hi-font-size-xs, 0.75rem);
      font-weight: var(--hi-font-weight-medium, 500);
      border-radius: var(--hi-radius-full, 9999px);
    }

    .hi-hero-demo__next-content {
      display: flex;
      align-items: center;
      gap: var(--hi-space-3, 12px);
    }

    .hi-hero-demo__next-avatar {
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--hi-primary-100, #dbeafe);
      color: var(--hi-primary, #3b82f6);
      border-radius: 50%;
      font-size: 1.25rem;
      font-weight: var(--hi-font-weight-bold, 700);
    }

    .hi-hero-demo__next-info {
      flex: 1;
      min-width: 0;
    }

    .hi-hero-demo__next-name {
      font-size: 1rem;
      font-weight: var(--hi-font-weight-semibold, 600);
      margin: 0 0 var(--hi-space-1, 4px) 0;
      color: var(--hi-text-primary, #1f2937);
    }

    .hi-hero-demo__next-details,
    .hi-hero-demo__next-phone {
      font-size: var(--hi-font-size-sm, 0.875rem);
      color: var(--hi-text-muted, #9ca3af);
      display: flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      margin: 0;
    }

    .hi-hero-demo__next-phone {
      margin-top: var(--hi-space-1, 4px);
    }

    .hi-hero-demo__next-actions {
      display: flex;
      gap: var(--hi-space-2, 8px);
      margin-top: var(--hi-space-3, 12px);
      padding-top: var(--hi-space-3, 12px);
      border-top: 1px solid var(--hi-border-light, #e5e7eb);
    }

    .hi-hero-demo__action-btn {
      width: 44px;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      text-decoration: none;
      font-size: 1.125rem;
      transition: all var(--hi-transition-fast, 150ms);
    }

    .hi-hero-demo__action-btn--call {
      background: var(--hi-primary-100, #dbeafe);
      color: var(--hi-primary, #3b82f6);
    }

    .hi-hero-demo__action-btn--call:hover {
      background: var(--hi-primary, #3b82f6);
      color: white;
    }

    .hi-hero-demo__action-btn--whatsapp {
      background: #dcfce7;
      color: #16a34a;
    }

    .hi-hero-demo__action-btn--whatsapp:hover {
      background: #16a34a;
      color: white;
    }

    /* Empty State */
    .hi-hero-demo__empty {
      margin-top: var(--hi-space-4, 16px);
      padding: var(--hi-space-6, 24px);
      background: rgba(255, 255, 255, 0.1);
      border-radius: var(--hi-radius-lg, 12px);
      text-align: center;
    }

    .hi-hero-demo__empty-icon {
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 50%;
      margin: 0 auto var(--hi-space-3, 12px);
      font-size: 1.25rem;
    }

    .hi-hero-demo__empty-title {
      font-size: 1rem;
      font-weight: var(--hi-font-weight-semibold, 600);
      margin: 0 0 var(--hi-space-1, 4px) 0;
    }

    .hi-hero-demo__empty-text {
      font-size: var(--hi-font-size-sm, 0.875rem);
      opacity: 0.9;
      margin: 0;
    }

    /* Quick Actions */
    .hi-hero-demo__actions {
      display: flex;
      gap: var(--hi-space-3, 12px);
      margin-top: var(--hi-space-4, 16px);
    }

    .hi-hero-demo__action {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: var(--hi-space-2, 8px);
      padding: var(--hi-space-3, 12px) var(--hi-space-4, 16px);
      border-radius: var(--hi-radius-lg, 12px);
      font-size: var(--hi-font-size-sm, 0.875rem);
      font-weight: var(--hi-font-weight-medium, 500);
      cursor: pointer;
      transition: all var(--hi-transition-fast, 150ms);
      border: none;
      min-height: var(--hi-touch-target-min, 44px);
    }

    .hi-hero-demo__action--primary {
      background: white;
      color: var(--hi-primary, #3b82f6);
    }

    .hi-hero-demo__action--primary:hover {
      background: var(--hi-gray-100, #f3f4f6);
    }

    .hi-hero-demo__action--secondary {
      background: rgba(255, 255, 255, 0.2);
      color: white;
      border: 1px solid rgba(255, 255, 255, 0.3);
    }

    .hi-hero-demo__action--secondary:hover {
      background: rgba(255, 255, 255, 0.3);
    }

    /* Desktop adjustments */
    @media (min-width: 768px) {
      .hi-hero-demo {
        padding: var(--hi-space-6, 24px);
        border-radius: var(--hi-radius-xl, 16px);
        margin: var(--hi-space-4, 16px);
      }

      .hi-hero-demo__title {
        font-size: 2rem;
      }

      .hi-hero-demo__stats {
        justify-content: flex-start;
      }

      .hi-hero-demo__stat {
        min-width: 160px;
      }

      .hi-hero-demo__next-appointment {
        display: flex;
        align-items: center;
        gap: var(--hi-space-4, 16px);
      }

      .hi-hero-demo__next-header {
        margin-bottom: 0;
      }

      .hi-hero-demo__next-content {
        flex: 1;
      }

      .hi-hero-demo__next-actions {
        margin-top: 0;
        padding-top: 0;
        padding-left: var(--hi-space-4, 16px);
        border-top: none;
        border-left: 1px solid var(--hi-border-light, #e5e7eb);
      }

      .hi-hero-demo__actions {
        max-width: 400px;
      }
    }

    /* Hide tour text on very small screens */
    @media (max-width: 360px) {
      .hi-hero-demo__tour-btn-text {
        display: none;
      }
    }
  `;
  document.head.appendChild(styles);

  // Expõe globalmente
  global.HiHeroDemo = HiHeroDemo;

})(typeof window !== 'undefined' ? window : this);
