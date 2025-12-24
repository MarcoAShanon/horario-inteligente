/**
 * HORÁRIO INTELIGENTE - Mobile Form Components
 * Formulários otimizados para dispositivos móveis
 *
 * Uso:
 *   HiMobileForm.enhance('#meu-form');
 *
 *   // Input com floating label
 *   HiMobileForm.createInput({
 *     type: 'text',
 *     name: 'nome',
 *     label: 'Nome completo',
 *     required: true
 *   });
 *
 *   // Date picker nativo mobile
 *   HiMobileForm.createDatePicker({
 *     name: 'data',
 *     label: 'Data da consulta',
 *     min: new Date()
 *   });
 */

(function(global) {
  'use strict';

  // Detecta se é iOS
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);

  // Configurações padrão
  const defaults = {
    floatingLabels: true,
    hapticFeedback: true,
    scrollIntoView: true,
    autoAdvance: true
  };

  let formCount = 0;

  /**
   * Cria um ID único
   */
  function generateId(prefix = 'hi-input') {
    return `${prefix}-${++formCount}`;
  }

  /**
   * Cria input com floating label
   */
  function createFloatingInput(config) {
    const {
      type = 'text',
      name,
      label,
      placeholder = ' ',
      required = false,
      pattern,
      minLength,
      maxLength,
      min,
      max,
      step,
      value = '',
      autocomplete,
      inputmode,
      icon,
      helper,
      error,
      disabled = false
    } = config;

    const id = config.id || generateId();

    const wrapper = document.createElement('div');
    wrapper.className = 'hi-mobile-field';
    if (error) wrapper.classList.add('hi-mobile-field--error');
    if (disabled) wrapper.classList.add('hi-mobile-field--disabled');

    let inputHtml = '';

    if (type === 'textarea') {
      inputHtml = `
        <textarea
          id="${id}"
          name="${name || ''}"
          class="hi-mobile-input hi-mobile-textarea"
          placeholder="${placeholder}"
          ${required ? 'required' : ''}
          ${minLength ? `minlength="${minLength}"` : ''}
          ${maxLength ? `maxlength="${maxLength}"` : ''}
          ${disabled ? 'disabled' : ''}
          rows="3"
        >${value}</textarea>
      `;
    } else if (type === 'select') {
      const options = config.options || [];
      inputHtml = `
        <select
          id="${id}"
          name="${name || ''}"
          class="hi-mobile-input hi-mobile-select"
          ${required ? 'required' : ''}
          ${disabled ? 'disabled' : ''}
        >
          <option value="" disabled ${!value ? 'selected' : ''}>${placeholder || 'Selecione...'}</option>
          ${options.map(opt => `
            <option value="${opt.value}" ${opt.value === value ? 'selected' : ''}>
              ${opt.label}
            </option>
          `).join('')}
        </select>
      `;
    } else {
      inputHtml = `
        <input
          type="${type}"
          id="${id}"
          name="${name || ''}"
          class="hi-mobile-input"
          placeholder="${placeholder}"
          ${required ? 'required' : ''}
          ${pattern ? `pattern="${pattern}"` : ''}
          ${minLength ? `minlength="${minLength}"` : ''}
          ${maxLength ? `maxlength="${maxLength}"` : ''}
          ${min !== undefined ? `min="${min}"` : ''}
          ${max !== undefined ? `max="${max}"` : ''}
          ${step ? `step="${step}"` : ''}
          ${value ? `value="${value}"` : ''}
          ${autocomplete ? `autocomplete="${autocomplete}"` : ''}
          ${inputmode ? `inputmode="${inputmode}"` : ''}
          ${disabled ? 'disabled' : ''}
        />
      `;
    }

    wrapper.innerHTML = `
      ${icon ? `<span class="hi-mobile-field__icon"><i class="fas ${icon}"></i></span>` : ''}
      <div class="hi-mobile-field__input-wrapper">
        ${inputHtml}
        <label for="${id}" class="hi-mobile-label">${label}${required ? ' <span class="hi-required">*</span>' : ''}</label>
        <span class="hi-mobile-field__focus-ring"></span>
      </div>
      ${helper ? `<span class="hi-mobile-field__helper">${helper}</span>` : ''}
      ${error ? `<span class="hi-mobile-field__error"><i class="fas fa-exclamation-circle"></i> ${error}</span>` : ''}
    `;

    // Event listeners
    const input = wrapper.querySelector('.hi-mobile-input');

    input.addEventListener('focus', () => {
      wrapper.classList.add('hi-mobile-field--focused');
    });

    input.addEventListener('blur', () => {
      wrapper.classList.remove('hi-mobile-field--focused');
      if (input.value) {
        wrapper.classList.add('hi-mobile-field--filled');
      } else {
        wrapper.classList.remove('hi-mobile-field--filled');
      }
    });

    // Marca como filled se já tiver valor
    if (value) {
      wrapper.classList.add('hi-mobile-field--filled');
    }

    return { wrapper, input, id };
  }

  /**
   * Cria date picker nativo otimizado
   */
  function createDatePicker(config) {
    const {
      name,
      label,
      required = false,
      min,
      max,
      value = '',
      disabled = false
    } = config;

    const id = config.id || generateId('hi-date');

    // Formata datas para o input
    const formatDate = (date) => {
      if (!date) return '';
      const d = new Date(date);
      return d.toISOString().split('T')[0];
    };

    const wrapper = document.createElement('div');
    wrapper.className = 'hi-mobile-field hi-mobile-field--date';
    if (disabled) wrapper.classList.add('hi-mobile-field--disabled');

    wrapper.innerHTML = `
      <div class="hi-mobile-field__input-wrapper">
        <input
          type="date"
          id="${id}"
          name="${name || ''}"
          class="hi-mobile-input hi-mobile-date"
          ${required ? 'required' : ''}
          ${min ? `min="${formatDate(min)}"` : ''}
          ${max ? `max="${formatDate(max)}"` : ''}
          ${value ? `value="${formatDate(value)}"` : ''}
          ${disabled ? 'disabled' : ''}
        />
        <label for="${id}" class="hi-mobile-label hi-mobile-label--always-up">
          ${label}${required ? ' <span class="hi-required">*</span>' : ''}
        </label>
        <span class="hi-mobile-field__icon hi-mobile-field__icon--right">
          <i class="fas fa-calendar-alt"></i>
        </span>
      </div>
    `;

    const input = wrapper.querySelector('.hi-mobile-input');

    // Para iOS, usa click para abrir o picker
    if (isIOS) {
      input.addEventListener('click', (e) => {
        input.showPicker && input.showPicker();
      });
    }

    return { wrapper, input, id };
  }

  /**
   * Cria time picker nativo otimizado
   */
  function createTimePicker(config) {
    const {
      name,
      label,
      required = false,
      min,
      max,
      step = 900, // 15 minutos
      value = '',
      disabled = false
    } = config;

    const id = config.id || generateId('hi-time');

    const wrapper = document.createElement('div');
    wrapper.className = 'hi-mobile-field hi-mobile-field--time';
    if (disabled) wrapper.classList.add('hi-mobile-field--disabled');

    wrapper.innerHTML = `
      <div class="hi-mobile-field__input-wrapper">
        <input
          type="time"
          id="${id}"
          name="${name || ''}"
          class="hi-mobile-input hi-mobile-time"
          ${required ? 'required' : ''}
          ${min ? `min="${min}"` : ''}
          ${max ? `max="${max}"` : ''}
          ${step ? `step="${step}"` : ''}
          ${value ? `value="${value}"` : ''}
          ${disabled ? 'disabled' : ''}
        />
        <label for="${id}" class="hi-mobile-label hi-mobile-label--always-up">
          ${label}${required ? ' <span class="hi-required">*</span>' : ''}
        </label>
        <span class="hi-mobile-field__icon hi-mobile-field__icon--right">
          <i class="fas fa-clock"></i>
        </span>
      </div>
    `;

    const input = wrapper.querySelector('.hi-mobile-input');

    return { wrapper, input, id };
  }

  /**
   * Cria grupo de radio buttons estilizados
   */
  function createRadioGroup(config) {
    const {
      name,
      label,
      options = [],
      value = '',
      required = false,
      layout = 'vertical' // vertical, horizontal, cards
    } = config;

    const groupId = generateId('hi-radio-group');

    const wrapper = document.createElement('fieldset');
    wrapper.className = `hi-mobile-radio-group hi-mobile-radio-group--${layout}`;

    wrapper.innerHTML = `
      <legend class="hi-mobile-radio-group__label">
        ${label}${required ? ' <span class="hi-required">*</span>' : ''}
      </legend>
      <div class="hi-mobile-radio-group__options">
        ${options.map((opt, i) => {
          const optId = `${groupId}-${i}`;
          const isSelected = opt.value === value;
          return `
            <label class="hi-mobile-radio ${layout === 'cards' ? 'hi-mobile-radio--card' : ''} ${isSelected ? 'hi-mobile-radio--selected' : ''}" for="${optId}">
              <input
                type="radio"
                id="${optId}"
                name="${name}"
                value="${opt.value}"
                ${isSelected ? 'checked' : ''}
                ${required ? 'required' : ''}
                class="hi-mobile-radio__input"
              />
              <span class="hi-mobile-radio__box">
                ${layout === 'cards' && opt.icon ? `<i class="fas ${opt.icon}"></i>` : ''}
              </span>
              <span class="hi-mobile-radio__label">
                ${opt.label}
                ${opt.description ? `<span class="hi-mobile-radio__description">${opt.description}</span>` : ''}
              </span>
            </label>
          `;
        }).join('')}
      </div>
    `;

    // Event listeners
    const radios = wrapper.querySelectorAll('.hi-mobile-radio__input');
    radios.forEach(radio => {
      radio.addEventListener('change', () => {
        wrapper.querySelectorAll('.hi-mobile-radio').forEach(label => {
          label.classList.toggle('hi-mobile-radio--selected', label.querySelector('input').checked);
        });

        // Haptic feedback
        if (navigator.vibrate) {
          navigator.vibrate(10);
        }
      });
    });

    return { wrapper, radios, name };
  }

  /**
   * Cria checkbox estilizado
   */
  function createCheckbox(config) {
    const {
      name,
      label,
      checked = false,
      required = false,
      disabled = false,
      description
    } = config;

    const id = config.id || generateId('hi-checkbox');

    const wrapper = document.createElement('div');
    wrapper.className = 'hi-mobile-checkbox-wrapper';
    if (disabled) wrapper.classList.add('hi-mobile-checkbox-wrapper--disabled');

    wrapper.innerHTML = `
      <label class="hi-mobile-checkbox" for="${id}">
        <input
          type="checkbox"
          id="${id}"
          name="${name || ''}"
          ${checked ? 'checked' : ''}
          ${required ? 'required' : ''}
          ${disabled ? 'disabled' : ''}
          class="hi-mobile-checkbox__input"
        />
        <span class="hi-mobile-checkbox__box">
          <i class="fas fa-check" aria-hidden="true"></i>
        </span>
        <span class="hi-mobile-checkbox__label">
          ${label}${required ? ' <span class="hi-required">*</span>' : ''}
          ${description ? `<span class="hi-mobile-checkbox__description">${description}</span>` : ''}
        </span>
      </label>
    `;

    const input = wrapper.querySelector('.hi-mobile-checkbox__input');

    input.addEventListener('change', () => {
      if (navigator.vibrate) {
        navigator.vibrate(10);
      }
    });

    return { wrapper, input, id };
  }

  /**
   * Cria switch/toggle
   */
  function createSwitch(config) {
    const {
      name,
      label,
      checked = false,
      disabled = false,
      description
    } = config;

    const id = config.id || generateId('hi-switch');

    const wrapper = document.createElement('div');
    wrapper.className = 'hi-mobile-switch-wrapper';
    if (disabled) wrapper.classList.add('hi-mobile-switch-wrapper--disabled');

    wrapper.innerHTML = `
      <label class="hi-mobile-switch" for="${id}">
        <span class="hi-mobile-switch__label">
          ${label}
          ${description ? `<span class="hi-mobile-switch__description">${description}</span>` : ''}
        </span>
        <span class="hi-mobile-switch__track">
          <input
            type="checkbox"
            id="${id}"
            name="${name || ''}"
            ${checked ? 'checked' : ''}
            ${disabled ? 'disabled' : ''}
            class="hi-mobile-switch__input"
            role="switch"
            aria-checked="${checked}"
          />
          <span class="hi-mobile-switch__thumb"></span>
        </span>
      </label>
    `;

    const input = wrapper.querySelector('.hi-mobile-switch__input');

    input.addEventListener('change', () => {
      input.setAttribute('aria-checked', input.checked);
      if (navigator.vibrate) {
        navigator.vibrate(15);
      }
    });

    return { wrapper, input, id };
  }

  /**
   * Aprimora um formulário existente
   */
  function enhanceForm(form, options = {}) {
    const formEl = typeof form === 'string' ? document.querySelector(form) : form;
    if (!formEl) return;

    const opts = { ...defaults, ...options };

    // Adiciona classe
    formEl.classList.add('hi-mobile-form');

    // Scroll into view no focus (evita teclado cobrir input)
    if (opts.scrollIntoView) {
      formEl.querySelectorAll('input, textarea, select').forEach(input => {
        input.addEventListener('focus', () => {
          setTimeout(() => {
            input.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }, 300);
        });
      });
    }

    // Auto advance para inputs com maxLength
    if (opts.autoAdvance) {
      formEl.querySelectorAll('input[maxlength]').forEach(input => {
        input.addEventListener('input', () => {
          if (input.value.length >= input.maxLength) {
            const nextInput = getNextFocusable(formEl, input);
            if (nextInput) {
              nextInput.focus();
            }
          }
        });
      });
    }

    // Previne zoom no iOS ao focar inputs pequenos
    if (isIOS) {
      formEl.querySelectorAll('input, select, textarea').forEach(input => {
        if (!input.style.fontSize || parseFloat(input.style.fontSize) < 16) {
          input.style.fontSize = '16px';
        }
      });
    }

    return formEl;
  }

  /**
   * Obtém próximo elemento focável
   */
  function getNextFocusable(container, current) {
    const focusables = Array.from(
      container.querySelectorAll('input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])')
    );

    const currentIndex = focusables.indexOf(current);
    if (currentIndex >= 0 && currentIndex < focusables.length - 1) {
      return focusables[currentIndex + 1];
    }
    return null;
  }

  /**
   * API pública
   */
  const HiMobileForm = {
    enhance: enhanceForm,
    createInput: createFloatingInput,
    createDatePicker,
    createTimePicker,
    createRadioGroup,
    createCheckbox,
    createSwitch,

    /**
     * Cria um formulário completo
     */
    createForm(config) {
      const {
        id,
        fields = [],
        submitLabel = 'Enviar',
        cancelLabel = 'Cancelar',
        onSubmit,
        onCancel,
        showCancel = false
      } = config;

      const form = document.createElement('form');
      form.id = id || generateId('hi-form');
      form.className = 'hi-mobile-form';

      // Adiciona campos
      fields.forEach(field => {
        let component;

        switch (field.type) {
          case 'date':
            component = this.createDatePicker(field);
            break;
          case 'time':
            component = this.createTimePicker(field);
            break;
          case 'radio':
            component = this.createRadioGroup(field);
            break;
          case 'checkbox':
            component = this.createCheckbox(field);
            break;
          case 'switch':
            component = this.createSwitch(field);
            break;
          default:
            component = this.createInput(field);
        }

        form.appendChild(component.wrapper);
      });

      // Botões
      const actions = document.createElement('div');
      actions.className = 'hi-mobile-form__actions';
      actions.innerHTML = `
        ${showCancel ? `
          <button type="button" class="hi-btn hi-btn--outline hi-mobile-form__cancel">
            ${cancelLabel}
          </button>
        ` : ''}
        <button type="submit" class="hi-btn hi-btn--primary hi-mobile-form__submit">
          ${submitLabel}
        </button>
      `;
      form.appendChild(actions);

      // Events
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        if (typeof onSubmit === 'function') {
          const formData = new FormData(form);
          const data = Object.fromEntries(formData.entries());
          onSubmit(data, form);
        }
      });

      if (showCancel) {
        actions.querySelector('.hi-mobile-form__cancel').addEventListener('click', () => {
          if (typeof onCancel === 'function') {
            onCancel(form);
          }
        });
      }

      // Enhance
      this.enhance(form);

      return form;
    },

    /**
     * Valida um formulário
     */
    validate(form) {
      const formEl = typeof form === 'string' ? document.querySelector(form) : form;
      if (!formEl) return false;

      // Limpa erros anteriores
      formEl.querySelectorAll('.hi-mobile-field--error').forEach(field => {
        field.classList.remove('hi-mobile-field--error');
        const errorEl = field.querySelector('.hi-mobile-field__error');
        if (errorEl) errorEl.remove();
      });

      // Valida
      const isValid = formEl.checkValidity();

      if (!isValid) {
        // Mostra erros
        formEl.querySelectorAll(':invalid').forEach(input => {
          const field = input.closest('.hi-mobile-field');
          if (field) {
            field.classList.add('hi-mobile-field--error');

            // Adiciona mensagem de erro
            let message = input.validationMessage;
            if (input.validity.valueMissing) {
              message = 'Este campo é obrigatório';
            } else if (input.validity.typeMismatch) {
              message = 'Formato inválido';
            } else if (input.validity.patternMismatch) {
              message = 'Formato inválido';
            }

            const errorEl = document.createElement('span');
            errorEl.className = 'hi-mobile-field__error';
            errorEl.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
            field.appendChild(errorEl);
          }
        });

        // Foca no primeiro campo inválido
        const firstInvalid = formEl.querySelector(':invalid');
        if (firstInvalid) {
          firstInvalid.focus();
          firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        // Haptic feedback
        if (navigator.vibrate) {
          navigator.vibrate([30, 50, 30]);
        }
      }

      return isValid;
    },

    /**
     * Limpa um formulário
     */
    reset(form) {
      const formEl = typeof form === 'string' ? document.querySelector(form) : form;
      if (!formEl) return;

      formEl.reset();

      // Remove estados
      formEl.querySelectorAll('.hi-mobile-field').forEach(field => {
        field.classList.remove('hi-mobile-field--error', 'hi-mobile-field--filled', 'hi-mobile-field--focused');
      });

      formEl.querySelectorAll('.hi-mobile-field__error').forEach(el => el.remove());
    }
  };

  // Estilos do componente
  const styles = document.createElement('style');
  styles.textContent = `
    /* Form Base */
    .hi-mobile-form {
      display: flex;
      flex-direction: column;
      gap: var(--hi-space-4, 16px);
    }

    /* Field Wrapper */
    .hi-mobile-field {
      position: relative;
      display: flex;
      flex-direction: column;
    }

    .hi-mobile-field__input-wrapper {
      position: relative;
      display: flex;
      align-items: center;
    }

    /* Input Base */
    .hi-mobile-input {
      width: 100%;
      min-height: var(--hi-touch-target-min, 44px);
      padding: 20px 16px 8px;
      font-size: 16px; /* Prevents zoom on iOS */
      font-family: inherit;
      color: var(--hi-text-primary, #1f2937);
      background-color: var(--hi-bg-secondary, #f9fafb);
      border: 2px solid var(--hi-border-light, #e5e7eb);
      border-radius: var(--hi-radius-lg, 12px);
      outline: none;
      transition: all var(--hi-transition-fast, 150ms);
      -webkit-appearance: none;
      appearance: none;
    }

    .hi-mobile-input:focus {
      border-color: var(--hi-primary, #3b82f6);
      background-color: white;
    }

    .hi-mobile-field--error .hi-mobile-input {
      border-color: var(--hi-error, #ef4444);
    }

    .hi-mobile-input:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    /* Textarea */
    .hi-mobile-textarea {
      resize: vertical;
      min-height: 100px;
    }

    /* Select */
    .hi-mobile-select {
      cursor: pointer;
      padding-right: 40px;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%239ca3af'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 12px center;
      background-size: 20px;
    }

    /* Floating Label */
    .hi-mobile-label {
      position: absolute;
      left: 16px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 16px;
      color: var(--hi-text-muted, #9ca3af);
      pointer-events: none;
      transition: all var(--hi-transition-fast, 150ms);
      background: transparent;
    }

    .hi-mobile-textarea + .hi-mobile-label {
      top: 20px;
      transform: none;
    }

    .hi-mobile-label--always-up,
    .hi-mobile-field--focused .hi-mobile-label,
    .hi-mobile-field--filled .hi-mobile-label,
    .hi-mobile-input:not(:placeholder-shown) + .hi-mobile-label {
      top: 8px;
      transform: none;
      font-size: 12px;
      color: var(--hi-primary, #3b82f6);
    }

    .hi-mobile-field--error .hi-mobile-label {
      color: var(--hi-error, #ef4444);
    }

    /* Focus Ring */
    .hi-mobile-field__focus-ring {
      position: absolute;
      inset: -2px;
      border-radius: calc(var(--hi-radius-lg, 12px) + 2px);
      pointer-events: none;
      opacity: 0;
      transition: opacity var(--hi-transition-fast, 150ms);
    }

    .hi-mobile-field--focused .hi-mobile-field__focus-ring {
      opacity: 1;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
    }

    .hi-mobile-field--error.hi-mobile-field--focused .hi-mobile-field__focus-ring {
      box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2);
    }

    /* Icons */
    .hi-mobile-field__icon {
      position: absolute;
      left: 16px;
      color: var(--hi-text-muted, #9ca3af);
      pointer-events: none;
      z-index: 1;
    }

    .hi-mobile-field__icon--right {
      left: auto;
      right: 16px;
    }

    .hi-mobile-field__icon + .hi-mobile-field__input-wrapper .hi-mobile-input {
      padding-left: 44px;
    }

    .hi-mobile-field__icon + .hi-mobile-field__input-wrapper .hi-mobile-label {
      left: 44px;
    }

    /* Helper & Error */
    .hi-mobile-field__helper,
    .hi-mobile-field__error {
      margin-top: var(--hi-space-1, 4px);
      padding-left: 16px;
      font-size: 12px;
    }

    .hi-mobile-field__helper {
      color: var(--hi-text-muted, #9ca3af);
    }

    .hi-mobile-field__error {
      color: var(--hi-error, #ef4444);
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .hi-required {
      color: var(--hi-error, #ef4444);
    }

    /* Date & Time */
    .hi-mobile-date,
    .hi-mobile-time {
      padding-right: 44px;
    }

    .hi-mobile-date::-webkit-calendar-picker-indicator,
    .hi-mobile-time::-webkit-calendar-picker-indicator {
      opacity: 0;
      position: absolute;
      right: 0;
      width: 100%;
      height: 100%;
      cursor: pointer;
    }

    /* Radio Group */
    .hi-mobile-radio-group {
      border: none;
      padding: 0;
      margin: 0;
    }

    .hi-mobile-radio-group__label {
      font-size: 14px;
      font-weight: var(--hi-font-weight-medium, 500);
      color: var(--hi-text-secondary, #6b7280);
      margin-bottom: var(--hi-space-3, 12px);
    }

    .hi-mobile-radio-group__options {
      display: flex;
      flex-direction: column;
      gap: var(--hi-space-2, 8px);
    }

    .hi-mobile-radio-group--horizontal .hi-mobile-radio-group__options {
      flex-direction: row;
      flex-wrap: wrap;
    }

    .hi-mobile-radio-group--cards .hi-mobile-radio-group__options {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: var(--hi-space-3, 12px);
    }

    /* Radio */
    .hi-mobile-radio {
      display: flex;
      align-items: flex-start;
      gap: var(--hi-space-3, 12px);
      padding: var(--hi-space-3, 12px);
      background-color: var(--hi-bg-secondary, #f9fafb);
      border: 2px solid var(--hi-border-light, #e5e7eb);
      border-radius: var(--hi-radius-lg, 12px);
      cursor: pointer;
      transition: all var(--hi-transition-fast, 150ms);
      min-height: var(--hi-touch-target-min, 44px);
    }

    .hi-mobile-radio:hover {
      border-color: var(--hi-primary-light, #93c5fd);
    }

    .hi-mobile-radio--selected {
      border-color: var(--hi-primary, #3b82f6);
      background-color: var(--hi-primary-50, #eff6ff);
    }

    .hi-mobile-radio__input {
      position: absolute;
      opacity: 0;
      pointer-events: none;
    }

    .hi-mobile-radio__box {
      flex-shrink: 0;
      width: 20px;
      height: 20px;
      border: 2px solid var(--hi-border, #d1d5db);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all var(--hi-transition-fast, 150ms);
    }

    .hi-mobile-radio--selected .hi-mobile-radio__box {
      border-color: var(--hi-primary, #3b82f6);
      background-color: var(--hi-primary, #3b82f6);
    }

    .hi-mobile-radio--selected .hi-mobile-radio__box::after {
      content: '';
      width: 8px;
      height: 8px;
      background-color: white;
      border-radius: 50%;
    }

    .hi-mobile-radio__label {
      font-size: 14px;
      color: var(--hi-text-primary, #1f2937);
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .hi-mobile-radio__description {
      font-size: 12px;
      color: var(--hi-text-muted, #9ca3af);
    }

    /* Radio Card */
    .hi-mobile-radio--card {
      flex-direction: column;
      align-items: center;
      text-align: center;
      padding: var(--hi-space-4, 16px);
    }

    .hi-mobile-radio--card .hi-mobile-radio__box {
      width: 40px;
      height: 40px;
      font-size: 1.25rem;
      color: var(--hi-text-muted, #9ca3af);
    }

    .hi-mobile-radio--card.hi-mobile-radio--selected .hi-mobile-radio__box {
      color: white;
    }

    .hi-mobile-radio--card .hi-mobile-radio__box::after {
      display: none;
    }

    /* Checkbox */
    .hi-mobile-checkbox-wrapper {
      display: block;
    }

    .hi-mobile-checkbox {
      display: flex;
      align-items: flex-start;
      gap: var(--hi-space-3, 12px);
      padding: var(--hi-space-3, 12px);
      cursor: pointer;
      min-height: var(--hi-touch-target-min, 44px);
    }

    .hi-mobile-checkbox__input {
      position: absolute;
      opacity: 0;
      pointer-events: none;
    }

    .hi-mobile-checkbox__box {
      flex-shrink: 0;
      width: 24px;
      height: 24px;
      border: 2px solid var(--hi-border, #d1d5db);
      border-radius: var(--hi-radius-md, 8px);
      display: flex;
      align-items: center;
      justify-content: center;
      color: transparent;
      transition: all var(--hi-transition-fast, 150ms);
    }

    .hi-mobile-checkbox__input:checked + .hi-mobile-checkbox__box {
      border-color: var(--hi-primary, #3b82f6);
      background-color: var(--hi-primary, #3b82f6);
      color: white;
    }

    .hi-mobile-checkbox__input:focus-visible + .hi-mobile-checkbox__box {
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
    }

    .hi-mobile-checkbox__label {
      font-size: 14px;
      color: var(--hi-text-primary, #1f2937);
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .hi-mobile-checkbox__description {
      font-size: 12px;
      color: var(--hi-text-muted, #9ca3af);
    }

    /* Switch */
    .hi-mobile-switch-wrapper {
      display: block;
    }

    .hi-mobile-switch {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--hi-space-4, 16px);
      padding: var(--hi-space-3, 12px);
      cursor: pointer;
      min-height: var(--hi-touch-target-min, 44px);
    }

    .hi-mobile-switch__label {
      font-size: 14px;
      color: var(--hi-text-primary, #1f2937);
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .hi-mobile-switch__description {
      font-size: 12px;
      color: var(--hi-text-muted, #9ca3af);
    }

    .hi-mobile-switch__track {
      position: relative;
      flex-shrink: 0;
      width: 52px;
      height: 32px;
      background-color: var(--hi-gray-300, #d1d5db);
      border-radius: 16px;
      transition: background-color var(--hi-transition-fast, 150ms);
    }

    .hi-mobile-switch__input {
      position: absolute;
      opacity: 0;
      width: 100%;
      height: 100%;
      cursor: pointer;
    }

    .hi-mobile-switch__thumb {
      position: absolute;
      top: 4px;
      left: 4px;
      width: 24px;
      height: 24px;
      background-color: white;
      border-radius: 50%;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
      transition: transform var(--hi-transition-fast, 150ms);
    }

    .hi-mobile-switch__input:checked ~ .hi-mobile-switch__thumb {
      transform: translateX(20px);
    }

    .hi-mobile-switch__input:checked + .hi-mobile-switch__track,
    .hi-mobile-switch__track:has(.hi-mobile-switch__input:checked) {
      background-color: var(--hi-primary, #3b82f6);
    }

    .hi-mobile-switch__input:focus-visible ~ .hi-mobile-switch__thumb {
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
    }

    /* Fix for browsers that don't support :has() */
    .hi-mobile-switch__input:checked ~ .hi-mobile-switch__thumb {
      transform: translateX(20px);
    }

    .hi-mobile-switch:has(.hi-mobile-switch__input:checked) .hi-mobile-switch__track {
      background-color: var(--hi-primary, #3b82f6);
    }

    /* Form Actions */
    .hi-mobile-form__actions {
      display: flex;
      gap: var(--hi-space-3, 12px);
      margin-top: var(--hi-space-4, 16px);
      padding-top: var(--hi-space-4, 16px);
      border-top: 1px solid var(--hi-border-light, #e5e7eb);
    }

    .hi-mobile-form__actions .hi-btn {
      flex: 1;
      min-height: var(--hi-touch-target-min, 44px);
    }

    /* Animations */
    @keyframes shake {
      0%, 100% { transform: translateX(0); }
      25% { transform: translateX(-4px); }
      75% { transform: translateX(4px); }
    }

    .hi-mobile-field--error .hi-mobile-input {
      animation: shake 200ms ease-in-out;
    }
  `;
  document.head.appendChild(styles);

  // Expõe globalmente
  global.HiMobileForm = HiMobileForm;

})(typeof window !== 'undefined' ? window : this);
