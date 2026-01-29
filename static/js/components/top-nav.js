/**
 * HORARIO INTELIGENTE - Top Navigation
 * Barra de navegacao superior para desktop (>= 1024px)
 *
 * Uso:
 *   HiTopNav.init({
 *     activeId: 'dashboard',
 *     items: [
 *       { id: 'dashboard', label: 'Painel', icon: 'fa-chart-line', href: '/static/dashboard.html' },
 *       ...
 *     ]
 *   });
 */

(function(global) {
  'use strict';

  let navElement = null;
  let currentOptions = {};

  /**
   * Obtem dados do usuario do localStorage
   */
  function getUserData() {
    try {
      return JSON.parse(localStorage.getItem('userData') || '{}');
    } catch (e) {
      return {};
    }
  }

  /**
   * Cria o HTML da navegacao desktop
   */
  function createNavHtml(items, activeId) {
    const userData = getUserData();
    const nome = userData.nome || 'Usuario';
    const isMedico = !userData.is_secretaria;
    const displayName = isMedico ? ('Dr(a). ' + nome) : nome;

    return `
      <nav class="hi-top-nav" role="navigation" aria-label="Navegacao principal desktop">
        <div class="hi-top-nav__inner">
          <div class="hi-top-nav__left">
            <a href="/static/dashboard.html" class="hi-top-nav__logo" aria-label="Horario Inteligente - Inicio">
              <img src="/static/images/logo.png" alt="HI" class="hi-top-nav__logo-img" onerror="this.style.display='none'">
              <span class="hi-top-nav__logo-text">HI</span>
            </a>
            <div class="hi-top-nav__links">
              ${items.map(item => {
                const isActive = item.id === activeId;
                return `
                  <${item.href ? 'a' : 'button'}
                    ${item.href ? `href="${item.href}"` : 'type="button"'}
                    class="hi-top-nav__link ${isActive ? 'hi-top-nav__link--active' : ''}"
                    data-nav-id="${item.id}"
                    ${isActive ? 'aria-current="page"' : ''}
                  >
                    <i class="fas ${item.icon}" aria-hidden="true"></i>
                    <span>${item.label}</span>
                    <span class="hi-top-nav__badge" data-badge-id="${item.id}" style="display:none;"></span>
                  </${item.href ? 'a' : 'button'}>
                `;
              }).join('')}
            </div>
          </div>
          <div class="hi-top-nav__right">
            <span class="hi-top-nav__user">
              <i class="fas fa-user-circle" aria-hidden="true"></i>
              ${displayName}
            </span>
            <button type="button" class="hi-top-nav__logout" data-action="logout" aria-label="Sair do sistema">
              <i class="fas fa-sign-out-alt" aria-hidden="true"></i>
              Sair
            </button>
          </div>
        </div>
      </nav>
    `;
  }

  /**
   * Configura event listeners
   */
  function setupListeners() {
    if (!navElement) return;

    // Click handlers para items com onClick
    navElement.addEventListener('click', function(e) {
      var link = e.target.closest('.hi-top-nav__link');
      if (link) {
        var navId = link.dataset.navId;
        var itemConfig = currentOptions.items.find(function(i) { return i.id === navId; });
        if (itemConfig && typeof itemConfig.onClick === 'function') {
          e.preventDefault();
          itemConfig.onClick(itemConfig);
        }
        return;
      }

      // Logout
      var logoutBtn = e.target.closest('[data-action="logout"]');
      if (logoutBtn) {
        e.preventDefault();
        if (confirm('Deseja realmente sair do sistema?')) {
          localStorage.removeItem('authToken');
          localStorage.removeItem('userData');
          window.location.href = '/static/login.html';
        }
      }
    });
  }

  /**
   * API publica
   */
  var HiTopNav = {
    /**
     * Inicializa a navegacao
     */
    init: function(options) {
      // Remove navegacao existente se houver
      this.destroy();

      options = options || {};
      var items = options.items || [];
      var activeId = options.activeId || '';

      currentOptions = { items: items, activeId: activeId };

      // Cria o elemento
      var wrapper = document.createElement('div');
      wrapper.innerHTML = createNavHtml(items, activeId);
      navElement = wrapper.firstElementChild;

      // Insere no inicio do body (antes de qualquer conteudo)
      document.body.insertBefore(navElement, document.body.firstChild);

      // Adiciona classe ao body para padding-top
      document.body.classList.add('hi-has-top-nav');

      // Configura listeners
      setupListeners();

      return this;
    },

    /**
     * Atualiza badge de um item
     */
    setBadge: function(itemId, count) {
      if (!navElement) return;

      var badge = navElement.querySelector('[data-badge-id="' + itemId + '"]');
      if (!badge) return;

      if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.style.display = '';
      } else {
        badge.style.display = 'none';
      }
    },

    /**
     * Destroi a navegacao
     */
    destroy: function() {
      if (navElement && navElement.parentNode) {
        navElement.parentNode.removeChild(navElement);
      }
      navElement = null;
      document.body.classList.remove('hi-has-top-nav');
    }
  };

  // Estilos do componente
  var styles = document.createElement('style');
  styles.textContent = `
    /* Top Navigation - Desktop only */
    .hi-top-nav {
      position: sticky;
      top: 0;
      left: 0;
      right: 0;
      height: 56px;
      background-color: var(--hi-bg-primary, #ffffff);
      border-bottom: 1px solid var(--hi-border-light, #e5e7eb);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
      z-index: var(--hi-z-sticky, 200);
      display: none;
    }

    /* So mostra em desktop */
    @media (min-width: 1024px) {
      .hi-top-nav {
        display: block;
      }
      .hi-has-top-nav {
        /* padding-top handled by sticky */
      }
    }

    .hi-top-nav__inner {
      max-width: 1280px;
      margin: 0 auto;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 1rem;
      gap: 1rem;
    }

    .hi-top-nav__left {
      display: flex;
      align-items: center;
      gap: 1.5rem;
      min-width: 0;
    }

    .hi-top-nav__logo {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      text-decoration: none;
      flex-shrink: 0;
    }

    .hi-top-nav__logo-img {
      width: 32px;
      height: 32px;
      object-fit: contain;
    }

    .hi-top-nav__logo-text {
      font-size: 1.125rem;
      font-weight: 700;
      color: var(--hi-primary, #3b82f6);
    }

    .hi-top-nav__links {
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    .hi-top-nav__link {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.5rem 0.75rem;
      border-radius: 0.5rem;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--hi-text-secondary, #6b7280);
      text-decoration: none;
      border: none;
      background: none;
      cursor: pointer;
      transition: all 150ms ease;
      position: relative;
      white-space: nowrap;
    }

    .hi-top-nav__link:hover {
      color: var(--hi-primary, #3b82f6);
      background-color: var(--hi-primary-50, #eff6ff);
    }

    .hi-top-nav__link--active {
      color: var(--hi-primary, #3b82f6);
      background-color: var(--hi-primary-50, #eff6ff);
      font-weight: 600;
    }

    .hi-top-nav__link--active::after {
      content: '';
      position: absolute;
      bottom: -1px;
      left: 0.5rem;
      right: 0.5rem;
      height: 2px;
      background-color: var(--hi-primary, #3b82f6);
      border-radius: 1px 1px 0 0;
    }

    .hi-top-nav__link:focus-visible {
      outline: 2px solid var(--hi-primary, #3b82f6);
      outline-offset: 2px;
    }

    .hi-top-nav__badge {
      min-width: 18px;
      height: 18px;
      padding: 0 5px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background-color: var(--hi-error, #ef4444);
      color: white;
      font-size: 0.625rem;
      font-weight: 700;
      border-radius: 9px;
      line-height: 1;
    }

    .hi-top-nav__right {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-shrink: 0;
    }

    .hi-top-nav__user {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--hi-text-primary, #374151);
      white-space: nowrap;
    }

    .hi-top-nav__logout {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.375rem 0.75rem;
      border-radius: 0.5rem;
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--hi-error, #ef4444);
      background: none;
      border: 1px solid var(--hi-error, #ef4444);
      cursor: pointer;
      transition: all 150ms ease;
      white-space: nowrap;
    }

    .hi-top-nav__logout:hover {
      background-color: #fef2f2;
    }

    .hi-top-nav__logout:focus-visible {
      outline: 2px solid var(--hi-error, #ef4444);
      outline-offset: 2px;
    }

    /* Dark mode */
    @media (prefers-color-scheme: dark) {
      .hi-top-nav {
        background-color: var(--hi-gray-900, #111827);
        border-bottom-color: var(--hi-gray-800, #1f2937);
      }

      .hi-top-nav__link:hover {
        background-color: var(--hi-gray-800, #1f2937);
      }

      .hi-top-nav__link--active {
        background-color: var(--hi-gray-800, #1f2937);
      }

      .hi-top-nav__user {
        color: var(--hi-gray-200, #e5e7eb);
      }
    }
  `;
  document.head.appendChild(styles);

  // Expoe globalmente
  global.HiTopNav = HiTopNav;

})(typeof window !== 'undefined' ? window : this);
