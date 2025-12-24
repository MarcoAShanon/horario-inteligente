/**
 * HORÁRIO INTELIGENTE - Bloqueio de Período
 * Modal para bloquear horários (férias, feriados, congressos, etc.)
 *
 * Uso:
 *   HiBlockPeriod.show({
 *     onSave: (bloqueio) => { ... }
 *   });
 *
 *   // Com dados pré-preenchidos (edição)
 *   HiBlockPeriod.show({
 *     bloqueio: { tipo: 'ferias', dataInicio: '2024-12-24', dataFim: '2025-01-02' },
 *     onSave: (bloqueio) => { ... },
 *     onDelete: (bloqueio) => { ... }
 *   });
 */

(function(global) {
  'use strict';

  let currentModal = null;

  // Tipos de bloqueio
  const TIPOS_BLOQUEIO = [
    { id: 'ferias', label: 'Férias', icon: 'fa-umbrella-beach', color: '#3b82f6' },
    { id: 'feriado', label: 'Feriado / Emenda', icon: 'fa-flag', color: '#10b981' },
    { id: 'congresso', label: 'Congresso / Evento', icon: 'fa-graduation-cap', color: '#8b5cf6' },
    { id: 'pessoal', label: 'Compromisso Pessoal', icon: 'fa-user', color: '#f59e0b' },
    { id: 'outro', label: 'Outro', icon: 'fa-calendar-times', color: '#6b7280' }
  ];

  /**
   * Formata data para input date
   */
  function formatDateForInput(date) {
    if (!date) return '';
    if (typeof date === 'string' && date.includes('-')) return date;
    const d = new Date(date);
    return d.toISOString().split('T')[0];
  }

  /**
   * Formata data para exibição
   */
  function formatDateDisplay(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  /**
   * Calcula diferença em dias
   */
  function getDaysDiff(startDate, endDate) {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end - start);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
  }

  /**
   * Gera opções de horário
   */
  function generateTimeOptions() {
    const options = [];
    for (let h = 6; h <= 22; h++) {
      for (let m = 0; m < 60; m += 30) {
        const time = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
        options.push(time);
      }
    }
    return options;
  }

  /**
   * Cria o conteúdo do modal
   */
  function createModalContent(bloqueio = {}) {
    const {
      tipo = '',
      dataInicio = formatDateForInput(new Date()),
      dataFim = '',
      horarioInicio = '',
      horarioFim = '',
      motivo = '',
      bloqueioTotal = true
    } = bloqueio;

    const today = formatDateForInput(new Date());
    const timeOptions = generateTimeOptions();

    return `
      <form id="hi-block-form" class="hi-block-period">
        <!-- Tipo de Bloqueio -->
        <div class="hi-block-section">
          <h4 class="hi-section-title">
            <i class="fas fa-tag" aria-hidden="true"></i>
            Tipo de Bloqueio
          </h4>
          <div class="hi-block-types">
            ${TIPOS_BLOQUEIO.map(t => `
              <label class="hi-block-type ${tipo === t.id ? 'hi-block-type--selected' : ''}" style="--type-color: ${t.color}">
                <input type="radio" name="tipo" value="${t.id}" ${tipo === t.id ? 'checked' : ''} required />
                <i class="fas ${t.icon}" aria-hidden="true"></i>
                <span>${t.label}</span>
              </label>
            `).join('')}
          </div>
        </div>

        <!-- Período -->
        <div class="hi-block-section">
          <h4 class="hi-section-title">
            <i class="fas fa-calendar" aria-hidden="true"></i>
            Período
          </h4>
          <div class="hi-date-range">
            <div class="hi-form-group">
              <label for="dataInicio" class="hi-label hi-label--required">Data Início</label>
              <input
                type="date"
                id="dataInicio"
                name="dataInicio"
                class="hi-input"
                value="${dataInicio}"
                min="${today}"
                required
              />
            </div>
            <div class="hi-date-separator">
              <i class="fas fa-arrow-right" aria-hidden="true"></i>
            </div>
            <div class="hi-form-group">
              <label for="dataFim" class="hi-label hi-label--required">Data Fim</label>
              <input
                type="date"
                id="dataFim"
                name="dataFim"
                class="hi-input"
                value="${dataFim}"
                min="${dataInicio || today}"
                required
              />
            </div>
          </div>
          <div class="hi-date-summary" id="dateSummary">
            <i class="fas fa-info-circle" aria-hidden="true"></i>
            <span id="dateSummaryText">Selecione as datas</span>
          </div>
        </div>

        <!-- Bloqueio parcial -->
        <div class="hi-block-section">
          <div class="hi-block-toggle">
            <label class="hi-checkbox">
              <input type="checkbox" id="bloqueioTotal" name="bloqueioTotal" ${bloqueioTotal ? 'checked' : ''} />
              <span>Bloquear o dia inteiro</span>
            </label>
          </div>

          <div class="hi-partial-block" id="partialBlock" style="${bloqueioTotal ? 'display: none;' : ''}">
            <p class="hi-partial-hint">Bloquear apenas alguns horários:</p>
            <div class="hi-time-range">
              <div class="hi-form-group">
                <label for="horarioInicio" class="hi-label">De</label>
                <select id="horarioInicio" name="horarioInicio" class="hi-input hi-select">
                  <option value="">Selecione</option>
                  ${timeOptions.map(time => `
                    <option value="${time}" ${time === horarioInicio ? 'selected' : ''}>${time}</option>
                  `).join('')}
                </select>
              </div>
              <div class="hi-time-separator">até</div>
              <div class="hi-form-group">
                <label for="horarioFim" class="hi-label">Até</label>
                <select id="horarioFim" name="horarioFim" class="hi-input hi-select">
                  <option value="">Selecione</option>
                  ${timeOptions.map(time => `
                    <option value="${time}" ${time === horarioFim ? 'selected' : ''}>${time}</option>
                  `).join('')}
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- Motivo -->
        <div class="hi-block-section">
          <h4 class="hi-section-title">
            <i class="fas fa-sticky-note" aria-hidden="true"></i>
            Motivo
            <span class="hi-optional">(opcional)</span>
          </h4>
          <div class="hi-form-group">
            <textarea
              id="motivo"
              name="motivo"
              class="hi-input hi-textarea"
              rows="2"
              placeholder="Descreva o motivo do bloqueio..."
              maxlength="200"
            >${motivo}</textarea>
            <span class="hi-char-count">
              <span id="charCount">${motivo.length}</span>/200
            </span>
          </div>
        </div>

        <!-- Aviso sobre agendamentos -->
        <div class="hi-block-warning" id="blockWarning" style="display: none;">
          <i class="fas fa-exclamation-triangle" aria-hidden="true"></i>
          <div>
            <strong>Atenção:</strong>
            <span id="warningText">Existem agendamentos neste período que serão afetados.</span>
          </div>
        </div>
      </form>
    `;
  }

  /**
   * Configura listeners do formulário
   */
  function setupFormListeners(form, options) {
    const dataInicio = form.querySelector('#dataInicio');
    const dataFim = form.querySelector('#dataFim');
    const dateSummary = form.querySelector('#dateSummaryText');
    const bloqueioTotal = form.querySelector('#bloqueioTotal');
    const partialBlock = form.querySelector('#partialBlock');
    const motivo = form.querySelector('#motivo');
    const charCount = form.querySelector('#charCount');

    // Atualiza data mínima do fim
    dataInicio.addEventListener('change', () => {
      dataFim.min = dataInicio.value;
      if (dataFim.value && dataFim.value < dataInicio.value) {
        dataFim.value = dataInicio.value;
      }
      updateDateSummary();
    });

    dataFim.addEventListener('change', updateDateSummary);

    function updateDateSummary() {
      if (dataInicio.value && dataFim.value) {
        const days = getDaysDiff(dataInicio.value, dataFim.value);
        const startFormatted = formatDateDisplay(dataInicio.value);
        const endFormatted = formatDateDisplay(dataFim.value);

        if (dataInicio.value === dataFim.value) {
          dateSummary.textContent = `1 dia: ${startFormatted}`;
        } else {
          dateSummary.textContent = `${days} dias: ${startFormatted} a ${endFormatted}`;
        }

        // Verifica se há agendamentos no período (callback opcional)
        if (typeof options.onCheckConflicts === 'function') {
          options.onCheckConflicts(dataInicio.value, dataFim.value);
        }
      } else {
        dateSummary.textContent = 'Selecione as datas';
      }
    }

    // Toggle bloqueio parcial
    bloqueioTotal.addEventListener('change', () => {
      partialBlock.style.display = bloqueioTotal.checked ? 'none' : 'block';
    });

    // Tipos de bloqueio
    form.querySelectorAll('.hi-block-type input').forEach(radio => {
      radio.addEventListener('change', (e) => {
        form.querySelectorAll('.hi-block-type').forEach(type => {
          type.classList.remove('hi-block-type--selected');
        });
        e.target.closest('.hi-block-type').classList.add('hi-block-type--selected');
      });
    });

    // Contador de caracteres
    motivo.addEventListener('input', () => {
      charCount.textContent = motivo.value.length;
    });

    // Atualiza resumo inicial
    updateDateSummary();
  }

  /**
   * Obtém dados do formulário
   */
  function getFormData(form) {
    const formData = new FormData(form);
    return {
      tipo: formData.get('tipo'),
      dataInicio: formData.get('dataInicio'),
      dataFim: formData.get('dataFim'),
      bloqueioTotal: formData.get('bloqueioTotal') === 'on',
      horarioInicio: formData.get('bloqueioTotal') === 'on' ? null : formData.get('horarioInicio'),
      horarioFim: formData.get('bloqueioTotal') === 'on' ? null : formData.get('horarioFim'),
      motivo: formData.get('motivo')?.trim() || null
    };
  }

  /**
   * Valida dados
   */
  function validateData(data) {
    const errors = [];

    if (!data.tipo) {
      errors.push('Selecione um tipo de bloqueio.');
    }

    if (!data.dataInicio) {
      errors.push('Informe a data de início.');
    }

    if (!data.dataFim) {
      errors.push('Informe a data de fim.');
    }

    if (data.dataInicio && data.dataFim && data.dataFim < data.dataInicio) {
      errors.push('A data de fim deve ser igual ou posterior à data de início.');
    }

    if (!data.bloqueioTotal) {
      if (!data.horarioInicio || !data.horarioFim) {
        errors.push('Informe os horários de início e fim do bloqueio.');
      } else if (data.horarioFim <= data.horarioInicio) {
        errors.push('O horário de fim deve ser após o horário de início.');
      }
    }

    return errors;
  }

  /**
   * API pública
   */
  const HiBlockPeriod = {
    /**
     * Mostra o modal de bloqueio
     */
    show(options = {}) {
      const { bloqueio = {}, onSave, onDelete, onClose, onCheckConflicts } = options;
      const isEditing = !!bloqueio.id;

      // Fecha modal anterior
      if (currentModal) {
        currentModal.close();
      }

      const buttons = [
        {
          text: 'Cancelar',
          variant: 'secondary',
          action: (modal) => modal.close()
        }
      ];

      // Botão de excluir (apenas na edição)
      if (isEditing && typeof onDelete === 'function') {
        buttons.push({
          text: 'Excluir',
          variant: 'danger',
          icon: 'fas fa-trash',
          action: async (modal) => {
            if (typeof HiModal !== 'undefined') {
              const confirmed = await HiModal.confirm(
                'Excluir Bloqueio',
                'Deseja realmente excluir este bloqueio?',
                { danger: true, confirmText: 'Sim, excluir', cancelText: 'Não' }
              );
              if (confirmed) {
                await onDelete(bloqueio);
                modal.close();
              }
            } else {
              await onDelete(bloqueio);
              modal.close();
            }
          }
        });
      }

      // Botão de salvar
      buttons.push({
        text: isEditing ? 'Atualizar' : 'Bloquear',
        variant: 'primary',
        icon: isEditing ? 'fas fa-save' : 'fas fa-lock',
        action: async (modal) => {
          const form = modal.modal.querySelector('#hi-block-form');
          const data = getFormData(form);
          const errors = validateData(data);

          if (errors.length > 0) {
            if (typeof HiToast !== 'undefined') {
              HiToast.error('Dados inválidos', errors[0]);
            } else {
              alert(errors[0]);
            }
            return;
          }

          if (typeof onSave === 'function') {
            try {
              // Adiciona ID se for edição
              if (isEditing) {
                data.id = bloqueio.id;
              }

              await onSave(data);

              if (typeof HiToast !== 'undefined') {
                HiToast.success(
                  isEditing ? 'Bloqueio atualizado!' : 'Período bloqueado!',
                  `${formatDateDisplay(data.dataInicio)} a ${formatDateDisplay(data.dataFim)}`
                );
              }
              modal.close();
            } catch (error) {
              if (typeof HiToast !== 'undefined') {
                HiToast.error('Erro', error.message || 'Tente novamente.');
              }
            }
          } else {
            modal.close();
          }
        }
      });

      currentModal = HiModal.create({
        title: isEditing ? 'Editar Bloqueio' : 'Bloquear Período',
        content: createModalContent(bloqueio),
        size: 'md',
        buttons: buttons,
        onOpen: (modal) => {
          const form = modal.modal.querySelector('#hi-block-form');
          if (form) {
            setupFormListeners(form, { onCheckConflicts });
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
     * Mostra aviso de conflito
     */
    showConflictWarning(count) {
      const warning = document.querySelector('#blockWarning');
      const warningText = document.querySelector('#warningText');

      if (warning && count > 0) {
        warning.style.display = 'flex';
        warningText.textContent = `Existem ${count} agendamento(s) neste período que serão afetados.`;
      } else if (warning) {
        warning.style.display = 'none';
      }
    },

    /**
     * Fecha o modal
     */
    close() {
      if (currentModal) {
        currentModal.close();
        currentModal = null;
      }
    },

    /**
     * Obtém tipos de bloqueio
     */
    getTypes() {
      return [...TIPOS_BLOQUEIO];
    }
  };

  // Estilos do componente
  const styles = document.createElement('style');
  styles.textContent = `
    .hi-block-period {
      display: flex;
      flex-direction: column;
      gap: var(--hi-space-5, 20px);
    }

    .hi-block-section {
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

    .hi-optional {
      font-weight: var(--hi-font-weight-normal, 400);
      color: var(--hi-text-muted, #9ca3af);
      font-size: var(--hi-font-size-xs, 0.75rem);
    }

    /* Tipos de bloqueio */
    .hi-block-types {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: var(--hi-space-2, 8px);
    }

    .hi-block-type {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      padding: var(--hi-space-3, 12px);
      background-color: var(--hi-gray-50, #f9fafb);
      border: 2px solid var(--hi-gray-200, #e5e7eb);
      border-radius: var(--hi-radius-lg, 12px);
      cursor: pointer;
      transition: all var(--hi-transition-fast, 150ms);
      text-align: center;
    }

    .hi-block-type input {
      display: none;
    }

    .hi-block-type i {
      font-size: 1.25rem;
      color: var(--type-color, var(--hi-text-secondary));
    }

    .hi-block-type span {
      font-size: var(--hi-font-size-sm, 0.875rem);
      font-weight: var(--hi-font-weight-medium, 500);
      color: var(--hi-text-primary, #1f2937);
    }

    .hi-block-type:hover {
      border-color: var(--type-color, var(--hi-primary));
      background-color: white;
    }

    .hi-block-type--selected {
      border-color: var(--type-color, var(--hi-primary));
      background-color: white;
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--type-color) 20%, transparent);
    }

    /* Range de datas */
    .hi-date-range {
      display: flex;
      align-items: flex-end;
      gap: var(--hi-space-3, 12px);
    }

    .hi-date-range .hi-form-group {
      flex: 1;
      margin: 0;
    }

    .hi-date-separator {
      padding-bottom: var(--hi-space-3, 12px);
      color: var(--hi-text-muted, #9ca3af);
    }

    .hi-date-summary {
      display: flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      padding: var(--hi-space-2, 8px) var(--hi-space-3, 12px);
      background-color: var(--hi-primary-50, #eff6ff);
      border-radius: var(--hi-radius-md, 8px);
      font-size: var(--hi-font-size-sm, 0.875rem);
      color: var(--hi-primary, #3b82f6);
    }

    /* Bloqueio parcial */
    .hi-block-toggle {
      padding: var(--hi-space-3, 12px);
      background-color: var(--hi-gray-50, #f9fafb);
      border-radius: var(--hi-radius-md, 8px);
    }

    .hi-partial-block {
      padding: var(--hi-space-3, 12px);
      background-color: var(--hi-gray-50, #f9fafb);
      border-radius: var(--hi-radius-md, 8px);
      margin-top: var(--hi-space-2, 8px);
    }

    .hi-partial-hint {
      font-size: var(--hi-font-size-sm, 0.875rem);
      color: var(--hi-text-secondary, #6b7280);
      margin: 0 0 var(--hi-space-3, 12px) 0;
    }

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
      color: var(--hi-text-muted, #9ca3af);
      font-size: var(--hi-font-size-sm, 0.875rem);
    }

    /* Contador de caracteres */
    .hi-char-count {
      display: block;
      text-align: right;
      font-size: var(--hi-font-size-xs, 0.75rem);
      color: var(--hi-text-muted, #9ca3af);
      margin-top: var(--hi-space-1, 4px);
    }

    /* Aviso */
    .hi-block-warning {
      display: flex;
      align-items: flex-start;
      gap: var(--hi-space-3, 12px);
      padding: var(--hi-space-3, 12px) var(--hi-space-4, 16px);
      background-color: var(--hi-warning-bg, #fffbeb);
      border: 1px solid var(--hi-warning, #f59e0b);
      border-radius: var(--hi-radius-lg, 12px);
      font-size: var(--hi-font-size-sm, 0.875rem);
      color: var(--hi-warning-dark, #d97706);
    }

    .hi-block-warning i {
      font-size: 1.25rem;
      margin-top: 2px;
    }

    @media (max-width: 480px) {
      .hi-date-range,
      .hi-time-range {
        flex-direction: column;
      }

      .hi-date-separator {
        display: none;
      }

      .hi-block-types {
        grid-template-columns: repeat(2, 1fr);
      }
    }
  `;
  document.head.appendChild(styles);

  // Expõe globalmente
  global.HiBlockPeriod = HiBlockPeriod;

})(typeof window !== 'undefined' ? window : this);
