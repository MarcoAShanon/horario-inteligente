/**
 * HORÁRIO INTELIGENTE - Validação de Formulários
 * Sistema de validação em tempo real com feedback visual
 *
 * Uso:
 *   // Inicializar validação em um formulário
 *   const validator = HiValidation.init('#meu-form', {
 *     fields: {
 *       email: { required: true, email: true },
 *       senha: { required: true, minLength: 8, password: true },
 *       telefone: { required: true, phone: true, mask: 'phone' },
 *       cpf: { cpf: true, mask: 'cpf' }
 *     },
 *     onSubmit: (data, form) => { ... },
 *     onError: (errors, form) => { ... }
 *   });
 *
 *   // Validar manualmente
 *   const isValid = validator.validate();
 *   const errors = validator.getErrors();
 */

(function(global) {
  'use strict';

  // Mensagens de erro padrão
  const DEFAULT_MESSAGES = {
    required: 'Este campo é obrigatório',
    email: 'Digite um email válido',
    minLength: 'Mínimo de {min} caracteres',
    maxLength: 'Máximo de {max} caracteres',
    min: 'Valor mínimo é {min}',
    max: 'Valor máximo é {max}',
    pattern: 'Formato inválido',
    phone: 'Digite um telefone válido',
    cpf: 'Digite um CPF válido',
    cnpj: 'Digite um CNPJ válido',
    crm: 'Digite um CRM válido (ex: 12345-SP)',
    date: 'Digite uma data válida',
    url: 'Digite uma URL válida',
    match: 'Os campos não coincidem',
    password: 'Senha muito fraca',
    custom: 'Valor inválido'
  };

  // Padrões de regex
  const PATTERNS = {
    email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    phone: /^\(?[1-9]{2}\)?\s?(?:9\d{4}|\d{4})-?\d{4}$/,
    cpf: /^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$/,
    cnpj: /^\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}$/,
    crm: /^\d{4,6}-?[A-Z]{2}$/i,
    date: /^\d{2}\/\d{2}\/\d{4}$/,
    url: /^https?:\/\/.+/i
  };

  // Máscaras de input
  const MASKS = {
    phone: (value) => {
      const digits = value.replace(/\D/g, '').slice(0, 11);
      if (digits.length <= 2) return digits;
      if (digits.length <= 6) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
      if (digits.length <= 10) return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
      return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
    },
    cpf: (value) => {
      const digits = value.replace(/\D/g, '').slice(0, 11);
      if (digits.length <= 3) return digits;
      if (digits.length <= 6) return `${digits.slice(0, 3)}.${digits.slice(3)}`;
      if (digits.length <= 9) return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
      return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
    },
    cnpj: (value) => {
      const digits = value.replace(/\D/g, '').slice(0, 14);
      if (digits.length <= 2) return digits;
      if (digits.length <= 5) return `${digits.slice(0, 2)}.${digits.slice(2)}`;
      if (digits.length <= 8) return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5)}`;
      if (digits.length <= 12) return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8)}`;
      return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
    },
    crm: (value) => {
      const clean = value.replace(/[^0-9A-Za-z]/g, '').toUpperCase();
      const digits = clean.replace(/[A-Z]/g, '').slice(0, 6);
      const letters = clean.replace(/[0-9]/g, '').slice(0, 2);
      if (!digits) return '';
      if (!letters) return digits;
      return `${digits}-${letters}`;
    },
    date: (value) => {
      const digits = value.replace(/\D/g, '').slice(0, 8);
      if (digits.length <= 2) return digits;
      if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
      return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
    },
    currency: (value) => {
      const digits = value.replace(/\D/g, '');
      if (!digits) return '';
      const number = parseInt(digits, 10) / 100;
      return number.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    },
    cep: (value) => {
      const digits = value.replace(/\D/g, '').slice(0, 8);
      if (digits.length <= 5) return digits;
      return `${digits.slice(0, 5)}-${digits.slice(5)}`;
    }
  };

  /**
   * Valida CPF
   */
  function isValidCPF(cpf) {
    const digits = cpf.replace(/\D/g, '');
    if (digits.length !== 11 || /^(\d)\1+$/.test(digits)) return false;

    let sum = 0;
    for (let i = 0; i < 9; i++) sum += parseInt(digits[i]) * (10 - i);
    let remainder = (sum * 10) % 11;
    if (remainder === 10 || remainder === 11) remainder = 0;
    if (remainder !== parseInt(digits[9])) return false;

    sum = 0;
    for (let i = 0; i < 10; i++) sum += parseInt(digits[i]) * (11 - i);
    remainder = (sum * 10) % 11;
    if (remainder === 10 || remainder === 11) remainder = 0;

    return remainder === parseInt(digits[10]);
  }

  /**
   * Valida CNPJ
   */
  function isValidCNPJ(cnpj) {
    const digits = cnpj.replace(/\D/g, '');
    if (digits.length !== 14 || /^(\d)\1+$/.test(digits)) return false;

    const calcDigit = (digits, length) => {
      let sum = 0;
      let pos = length - 7;
      for (let i = length; i >= 1; i--) {
        sum += parseInt(digits[length - i]) * pos--;
        if (pos < 2) pos = 9;
      }
      const result = sum % 11 < 2 ? 0 : 11 - (sum % 11);
      return result;
    };

    if (calcDigit(digits, 12) !== parseInt(digits[12])) return false;
    if (calcDigit(digits, 13) !== parseInt(digits[13])) return false;

    return true;
  }

  /**
   * Calcula força da senha
   */
  function getPasswordStrength(password) {
    let strength = 0;
    const checks = {
      length: password.length >= 8,
      lowercase: /[a-z]/.test(password),
      uppercase: /[A-Z]/.test(password),
      numbers: /\d/.test(password),
      special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
    };

    strength = Object.values(checks).filter(Boolean).length;

    return {
      score: strength,
      checks,
      label: strength <= 1 ? 'Muito fraca' :
             strength === 2 ? 'Fraca' :
             strength === 3 ? 'Média' :
             strength === 4 ? 'Forte' : 'Muito forte',
      color: strength <= 1 ? 'var(--hi-error)' :
             strength === 2 ? 'var(--hi-warning)' :
             strength === 3 ? 'var(--hi-warning)' :
             'var(--hi-success)'
    };
  }

  /**
   * Classe Validator
   */
  class FormValidator {
    constructor(form, options = {}) {
      this.form = typeof form === 'string' ? document.querySelector(form) : form;
      if (!this.form) {
        throw new Error('Formulário não encontrado');
      }

      this.options = {
        validateOnBlur: true,
        validateOnInput: true,
        showPasswordStrength: true,
        ...options
      };

      this.fields = options.fields || {};
      this.errors = {};
      this.touched = {};

      this._init();
    }

    /**
     * Inicializa o validador
     */
    _init() {
      // Previne submit padrão
      this.form.addEventListener('submit', (e) => {
        e.preventDefault();
        this._handleSubmit();
      });

      // Configura campos
      Object.keys(this.fields).forEach(fieldName => {
        const field = this.form.querySelector(`[name="${fieldName}"]`);
        if (!field) return;

        const config = this.fields[fieldName];

        // Aplica máscara se definida
        if (config.mask && MASKS[config.mask]) {
          field.addEventListener('input', (e) => {
            const cursorPos = e.target.selectionStart;
            const oldLength = e.target.value.length;
            e.target.value = MASKS[config.mask](e.target.value);
            const newLength = e.target.value.length;
            const newPos = cursorPos + (newLength - oldLength);
            e.target.setSelectionRange(newPos, newPos);
          });
        }

        // Valida no blur
        if (this.options.validateOnBlur) {
          field.addEventListener('blur', () => {
            this.touched[fieldName] = true;
            this._validateField(fieldName);
          });
        }

        // Valida durante digitação (com debounce)
        if (this.options.validateOnInput) {
          let debounceTimer;
          field.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
              if (this.touched[fieldName]) {
                this._validateField(fieldName);
              }

              // Mostra força da senha
              if (config.password && this.options.showPasswordStrength) {
                this._showPasswordStrength(field);
              }
            }, 300);
          });
        }
      });
    }

    /**
     * Valida um campo específico
     */
    _validateField(fieldName) {
      const field = this.form.querySelector(`[name="${fieldName}"]`);
      if (!field) return true;

      const config = this.fields[fieldName];
      const value = field.value.trim();
      const errors = [];

      // Required
      if (config.required && !value) {
        errors.push(config.messages?.required || DEFAULT_MESSAGES.required);
      }

      // Apenas valida o resto se tem valor
      if (value) {
        // Min Length
        if (config.minLength && value.length < config.minLength) {
          errors.push((config.messages?.minLength || DEFAULT_MESSAGES.minLength)
            .replace('{min}', config.minLength));
        }

        // Max Length
        if (config.maxLength && value.length > config.maxLength) {
          errors.push((config.messages?.maxLength || DEFAULT_MESSAGES.maxLength)
            .replace('{max}', config.maxLength));
        }

        // Min Value
        if (config.min !== undefined && parseFloat(value) < config.min) {
          errors.push((config.messages?.min || DEFAULT_MESSAGES.min)
            .replace('{min}', config.min));
        }

        // Max Value
        if (config.max !== undefined && parseFloat(value) > config.max) {
          errors.push((config.messages?.max || DEFAULT_MESSAGES.max)
            .replace('{max}', config.max));
        }

        // Email
        if (config.email && !PATTERNS.email.test(value)) {
          errors.push(config.messages?.email || DEFAULT_MESSAGES.email);
        }

        // Phone
        if (config.phone && !PATTERNS.phone.test(value)) {
          errors.push(config.messages?.phone || DEFAULT_MESSAGES.phone);
        }

        // CPF
        if (config.cpf) {
          if (!PATTERNS.cpf.test(value) || !isValidCPF(value)) {
            errors.push(config.messages?.cpf || DEFAULT_MESSAGES.cpf);
          }
        }

        // CNPJ
        if (config.cnpj) {
          if (!PATTERNS.cnpj.test(value) || !isValidCNPJ(value)) {
            errors.push(config.messages?.cnpj || DEFAULT_MESSAGES.cnpj);
          }
        }

        // CRM
        if (config.crm && !PATTERNS.crm.test(value)) {
          errors.push(config.messages?.crm || DEFAULT_MESSAGES.crm);
        }

        // URL
        if (config.url && !PATTERNS.url.test(value)) {
          errors.push(config.messages?.url || DEFAULT_MESSAGES.url);
        }

        // Pattern customizado
        if (config.pattern) {
          const regex = config.pattern instanceof RegExp ? config.pattern : new RegExp(config.pattern);
          if (!regex.test(value)) {
            errors.push(config.messages?.pattern || DEFAULT_MESSAGES.pattern);
          }
        }

        // Match (para confirmar senha, etc)
        if (config.match) {
          const matchField = this.form.querySelector(`[name="${config.match}"]`);
          if (matchField && matchField.value !== value) {
            errors.push(config.messages?.match || DEFAULT_MESSAGES.match);
          }
        }

        // Password strength
        if (config.password) {
          const strength = getPasswordStrength(value);
          if (strength.score < (config.minPasswordStrength || 3)) {
            errors.push(config.messages?.password || DEFAULT_MESSAGES.password);
          }
        }

        // Validador customizado
        if (config.custom && typeof config.custom === 'function') {
          const customError = config.custom(value, this.form);
          if (customError) {
            errors.push(customError);
          }
        }
      }

      // Atualiza estado
      if (errors.length > 0) {
        this.errors[fieldName] = errors[0];
        this._showFieldError(field, errors[0]);
      } else {
        delete this.errors[fieldName];
        this._showFieldSuccess(field);
      }

      return errors.length === 0;
    }

    /**
     * Mostra erro no campo
     */
    _showFieldError(field, message) {
      const wrapper = field.closest('.hi-form-group') || field.parentElement;

      // Remove estados anteriores
      field.classList.remove('hi-input--valid');
      field.classList.add('hi-input--invalid');

      // Remove erro anterior se existir
      const existingError = wrapper.querySelector('.hi-form-error');
      if (existingError) existingError.remove();

      // Adiciona mensagem de erro
      const errorEl = document.createElement('span');
      errorEl.className = 'hi-form-error hi-animate-fade-in';
      errorEl.innerHTML = `<i class="fas fa-exclamation-circle" aria-hidden="true"></i> ${this._escapeHtml(message)}`;
      wrapper.appendChild(errorEl);

      // ARIA
      field.setAttribute('aria-invalid', 'true');
      field.setAttribute('aria-describedby', `${field.name}-error`);
      errorEl.id = `${field.name}-error`;
    }

    /**
     * Mostra sucesso no campo
     */
    _showFieldSuccess(field) {
      const wrapper = field.closest('.hi-form-group') || field.parentElement;

      // Atualiza classes
      field.classList.remove('hi-input--invalid');
      field.classList.add('hi-input--valid');

      // Remove mensagem de erro
      const existingError = wrapper.querySelector('.hi-form-error');
      if (existingError) existingError.remove();

      // ARIA
      field.setAttribute('aria-invalid', 'false');
      field.removeAttribute('aria-describedby');
    }

    /**
     * Mostra indicador de força da senha
     */
    _showPasswordStrength(field) {
      const wrapper = field.closest('.hi-form-group') || field.parentElement;
      const strength = getPasswordStrength(field.value);

      // Remove indicador anterior
      let indicator = wrapper.querySelector('.hi-password-strength');
      if (!indicator) {
        indicator = document.createElement('div');
        indicator.className = 'hi-password-strength';
        indicator.innerHTML = `
          <div class="hi-password-strength__bar">
            <div class="hi-password-strength__fill"></div>
          </div>
          <span class="hi-password-strength__label"></span>
        `;
        wrapper.appendChild(indicator);
      }

      const fill = indicator.querySelector('.hi-password-strength__fill');
      const label = indicator.querySelector('.hi-password-strength__label');

      fill.style.width = `${(strength.score / 5) * 100}%`;
      fill.style.backgroundColor = strength.color;
      label.textContent = strength.label;
      label.style.color = strength.color;
    }

    /**
     * Escapa HTML
     */
    _escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    /**
     * Valida todos os campos
     */
    validate() {
      let isValid = true;

      Object.keys(this.fields).forEach(fieldName => {
        this.touched[fieldName] = true;
        if (!this._validateField(fieldName)) {
          isValid = false;
        }
      });

      return isValid;
    }

    /**
     * Obtém erros atuais
     */
    getErrors() {
      return { ...this.errors };
    }

    /**
     * Obtém dados do formulário
     */
    getData() {
      const formData = new FormData(this.form);
      const data = {};
      formData.forEach((value, key) => {
        data[key] = value;
      });
      return data;
    }

    /**
     * Handler de submit
     */
    _handleSubmit() {
      if (this.validate()) {
        if (typeof this.options.onSubmit === 'function') {
          this.options.onSubmit(this.getData(), this.form);
        }
      } else {
        if (typeof this.options.onError === 'function') {
          this.options.onError(this.getErrors(), this.form);
        }

        // Foca no primeiro campo com erro
        const firstError = Object.keys(this.errors)[0];
        if (firstError) {
          const field = this.form.querySelector(`[name="${firstError}"]`);
          if (field) field.focus();
        }
      }
    }

    /**
     * Reseta o formulário
     */
    reset() {
      this.form.reset();
      this.errors = {};
      this.touched = {};

      // Remove todos os estados visuais
      this.form.querySelectorAll('.hi-input--valid, .hi-input--invalid').forEach(el => {
        el.classList.remove('hi-input--valid', 'hi-input--invalid');
        el.removeAttribute('aria-invalid');
        el.removeAttribute('aria-describedby');
      });

      this.form.querySelectorAll('.hi-form-error, .hi-password-strength').forEach(el => {
        el.remove();
      });
    }

    /**
     * Destrói o validador
     */
    destroy() {
      this.reset();
      // Remove event listeners seria necessário se guardássemos referências
    }
  }

  /**
   * API pública
   */
  const HiValidation = {
    /**
     * Inicializa validação em um formulário
     * @param {string|HTMLFormElement} form - Formulário ou seletor
     * @param {object} options - Opções de configuração
     * @returns {FormValidator}
     */
    init(form, options) {
      return new FormValidator(form, options);
    },

    /**
     * Aplica máscara a um input
     * @param {string|HTMLInputElement} input - Input ou seletor
     * @param {string} maskName - Nome da máscara (phone, cpf, cnpj, etc)
     */
    applyMask(input, maskName) {
      const el = typeof input === 'string' ? document.querySelector(input) : input;
      if (!el || !MASKS[maskName]) return;

      el.addEventListener('input', (e) => {
        const cursorPos = e.target.selectionStart;
        const oldLength = e.target.value.length;
        e.target.value = MASKS[maskName](e.target.value);
        const newLength = e.target.value.length;
        const newPos = cursorPos + (newLength - oldLength);
        e.target.setSelectionRange(newPos, newPos);
      });
    },

    /**
     * Valida CPF
     * @param {string} cpf
     * @returns {boolean}
     */
    isValidCPF(cpf) {
      return isValidCPF(cpf);
    },

    /**
     * Valida CNPJ
     * @param {string} cnpj
     * @returns {boolean}
     */
    isValidCNPJ(cnpj) {
      return isValidCNPJ(cnpj);
    },

    /**
     * Obtém força da senha
     * @param {string} password
     * @returns {object}
     */
    getPasswordStrength(password) {
      return getPasswordStrength(password);
    },

    /**
     * Máscaras disponíveis
     */
    masks: MASKS,

    /**
     * Padrões de regex
     */
    patterns: PATTERNS,

    /**
     * Mensagens padrão
     */
    messages: DEFAULT_MESSAGES
  };

  // Estilos adicionais para força de senha
  const style = document.createElement('style');
  style.textContent = `
    .hi-password-strength {
      display: flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      margin-top: var(--hi-space-2, 8px);
    }

    .hi-password-strength__bar {
      flex: 1;
      height: 4px;
      background-color: var(--hi-gray-200, #e5e7eb);
      border-radius: 2px;
      overflow: hidden;
    }

    .hi-password-strength__fill {
      height: 100%;
      width: 0;
      transition: width 0.3s, background-color 0.3s;
      border-radius: 2px;
    }

    .hi-password-strength__label {
      font-size: var(--hi-font-size-xs, 12px);
      font-weight: var(--hi-font-weight-medium, 500);
      white-space: nowrap;
    }
  `;
  document.head.appendChild(style);

  // Expõe globalmente
  global.HiValidation = HiValidation;

  // Também expõe como módulo ES6 se suportado
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = HiValidation;
  }

})(typeof window !== 'undefined' ? window : this);
