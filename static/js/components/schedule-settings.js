/**
 * HORÁRIO INTELIGENTE - Configurações de Horários
 * Modal para controle de horários de atendimento do médico
 *
 * Uso:
 *   HiScheduleSettings.show({
 *     config: {
 *       diasAtendimento: ['seg', 'ter', 'qua', 'qui', 'sex'],
 *       horarioInicio: '08:00',
 *       horarioFim: '18:00',
 *       intervaloInicio: '12:00',
 *       intervaloFim: '14:00',
 *       duracaoConsulta: 30
 *     },
 *     onSave: (newConfig) => { ... }
 *   });
 */

(function(global) {
  'use strict';

  let currentModal = null;

  // Dias da semana
  const DIAS_SEMANA = [
    { id: 'seg', label: 'Segunda', short: 'Seg' },
    { id: 'ter', label: 'Terça', short: 'Ter' },
    { id: 'qua', label: 'Quarta', short: 'Qua' },
    { id: 'qui', label: 'Quinta', short: 'Qui' },
    { id: 'sex', label: 'Sexta', short: 'Sex' },
    { id: 'sab', label: 'Sábado', short: 'Sáb' },
    { id: 'dom', label: 'Domingo', short: 'Dom' }
  ];

  // Opções de duração
  const DURACOES = [15, 20, 30, 40, 45, 60, 90, 120];

  // Gera opções de horário
  function generateTimeOptions(startHour = 6, endHour = 22, interval = 30) {
    const options = [];
    for (let h = startHour; h <= endHour; h++) {
      for (let m = 0; m < 60; m += interval) {
        if (h === endHour && m > 0) break;
        const time = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
        options.push(time);
      }
    }
    return options;
  }

  /**
   * Cria o conteúdo do modal
   */
  function createModalContent(config = {}) {
    const {
      diasAtendimento = ['seg', 'ter', 'qua', 'qui', 'sex'],
      horarioInicio = '08:00',
      horarioFim = '18:00',
      intervaloInicio = '12:00',
      intervaloFim = '14:00',
      duracaoConsulta = 30,
      temIntervalo = true
    } = config;

    const timeOptions = generateTimeOptions();

    return `
      <form id="hi-schedule-form" class="hi-schedule-settings">
        <!-- Dias de Atendimento -->
        <div class="hi-schedule-section">
          <h4 class="hi-section-title">
            <i class="fas fa-calendar-week" aria-hidden="true"></i>
            Dias de Atendimento
          </h4>
          <div class="hi-days-grid">
            ${DIAS_SEMANA.map(dia => `
              <label class="hi-day-checkbox ${diasAtendimento.includes(dia.id) ? 'hi-day-checkbox--checked' : ''}">
                <input
                  type="checkbox"
                  name="diasAtendimento"
                  value="${dia.id}"
                  ${diasAtendimento.includes(dia.id) ? 'checked' : ''}
                />
                <span class="hi-day-label">
                  <span class="hi-day-short">${dia.short}</span>
                  <span class="hi-day-full">${dia.label}</span>
                </span>
              </label>
            `).join('')}
          </div>
        </div>

        <!-- Horários -->
        <div class="hi-schedule-section">
          <h4 class="hi-section-title">
            <i class="fas fa-clock" aria-hidden="true"></i>
            Horário de Atendimento
          </h4>
          <div class="hi-time-range">
            <div class="hi-form-group">
              <label for="horarioInicio" class="hi-label">Início</label>
              <select id="horarioInicio" name="horarioInicio" class="hi-input hi-select">
                ${timeOptions.map(time => `
                  <option value="${time}" ${time === horarioInicio ? 'selected' : ''}>${time}</option>
                `).join('')}
              </select>
            </div>
            <div class="hi-time-separator">até</div>
            <div class="hi-form-group">
              <label for="horarioFim" class="hi-label">Término</label>
              <select id="horarioFim" name="horarioFim" class="hi-input hi-select">
                ${timeOptions.map(time => `
                  <option value="${time}" ${time === horarioFim ? 'selected' : ''}>${time}</option>
                `).join('')}
              </select>
            </div>
          </div>
        </div>

        <!-- Intervalo -->
        <div class="hi-schedule-section">
          <h4 class="hi-section-title">
            <i class="fas fa-utensils" aria-hidden="true"></i>
            Intervalo para Almoço
            <label class="hi-toggle-inline">
              <input type="checkbox" id="temIntervalo" name="temIntervalo" ${temIntervalo ? 'checked' : ''} />
              <span class="hi-toggle-slider"></span>
            </label>
          </h4>
          <div class="hi-time-range hi-interval-fields" ${!temIntervalo ? 'style="opacity: 0.5; pointer-events: none;"' : ''}>
            <div class="hi-form-group">
              <label for="intervaloInicio" class="hi-label">De</label>
              <select id="intervaloInicio" name="intervaloInicio" class="hi-input hi-select">
                ${timeOptions.map(time => `
                  <option value="${time}" ${time === intervaloInicio ? 'selected' : ''}>${time}</option>
                `).join('')}
              </select>
            </div>
            <div class="hi-time-separator">até</div>
            <div class="hi-form-group">
              <label for="intervaloFim" class="hi-label">Até</label>
              <select id="intervaloFim" name="intervaloFim" class="hi-input hi-select">
                ${timeOptions.map(time => `
                  <option value="${time}" ${time === intervaloFim ? 'selected' : ''}>${time}</option>
                `).join('')}
              </select>
            </div>
          </div>
        </div>

        <!-- Duração da Consulta -->
        <div class="hi-schedule-section">
          <h4 class="hi-section-title">
            <i class="fas fa-hourglass-half" aria-hidden="true"></i>
            Duração Padrão da Consulta
          </h4>
          <div class="hi-duration-options">
            ${DURACOES.map(dur => `
              <label class="hi-duration-option ${dur === duracaoConsulta ? 'hi-duration-option--selected' : ''}">
                <input
                  type="radio"
                  name="duracaoConsulta"
                  value="${dur}"
                  ${dur === duracaoConsulta ? 'checked' : ''}
                />
                <span>${dur} min</span>
              </label>
            `).join('')}
          </div>
        </div>

        <!-- Resumo -->
        <div class="hi-schedule-summary" id="scheduleSummary">
          <i class="fas fa-info-circle" aria-hidden="true"></i>
          <span id="summaryText">Calculando horários disponíveis...</span>
        </div>
      </form>
    `;
  }

  /**
   * Calcula slots disponíveis
   */
  function calculateSlots(config) {
    const { horarioInicio, horarioFim, intervaloInicio, intervaloFim, duracaoConsulta, temIntervalo, diasAtendimento } = config;

    const toMinutes = (time) => {
      const [h, m] = time.split(':').map(Number);
      return h * 60 + m;
    };

    let totalMinutes = toMinutes(horarioFim) - toMinutes(horarioInicio);

    if (temIntervalo) {
      const intervalMinutes = toMinutes(intervaloFim) - toMinutes(intervaloInicio);
      totalMinutes -= intervalMinutes;
    }

    const slotsPerDay = Math.floor(totalMinutes / duracaoConsulta);
    const totalSlots = slotsPerDay * diasAtendimento.length;

    return { slotsPerDay, totalSlots, totalMinutes };
  }

  /**
   * Atualiza o resumo
   */
  function updateSummary(form) {
    const config = getFormData(form);
    const { slotsPerDay, totalSlots } = calculateSlots(config);

    const summaryEl = form.querySelector('#summaryText');
    if (summaryEl) {
      if (config.diasAtendimento.length === 0) {
        summaryEl.textContent = 'Selecione pelo menos um dia de atendimento.';
      } else {
        summaryEl.textContent = `${slotsPerDay} consultas por dia • ${totalSlots} consultas por semana`;
      }
    }
  }

  /**
   * Obtém dados do formulário
   */
  function getFormData(form) {
    const formData = new FormData(form);
    return {
      diasAtendimento: formData.getAll('diasAtendimento'),
      horarioInicio: formData.get('horarioInicio'),
      horarioFim: formData.get('horarioFim'),
      intervaloInicio: formData.get('intervaloInicio'),
      intervaloFim: formData.get('intervaloFim'),
      duracaoConsulta: parseInt(formData.get('duracaoConsulta')),
      temIntervalo: formData.get('temIntervalo') === 'on'
    };
  }

  /**
   * Valida configurações
   */
  function validateConfig(config) {
    const errors = [];

    if (config.diasAtendimento.length === 0) {
      errors.push('Selecione pelo menos um dia de atendimento.');
    }

    const toMinutes = (time) => {
      const [h, m] = time.split(':').map(Number);
      return h * 60 + m;
    };

    if (toMinutes(config.horarioFim) <= toMinutes(config.horarioInicio)) {
      errors.push('O horário de término deve ser após o horário de início.');
    }

    if (config.temIntervalo) {
      if (toMinutes(config.intervaloFim) <= toMinutes(config.intervaloInicio)) {
        errors.push('O fim do intervalo deve ser após o início.');
      }
      if (toMinutes(config.intervaloInicio) < toMinutes(config.horarioInicio) ||
          toMinutes(config.intervaloFim) > toMinutes(config.horarioFim)) {
        errors.push('O intervalo deve estar dentro do horário de atendimento.');
      }
    }

    return errors;
  }

  /**
   * Configura event listeners do formulário
   */
  function setupFormListeners(form) {
    // Toggle de intervalo
    const intervaloToggle = form.querySelector('#temIntervalo');
    const intervalFields = form.querySelector('.hi-interval-fields');

    if (intervaloToggle && intervalFields) {
      intervaloToggle.addEventListener('change', () => {
        if (intervaloToggle.checked) {
          intervalFields.style.opacity = '1';
          intervalFields.style.pointerEvents = 'auto';
        } else {
          intervalFields.style.opacity = '0.5';
          intervalFields.style.pointerEvents = 'none';
        }
        updateSummary(form);
      });
    }

    // Checkboxes de dias
    form.querySelectorAll('.hi-day-checkbox input').forEach(checkbox => {
      checkbox.addEventListener('change', (e) => {
        const label = e.target.closest('.hi-day-checkbox');
        if (e.target.checked) {
          label.classList.add('hi-day-checkbox--checked');
        } else {
          label.classList.remove('hi-day-checkbox--checked');
        }
        updateSummary(form);
      });
    });

    // Radio de duração
    form.querySelectorAll('.hi-duration-option input').forEach(radio => {
      radio.addEventListener('change', (e) => {
        form.querySelectorAll('.hi-duration-option').forEach(opt => {
          opt.classList.remove('hi-duration-option--selected');
        });
        e.target.closest('.hi-duration-option').classList.add('hi-duration-option--selected');
        updateSummary(form);
      });
    });

    // Selects de horário
    form.querySelectorAll('select').forEach(select => {
      select.addEventListener('change', () => updateSummary(form));
    });

    // Atualiza resumo inicial
    setTimeout(() => updateSummary(form), 100);
  }

  /**
   * API pública
   */
  const HiScheduleSettings = {
    /**
     * Mostra o modal de configurações
     */
    show(options = {}) {
      const { config = {}, onSave, onClose } = options;

      // Fecha modal anterior
      if (currentModal) {
        currentModal.close();
      }

      currentModal = HiModal.create({
        title: 'Meus Horários de Atendimento',
        content: createModalContent(config),
        size: 'md',
        buttons: [
          {
            text: 'Cancelar',
            variant: 'secondary',
            action: (modal) => modal.close()
          },
          {
            text: 'Salvar',
            variant: 'primary',
            icon: 'fas fa-save',
            action: async (modal) => {
              const form = modal.modal.querySelector('#hi-schedule-form');
              const newConfig = getFormData(form);
              const errors = validateConfig(newConfig);

              if (errors.length > 0) {
                if (typeof HiToast !== 'undefined') {
                  HiToast.error('Configuração inválida', errors[0]);
                } else {
                  alert(errors[0]);
                }
                return;
              }

              if (typeof onSave === 'function') {
                try {
                  await onSave(newConfig);
                  if (typeof HiToast !== 'undefined') {
                    HiToast.success('Horários salvos com sucesso!');
                  }
                  modal.close();
                } catch (error) {
                  if (typeof HiToast !== 'undefined') {
                    HiToast.error('Erro ao salvar', error.message || 'Tente novamente.');
                  }
                }
              } else {
                modal.close();
              }
            }
          }
        ],
        onOpen: (modal) => {
          const form = modal.modal.querySelector('#hi-schedule-form');
          if (form) {
            setupFormListeners(form);
          }
        },
        onClose: () => {
          if (typeof onClose === 'function') {
            onClose();
          }
          currentModal = null;
        }
      });

      currentModal.open();
      return currentModal;
    },

    /**
     * Fecha o modal
     */
    close() {
      if (currentModal) {
        currentModal.close();
        currentModal = null;
      }
    }
  };

  // Estilos do componente
  const styles = document.createElement('style');
  styles.textContent = `
    .hi-schedule-settings {
      display: flex;
      flex-direction: column;
      gap: var(--hi-space-6, 24px);
    }

    .hi-schedule-section {
      display: flex;
      flex-direction: column;
      gap: var(--hi-space-3, 12px);
    }

    .hi-section-title {
      display: flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      font-size: var(--hi-font-size-sm, 0.875rem);
      font-weight: var(--hi-font-weight-semibold, 600);
      color: var(--hi-text-primary, #1f2937);
      margin: 0;
    }

    .hi-section-title i {
      color: var(--hi-primary, #3b82f6);
    }

    /* Toggle inline */
    .hi-toggle-inline {
      margin-left: auto;
      display: inline-flex;
      align-items: center;
      cursor: pointer;
    }

    .hi-toggle-inline input {
      display: none;
    }

    .hi-toggle-slider {
      width: 40px;
      height: 22px;
      background-color: var(--hi-gray-300, #d1d5db);
      border-radius: 11px;
      position: relative;
      transition: background-color 0.2s;
    }

    .hi-toggle-slider::after {
      content: '';
      position: absolute;
      width: 18px;
      height: 18px;
      background: white;
      border-radius: 50%;
      top: 2px;
      left: 2px;
      transition: transform 0.2s;
      box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }

    .hi-toggle-inline input:checked + .hi-toggle-slider {
      background-color: var(--hi-primary, #3b82f6);
    }

    .hi-toggle-inline input:checked + .hi-toggle-slider::after {
      transform: translateX(18px);
    }

    /* Dias da semana */
    .hi-days-grid {
      display: flex;
      flex-wrap: wrap;
      gap: var(--hi-space-2, 8px);
    }

    .hi-day-checkbox {
      display: flex;
      align-items: center;
      justify-content: center;
      min-width: 70px;
      padding: var(--hi-space-2, 8px) var(--hi-space-3, 12px);
      background-color: var(--hi-gray-100, #f3f4f6);
      border: 2px solid var(--hi-gray-200, #e5e7eb);
      border-radius: var(--hi-radius-lg, 12px);
      cursor: pointer;
      transition: all var(--hi-transition-fast, 150ms);
    }

    .hi-day-checkbox input {
      display: none;
    }

    .hi-day-checkbox:hover {
      border-color: var(--hi-primary-light, #60a5fa);
    }

    .hi-day-checkbox--checked {
      background-color: var(--hi-primary-50, #eff6ff);
      border-color: var(--hi-primary, #3b82f6);
    }

    .hi-day-label {
      font-size: var(--hi-font-size-sm, 0.875rem);
      font-weight: var(--hi-font-weight-medium, 500);
      color: var(--hi-text-primary, #1f2937);
    }

    .hi-day-short {
      display: none;
    }

    @media (max-width: 480px) {
      .hi-day-checkbox {
        min-width: 48px;
        padding: var(--hi-space-2, 8px);
      }
      .hi-day-short { display: inline; }
      .hi-day-full { display: none; }
    }

    /* Range de horário */
    .hi-time-range {
      display: flex;
      align-items: flex-end;
      gap: var(--hi-space-3, 12px);
    }

    .hi-time-range .hi-form-group {
      flex: 1;
      margin: 0;
    }

    .hi-time-separator {
      padding-bottom: var(--hi-space-3, 12px);
      color: var(--hi-text-secondary, #6b7280);
      font-size: var(--hi-font-size-sm, 0.875rem);
    }

    /* Opções de duração */
    .hi-duration-options {
      display: flex;
      flex-wrap: wrap;
      gap: var(--hi-space-2, 8px);
    }

    .hi-duration-option {
      display: flex;
      align-items: center;
      justify-content: center;
      min-width: 60px;
      padding: var(--hi-space-2, 8px) var(--hi-space-4, 16px);
      background-color: var(--hi-gray-100, #f3f4f6);
      border: 2px solid var(--hi-gray-200, #e5e7eb);
      border-radius: var(--hi-radius-lg, 12px);
      cursor: pointer;
      transition: all var(--hi-transition-fast, 150ms);
      font-size: var(--hi-font-size-sm, 0.875rem);
      font-weight: var(--hi-font-weight-medium, 500);
    }

    .hi-duration-option input {
      display: none;
    }

    .hi-duration-option:hover {
      border-color: var(--hi-primary-light, #60a5fa);
    }

    .hi-duration-option--selected {
      background-color: var(--hi-primary, #3b82f6);
      border-color: var(--hi-primary, #3b82f6);
      color: white;
    }

    /* Resumo */
    .hi-schedule-summary {
      display: flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      padding: var(--hi-space-3, 12px) var(--hi-space-4, 16px);
      background-color: var(--hi-info-bg, #eff6ff);
      border-radius: var(--hi-radius-lg, 12px);
      font-size: var(--hi-font-size-sm, 0.875rem);
      color: var(--hi-primary, #3b82f6);
    }

    .hi-schedule-summary i {
      font-size: 1rem;
    }
  `;
  document.head.appendChild(styles);

  // Expõe globalmente
  global.HiScheduleSettings = HiScheduleSettings;

})(typeof window !== 'undefined' ? window : this);
