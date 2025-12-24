/**
 * HORÁRIO INTELIGENTE - Modal Acessível
 * Componente de modal com suporte a acessibilidade completo
 *
 * Uso:
 *   // Criar modal programaticamente
 *   const modal = HiModal.create({
 *     title: 'Confirmar Agendamento',
 *     content: '<p>Deseja confirmar?</p>',
 *     size: 'sm', // sm, md (default), lg, xl, full
 *     buttons: [
 *       { text: 'Cancelar', variant: 'secondary', action: 'close' },
 *       { text: 'Confirmar', variant: 'primary', action: () => { ... } }
 *     ]
 *   });
 *   modal.open();
 *
 *   // Ou abrir modal existente no HTML
 *   HiModal.open('meu-modal-id');
 *
 *   // Fechar modal
 *   HiModal.close('meu-modal-id');
 */

(function(global) {
  'use strict';

  // Armazena modais ativos
  const activeModals = new Map();
  let modalCounter = 0;

  // Elementos focáveis
  const FOCUSABLE_SELECTORS = [
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    'a[href]',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ');

  /**
   * Classe Modal
   */
  class Modal {
    constructor(options = {}) {
      this.id = options.id || `hi-modal-${++modalCounter}`;
      this.options = {
        title: '',
        content: '',
        size: 'md', // sm, md, lg, xl, full
        closable: true,
        closeOnBackdrop: true,
        closeOnEscape: true,
        buttons: [],
        onOpen: null,
        onClose: null,
        ...options
      };

      this.isOpen = false;
      this.previousActiveElement = null;
      this.backdrop = null;
      this.modal = null;

      this._handleKeyDown = this._handleKeyDown.bind(this);
      this._handleBackdropClick = this._handleBackdropClick.bind(this);
    }

    /**
     * Cria o elemento modal
     */
    _createElement() {
      // Cria o backdrop
      this.backdrop = document.createElement('div');
      this.backdrop.className = 'hi-modal-backdrop';
      this.backdrop.id = this.id;
      this.backdrop.setAttribute('role', 'dialog');
      this.backdrop.setAttribute('aria-modal', 'true');
      this.backdrop.setAttribute('aria-labelledby', `${this.id}-title`);

      // Cria o modal
      this.modal = document.createElement('div');
      this.modal.className = `hi-modal hi-modal--${this.options.size}`;

      let html = '';

      // Header
      if (this.options.title || this.options.closable) {
        html += `
          <div class="hi-modal__header">
            <h2 class="hi-modal__title" id="${this.id}-title">${this._escapeHtml(this.options.title)}</h2>
            ${this.options.closable ? `
              <button type="button" class="hi-modal__close" aria-label="Fechar">
                <i class="fas fa-times" aria-hidden="true"></i>
              </button>
            ` : ''}
          </div>
        `;
      }

      // Body
      html += `
        <div class="hi-modal__body">
          ${this.options.content}
        </div>
      `;

      // Footer com botões
      if (this.options.buttons && this.options.buttons.length > 0) {
        html += `
          <div class="hi-modal__footer">
            ${this.options.buttons.map((btn, index) => {
              const variant = btn.variant || 'secondary';
              const type = btn.type || 'button';
              return `
                <button
                  type="${type}"
                  class="hi-btn hi-btn--${variant}"
                  data-action-index="${index}"
                  ${btn.disabled ? 'disabled' : ''}
                >
                  ${btn.icon ? `<i class="${btn.icon}" aria-hidden="true"></i>` : ''}
                  ${this._escapeHtml(btn.text)}
                </button>
              `;
            }).join('')}
          </div>
        `;
      }

      this.modal.innerHTML = html;
      this.backdrop.appendChild(this.modal);
      document.body.appendChild(this.backdrop);

      // Event listeners
      this._attachEventListeners();
    }

    /**
     * Anexa event listeners
     */
    _attachEventListeners() {
      // Fechar pelo botão X
      const closeBtn = this.modal.querySelector('.hi-modal__close');
      if (closeBtn) {
        closeBtn.addEventListener('click', () => this.close());
      }

      // Clique no backdrop
      if (this.options.closeOnBackdrop) {
        this.backdrop.addEventListener('click', this._handleBackdropClick);
      }

      // Botões de ação
      const actionButtons = this.modal.querySelectorAll('[data-action-index]');
      actionButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
          const index = parseInt(e.currentTarget.dataset.actionIndex);
          const buttonConfig = this.options.buttons[index];

          if (buttonConfig.action === 'close') {
            this.close();
          } else if (typeof buttonConfig.action === 'function') {
            buttonConfig.action(this, e);
          }
        });
      });
    }

    /**
     * Clique no backdrop
     */
    _handleBackdropClick(e) {
      if (e.target === this.backdrop) {
        this.close();
      }
    }

    /**
     * Handler de teclado
     */
    _handleKeyDown(e) {
      if (e.key === 'Escape' && this.options.closeOnEscape) {
        e.preventDefault();
        this.close();
        return;
      }

      // Focus trap
      if (e.key === 'Tab') {
        this._trapFocus(e);
      }
    }

    /**
     * Mantém o foco dentro do modal
     */
    _trapFocus(e) {
      const focusableElements = this.modal.querySelectorAll(FOCUSABLE_SELECTORS);
      const firstFocusable = focusableElements[0];
      const lastFocusable = focusableElements[focusableElements.length - 1];

      if (e.shiftKey) {
        // Shift + Tab: se está no primeiro, vai para o último
        if (document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable.focus();
        }
      } else {
        // Tab: se está no último, vai para o primeiro
        if (document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable.focus();
        }
      }
    }

    /**
     * Escapa HTML
     */
    _escapeHtml(text) {
      if (!text) return '';
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    /**
     * Abre o modal
     */
    open() {
      if (this.isOpen) return this;

      // Cria elemento se não existir
      if (!this.backdrop) {
        this._createElement();
      }

      // Salva o elemento ativo atual
      this.previousActiveElement = document.activeElement;

      // Previne scroll do body
      document.body.style.overflow = 'hidden';
      document.body.style.paddingRight = this._getScrollbarWidth() + 'px';

      // Mostra o modal
      requestAnimationFrame(() => {
        this.backdrop.classList.add('hi-modal-backdrop--visible');
      });

      // Adiciona listeners
      document.addEventListener('keydown', this._handleKeyDown);

      // Foca no primeiro elemento focável
      requestAnimationFrame(() => {
        const firstFocusable = this.modal.querySelector(FOCUSABLE_SELECTORS);
        if (firstFocusable) {
          firstFocusable.focus();
        } else {
          this.modal.focus();
        }
      });

      this.isOpen = true;
      activeModals.set(this.id, this);

      // Callback
      if (typeof this.options.onOpen === 'function') {
        this.options.onOpen(this);
      }

      return this;
    }

    /**
     * Fecha o modal
     */
    close() {
      if (!this.isOpen) return this;

      // Remove classe de visibilidade
      this.backdrop.classList.remove('hi-modal-backdrop--visible');

      // Remove listeners
      document.removeEventListener('keydown', this._handleKeyDown);

      // Aguarda animação
      setTimeout(() => {
        // Restaura scroll do body se não há outros modais
        if (activeModals.size === 1) {
          document.body.style.overflow = '';
          document.body.style.paddingRight = '';
        }

        // Remove do DOM
        if (this.backdrop && this.backdrop.parentNode) {
          this.backdrop.parentNode.removeChild(this.backdrop);
        }

        // Restaura foco
        if (this.previousActiveElement && this.previousActiveElement.focus) {
          this.previousActiveElement.focus();
        }

        this.isOpen = false;
        this.backdrop = null;
        this.modal = null;
        activeModals.delete(this.id);

        // Callback
        if (typeof this.options.onClose === 'function') {
          this.options.onClose(this);
        }
      }, 200);

      return this;
    }

    /**
     * Atualiza o conteúdo do modal
     */
    setContent(content) {
      if (this.modal) {
        const body = this.modal.querySelector('.hi-modal__body');
        if (body) {
          body.innerHTML = content;
        }
      }
      this.options.content = content;
      return this;
    }

    /**
     * Atualiza o título do modal
     */
    setTitle(title) {
      if (this.modal) {
        const titleEl = this.modal.querySelector('.hi-modal__title');
        if (titleEl) {
          titleEl.textContent = title;
        }
      }
      this.options.title = title;
      return this;
    }

    /**
     * Mostra loading no modal
     */
    showLoading(message = 'Carregando...') {
      this.setContent(`
        <div class="hi-flex hi-flex-col hi-items-center hi-gap-4 hi-py-6">
          <div class="hi-spinner hi-spinner--lg"></div>
          <p class="hi-text-secondary">${this._escapeHtml(message)}</p>
        </div>
      `);
      return this;
    }

    /**
     * Calcula a largura da scrollbar
     */
    _getScrollbarWidth() {
      const scrollDiv = document.createElement('div');
      scrollDiv.style.cssText = 'width:100px;height:100px;overflow:scroll;position:absolute;top:-9999px;';
      document.body.appendChild(scrollDiv);
      const width = scrollDiv.offsetWidth - scrollDiv.clientWidth;
      document.body.removeChild(scrollDiv);
      return width;
    }

    /**
     * Destrói o modal
     */
    destroy() {
      this.close();
    }
  }

  /**
   * API pública
   */
  const HiModal = {
    /**
     * Cria um novo modal
     * @param {object} options - Opções do modal
     * @returns {Modal}
     */
    create(options) {
      return new Modal(options);
    },

    /**
     * Abre um modal existente pelo ID
     * @param {string} id - ID do modal
     */
    open(id) {
      const modal = activeModals.get(id);
      if (modal) {
        modal.open();
        return modal;
      }

      // Procura no DOM por modal existente
      const existingBackdrop = document.getElementById(id);
      if (existingBackdrop && existingBackdrop.classList.contains('hi-modal-backdrop')) {
        existingBackdrop.classList.add('hi-modal-backdrop--visible');
        document.body.style.overflow = 'hidden';
        return null;
      }

      console.warn(`Modal '${id}' não encontrado`);
      return null;
    },

    /**
     * Fecha um modal pelo ID
     * @param {string} id - ID do modal
     */
    close(id) {
      const modal = activeModals.get(id);
      if (modal) {
        modal.close();
        return;
      }

      // Procura no DOM
      const existingBackdrop = document.getElementById(id);
      if (existingBackdrop) {
        existingBackdrop.classList.remove('hi-modal-backdrop--visible');
        if (activeModals.size === 0) {
          document.body.style.overflow = '';
        }
      }
    },

    /**
     * Fecha todos os modais ativos
     */
    closeAll() {
      activeModals.forEach(modal => modal.close());
    },

    /**
     * Modal de confirmação
     * @param {string} title - Título
     * @param {string} message - Mensagem
     * @param {object} options - Opções adicionais
     * @returns {Promise<boolean>}
     */
    confirm(title, message, options = {}) {
      return new Promise((resolve) => {
        const modal = new Modal({
          title: title,
          content: `<p class="hi-text-secondary">${message}</p>`,
          size: 'sm',
          closable: true,
          closeOnBackdrop: false,
          buttons: [
            {
              text: options.cancelText || 'Cancelar',
              variant: 'secondary',
              action: (m) => {
                m.close();
                resolve(false);
              }
            },
            {
              text: options.confirmText || 'Confirmar',
              variant: options.danger ? 'danger' : 'primary',
              action: (m) => {
                m.close();
                resolve(true);
              }
            }
          ],
          onClose: () => resolve(false),
          ...options
        });
        modal.open();
      });
    },

    /**
     * Modal de alerta
     * @param {string} title - Título
     * @param {string} message - Mensagem
     * @param {object} options - Opções adicionais
     * @returns {Promise<void>}
     */
    alert(title, message, options = {}) {
      return new Promise((resolve) => {
        const modal = new Modal({
          title: title,
          content: `<p class="hi-text-secondary">${message}</p>`,
          size: 'sm',
          closable: true,
          buttons: [
            {
              text: options.buttonText || 'OK',
              variant: 'primary',
              action: (m) => {
                m.close();
                resolve();
              }
            }
          ],
          onClose: () => resolve(),
          ...options
        });
        modal.open();
      });
    },

    /**
     * Modal de prompt (input)
     * @param {string} title - Título
     * @param {string} message - Mensagem
     * @param {object} options - Opções adicionais
     * @returns {Promise<string|null>}
     */
    prompt(title, message, options = {}) {
      return new Promise((resolve) => {
        const inputId = `hi-prompt-input-${Date.now()}`;
        const modal = new Modal({
          title: title,
          content: `
            <div class="hi-form-group">
              <label for="${inputId}" class="hi-label">${message}</label>
              <input
                type="${options.type || 'text'}"
                id="${inputId}"
                class="hi-input"
                placeholder="${options.placeholder || ''}"
                value="${options.defaultValue || ''}"
              />
            </div>
          `,
          size: 'sm',
          closable: true,
          closeOnBackdrop: false,
          buttons: [
            {
              text: options.cancelText || 'Cancelar',
              variant: 'secondary',
              action: (m) => {
                m.close();
                resolve(null);
              }
            },
            {
              text: options.confirmText || 'OK',
              variant: 'primary',
              action: (m) => {
                const input = m.modal.querySelector(`#${inputId}`);
                const value = input ? input.value : '';
                m.close();
                resolve(value);
              }
            }
          ],
          onOpen: (m) => {
            // Foca no input
            setTimeout(() => {
              const input = m.modal.querySelector(`#${inputId}`);
              if (input) input.focus();
            }, 100);
          },
          onClose: () => resolve(null),
          ...options
        });
        modal.open();
      });
    },

    /**
     * Obtém um modal ativo pelo ID
     * @param {string} id - ID do modal
     * @returns {Modal|undefined}
     */
    get(id) {
      return activeModals.get(id);
    },

    /**
     * Verifica se há algum modal aberto
     * @returns {boolean}
     */
    hasOpenModals() {
      return activeModals.size > 0;
    }
  };

  // Expõe globalmente
  global.HiModal = HiModal;

  // Também expõe como módulo ES6 se suportado
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = HiModal;
  }

})(typeof window !== 'undefined' ? window : this);
