/**
 * HORARIO INTELIGENTE - Navigation Initializer
 * Inicializa HiTopNav (desktop) + HiBottomNav (mobile) com itens padronizados por role
 *
 * Uso:
 *   HiNavInit.init({ activeId: 'dashboard' });
 *   HiNavInit.init({ activeId: 'agenda', onNewAppointment: () => {...} });
 */

(function(global) {
  'use strict';

  var moreMenuEl = null;
  var moreBackdropEl = null;

  /**
   * Injeta CSS do menu "Mais"
   */
  function injectStyles() {
    if (document.getElementById('hi-more-menu-styles')) return;
    var style = document.createElement('style');
    style.id = 'hi-more-menu-styles';
    style.textContent = [
      '.hi-more-menu-backdrop {',
      '  position: fixed; inset: 0; z-index: 199;',
      '  background: rgba(0,0,0,0.3);',
      '  opacity: 0; transition: opacity 200ms;',
      '}',
      '.hi-more-menu-backdrop--visible { opacity: 1; }',
      '',
      '.hi-more-menu {',
      '  position: fixed; bottom: 72px; right: 8px;',
      '  z-index: 201; min-width: 180px;',
      '  background: var(--hi-bg-primary, #fff);',
      '  border-radius: 12px;',
      '  box-shadow: 0 8px 32px rgba(0,0,0,0.18);',
      '  padding: 8px 0;',
      '  transform: translateY(12px); opacity: 0;',
      '  transition: transform 200ms, opacity 200ms;',
      '}',
      '.hi-more-menu--visible {',
      '  transform: translateY(0); opacity: 1;',
      '}',
      '',
      '.hi-more-menu__item {',
      '  display: flex; align-items: center; gap: 12px;',
      '  width: 100%; padding: 12px 20px;',
      '  background: none; border: none;',
      '  color: var(--hi-text-primary, #1f2937);',
      '  font-size: 0.938rem; font-family: inherit;',
      '  cursor: pointer; text-decoration: none;',
      '  transition: background 150ms;',
      '}',
      '.hi-more-menu__item:hover {',
      '  background: var(--hi-gray-100, #f3f4f6);',
      '}',
      '.hi-more-menu__item i {',
      '  width: 20px; text-align: center;',
      '  color: var(--hi-text-muted, #6b7280);',
      '  font-size: 1rem;',
      '}',
      '.hi-more-menu__item--danger {',
      '  color: var(--hi-error, #ef4444);',
      '}',
      '.hi-more-menu__item--danger i {',
      '  color: var(--hi-error, #ef4444);',
      '}',
      '.hi-more-menu__sep {',
      '  height: 1px; margin: 4px 12px;',
      '  background: var(--hi-border-light, #e5e7eb);',
      '}',
      '',
      '@media (min-width: 1024px) {',
      '  .hi-more-menu, .hi-more-menu-backdrop { display: none !important; }',
      '}',
      '@media (prefers-color-scheme: dark) {',
      '  .hi-more-menu {',
      '    background: var(--hi-gray-900, #111827);',
      '  }',
      '  .hi-more-menu__item:hover {',
      '    background: var(--hi-gray-800, #1f2937);',
      '  }',
      '}'
    ].join('\n');
    document.head.appendChild(style);
  }

  /**
   * Fecha o menu "Mais"
   */
  function closeMoreMenu() {
    if (moreMenuEl) {
      moreMenuEl.classList.remove('hi-more-menu--visible');
    }
    if (moreBackdropEl) {
      moreBackdropEl.classList.remove('hi-more-menu-backdrop--visible');
      setTimeout(function() {
        if (moreBackdropEl && moreBackdropEl.parentNode) {
          moreBackdropEl.parentNode.removeChild(moreBackdropEl);
        }
        if (moreMenuEl && moreMenuEl.parentNode) {
          moreMenuEl.parentNode.removeChild(moreMenuEl);
        }
        moreBackdropEl = null;
        moreMenuEl = null;
      }, 220);
    }
  }

  /**
   * Faz logout com confirmacao
   */
  function doLogout() {
    if (confirm('Deseja realmente sair?')) {
      localStorage.removeItem('authToken');
      localStorage.removeItem('userData');
      window.location.href = '/static/login.html';
    }
  }

  /**
   * Abre o menu "Mais" com itens overflow
   */
  function openMoreMenu(overflowItems) {
    closeMoreMenu();

    // Backdrop
    moreBackdropEl = document.createElement('div');
    moreBackdropEl.className = 'hi-more-menu-backdrop';
    moreBackdropEl.addEventListener('click', closeMoreMenu);
    document.body.appendChild(moreBackdropEl);

    // Menu
    moreMenuEl = document.createElement('div');
    moreMenuEl.className = 'hi-more-menu';
    moreMenuEl.setAttribute('role', 'menu');

    var html = '';
    for (var i = 0; i < overflowItems.length; i++) {
      var item = overflowItems[i];
      if (item.separator) {
        html += '<div class="hi-more-menu__sep"></div>';
        continue;
      }
      var cls = 'hi-more-menu__item' + (item.danger ? ' hi-more-menu__item--danger' : '');
      if (item.href) {
        html += '<a class="' + cls + '" href="' + item.href + '" role="menuitem">' +
                '<i class="fas ' + item.icon + '"></i>' + item.label + '</a>';
      } else {
        html += '<button class="' + cls + '" type="button" role="menuitem" data-action="' + (item.action || '') + '">' +
                '<i class="fas ' + item.icon + '"></i>' + item.label + '</button>';
      }
    }
    moreMenuEl.innerHTML = html;

    // Event delegation para botoes
    moreMenuEl.addEventListener('click', function(e) {
      var btn = e.target.closest('button[data-action]');
      if (btn && btn.dataset.action === 'logout') {
        closeMoreMenu();
        doLogout();
      }
    });

    document.body.appendChild(moreMenuEl);

    // Anima entrada
    requestAnimationFrame(function() {
      if (moreBackdropEl) moreBackdropEl.classList.add('hi-more-menu-backdrop--visible');
      if (moreMenuEl) moreMenuEl.classList.add('hi-more-menu--visible');
    });
  }

  /**
   * Detecta a pagina ativa baseado no pathname
   */
  function detectActiveId() {
    var path = window.location.pathname;

    if (path.includes('dashboard-v2') || path.includes('dashboard')) return 'dashboard';
    if (path.includes('calendario') || path.includes('agenda')) return 'agenda';
    if (path.includes('conversas')) return 'conversas';
    if (path.includes('configuracoes') || path.includes('configuracao-agenda') || path.includes('minha-agenda')) return 'config';
    if (path.includes('perfil')) return 'perfil';

    return 'dashboard';
  }

  /**
   * Retorna true se usuario e secretaria
   */
  function isSecretaria() {
    try {
      var data = JSON.parse(localStorage.getItem('userData') || '{}');
      return !!data.is_secretaria;
    } catch (e) {
      return false;
    }
  }

  /**
   * Itens de navegacao para medico (top nav desktop)
   */
  function getMedicoItems() {
    return [
      { id: 'dashboard', label: 'Painel',         icon: 'fa-chart-line',   href: '/static/dashboard.html' },
      { id: 'agenda',    label: 'Agenda',          icon: 'fa-calendar-alt', href: '/static/calendario-unificado.html' },
      { id: 'conversas', label: 'Conversas',       icon: 'fa-comments',     href: '/static/conversas.html' },
      { id: 'config',    label: 'Configuracoes',   icon: 'fa-cog',          href: '/static/configuracoes.html' },
      { id: 'perfil',    label: 'Perfil',          icon: 'fa-user',         href: '/static/perfil.html' }
    ];
  }

  /**
   * Itens de navegacao para secretaria (top nav desktop)
   */
  function getSecretariaItems() {
    return [
      { id: 'agenda',    label: 'Agenda',    icon: 'fa-calendar-alt', href: '/static/calendario-unificado.html' },
      { id: 'conversas', label: 'Conversas', icon: 'fa-comments',     href: '/static/conversas.html' }
    ];
  }

  /**
   * Itens do bottom nav para medico (5 itens com FAB central)
   * Agenda, Conversas, Novo(FAB), Config, Mais(...)
   */
  function getMedicoBottomItems(onNewAppointment) {
    var overflowItems = [
      { label: 'Painel',  icon: 'fa-chart-line', href: '/static/dashboard.html' },
      { label: 'Perfil',  icon: 'fa-user',       href: '/static/perfil.html' },
      { separator: true },
      { label: 'Sair',    icon: 'fa-sign-out-alt', action: 'logout', danger: true }
    ];

    return [
      { id: 'agenda',    label: 'Agenda',     icon: 'fa-calendar-alt', href: '/static/calendario-unificado.html' },
      { id: 'conversas', label: 'Conversas',  icon: 'fa-comments',     href: '/static/conversas.html' },
      {
        id: 'novo',
        label: 'Novo',
        icon: 'fa-plus',
        primary: true,
        onClick: onNewAppointment || function() {
          window.location.href = '/static/calendario-unificado.html';
        }
      },
      { id: 'config',    label: 'Config',     icon: 'fa-cog',          href: '/static/configuracoes.html' },
      {
        id: 'mais',
        label: 'Mais',
        icon: 'fa-ellipsis-h',
        onClick: function() {
          openMoreMenu(overflowItems);
        }
      }
    ];
  }

  /**
   * Itens do bottom nav para secretaria (5 itens com FAB central)
   */
  function getSecretariaBottomItems(onNewAppointment) {
    return [
      { id: 'agenda',    label: 'Agenda',    icon: 'fa-calendar-alt', href: '/static/calendario-unificado.html' },
      { id: 'conversas', label: 'Conversas', icon: 'fa-comments',     href: '/static/conversas.html' },
      {
        id: 'novo',
        label: 'Novo',
        icon: 'fa-plus',
        primary: true,
        onClick: onNewAppointment || function() {
          window.location.href = '/static/calendario-unificado.html';
        }
      },
      { id: 'config',    label: 'Config',   icon: 'fa-cog',  href: '/static/configuracoes.html' },
      { id: 'senha',     label: 'Senha',    icon: 'fa-key',  href: '/static/alterar-senha.html' }
    ];
  }

  /**
   * API publica
   */
  var HiNavInit = {
    /**
     * Inicializa ambas as barras de navegacao
     * @param {Object} options
     * @param {string} options.activeId - ID da pagina ativa
     * @param {Function} options.onNewAppointment - Handler para botao "Novo"
     */
    init: function(options) {
      options = options || {};
      var activeId = options.activeId || detectActiveId();
      var onNewAppointment = options.onNewAppointment || null;
      var secretaria = isSecretaria();

      // Injeta CSS do menu "Mais"
      injectStyles();

      // Inicializa Top Nav (desktop)
      if (typeof HiTopNav !== 'undefined') {
        var topItems = secretaria ? getSecretariaItems() : getMedicoItems();
        HiTopNav.init({
          items: topItems,
          activeId: activeId
        });
      }

      // Inicializa Bottom Nav (mobile)
      if (typeof HiBottomNav !== 'undefined') {
        var bottomItems = secretaria
          ? getSecretariaBottomItems(onNewAppointment)
          : getMedicoBottomItems(onNewAppointment);

        HiBottomNav.init({
          items: bottomItems,
          activeId: activeId
        });
      }
    }
  };

  // Expoe globalmente
  global.HiNavInit = HiNavInit;

})(typeof window !== 'undefined' ? window : this);
