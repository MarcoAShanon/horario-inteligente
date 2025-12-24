/**
 * HORÁRIO INTELIGENTE - Detalhes do Paciente
 * Modal para visualização rápida das informações do paciente agendado
 *
 * Uso:
 *   HiPatientDetails.show({
 *     paciente: { nome: 'Maria Silva', telefone: '11999999999', email: 'maria@email.com' },
 *     agendamento: { data: '2024-12-24', hora: '09:00', tipo: 'Consulta', convenio: 'Unimed' },
 *     onConfirm: () => { ... },
 *     onReschedule: () => { ... },
 *     onCancel: () => { ... }
 *   });
 */

(function(global) {
  'use strict';

  let currentModal = null;

  /**
   * Formata telefone para exibição
   */
  function formatPhone(phone) {
    if (!phone) return '';
    const digits = phone.replace(/\D/g, '');
    if (digits.length === 11) {
      return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
    } else if (digits.length === 10) {
      return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
    }
    return phone;
  }

  /**
   * Formata data para exibição
   */
  function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr + 'T00:00:00');
    const options = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
    return date.toLocaleDateString('pt-BR', options);
  }

  /**
   * Gera link do WhatsApp
   */
  function getWhatsAppLink(phone, message = '') {
    const digits = phone.replace(/\D/g, '');
    const formattedPhone = digits.startsWith('55') ? digits : `55${digits}`;
    const encodedMessage = encodeURIComponent(message);
    return `https://wa.me/${formattedPhone}${message ? `?text=${encodedMessage}` : ''}`;
  }

  /**
   * Gera link de ligação
   */
  function getPhoneLink(phone) {
    const digits = phone.replace(/\D/g, '');
    return `tel:+55${digits}`;
  }

  /**
   * Obtém badge de status
   */
  function getStatusBadge(status) {
    const statusConfig = {
      'confirmado': { class: 'hi-badge--success', icon: 'fa-check-circle', text: 'Confirmado' },
      'pendente': { class: 'hi-badge--warning', icon: 'fa-clock', text: 'Pendente' },
      'cancelado': { class: 'hi-badge--error', icon: 'fa-times-circle', text: 'Cancelado' },
      'realizado': { class: 'hi-badge--primary', icon: 'fa-check-double', text: 'Realizado' },
      'faltou': { class: 'hi-badge--error', icon: 'fa-user-times', text: 'Faltou' }
    };

    const config = statusConfig[status?.toLowerCase()] || statusConfig['pendente'];
    return `<span class="hi-badge ${config.class} hi-badge--dot">
      <i class="fas ${config.icon}" aria-hidden="true"></i>
      ${config.text}
    </span>`;
  }

  /**
   * Cria o conteúdo do modal
   */
  function createModalContent(data) {
    const { paciente, agendamento, historico } = data;

    const phoneFormatted = formatPhone(paciente.telefone);
    const dateFormatted = formatDate(agendamento.data);
    const whatsappLink = getWhatsAppLink(paciente.telefone);
    const phoneLink = getPhoneLink(paciente.telefone);

    return `
      <div class="hi-patient-details">
        <!-- Header com informações do paciente -->
        <div class="hi-patient-header">
          <div class="hi-patient-avatar">
            ${paciente.foto
              ? `<img src="${paciente.foto}" alt="${paciente.nome}" />`
              : `<i class="fas fa-user" aria-hidden="true"></i>`
            }
          </div>
          <div class="hi-patient-info">
            <h3 class="hi-patient-name">${escapeHtml(paciente.nome)}</h3>
            ${paciente.idade ? `<span class="hi-patient-age">${paciente.idade} anos</span>` : ''}
          </div>
          ${getStatusBadge(agendamento.status)}
        </div>

        <!-- Contatos -->
        <div class="hi-patient-contacts">
          ${paciente.telefone ? `
            <a href="${phoneLink}" class="hi-contact-btn hi-contact-btn--phone" aria-label="Ligar para ${paciente.nome}">
              <i class="fas fa-phone" aria-hidden="true"></i>
              <span>${phoneFormatted}</span>
            </a>
            <a href="${whatsappLink}" target="_blank" class="hi-contact-btn hi-contact-btn--whatsapp" aria-label="WhatsApp de ${paciente.nome}">
              <i class="fab fa-whatsapp" aria-hidden="true"></i>
              <span>WhatsApp</span>
            </a>
          ` : ''}
          ${paciente.email ? `
            <a href="mailto:${paciente.email}" class="hi-contact-btn hi-contact-btn--email" aria-label="Email para ${paciente.nome}">
              <i class="fas fa-envelope" aria-hidden="true"></i>
              <span>${escapeHtml(paciente.email)}</span>
            </a>
          ` : ''}
        </div>

        <!-- Detalhes do Agendamento -->
        <div class="hi-appointment-details">
          <h4 class="hi-section-title">
            <i class="fas fa-calendar-check" aria-hidden="true"></i>
            Consulta Agendada
          </h4>

          <div class="hi-detail-grid">
            <div class="hi-detail-item">
              <i class="fas fa-calendar" aria-hidden="true"></i>
              <div>
                <span class="hi-detail-label">Data</span>
                <span class="hi-detail-value">${dateFormatted}</span>
              </div>
            </div>

            <div class="hi-detail-item">
              <i class="fas fa-clock" aria-hidden="true"></i>
              <div>
                <span class="hi-detail-label">Horário</span>
                <span class="hi-detail-value">${agendamento.hora}${agendamento.duracao ? ` (${agendamento.duracao} min)` : ''}</span>
              </div>
            </div>

            ${agendamento.tipo ? `
              <div class="hi-detail-item">
                <i class="fas fa-stethoscope" aria-hidden="true"></i>
                <div>
                  <span class="hi-detail-label">Tipo</span>
                  <span class="hi-detail-value">${escapeHtml(agendamento.tipo)}</span>
                </div>
              </div>
            ` : ''}

            ${agendamento.convenio ? `
              <div class="hi-detail-item">
                <i class="fas fa-id-card" aria-hidden="true"></i>
                <div>
                  <span class="hi-detail-label">Convênio</span>
                  <span class="hi-detail-value">${escapeHtml(agendamento.convenio)}</span>
                </div>
              </div>
            ` : ''}
          </div>
        </div>

        <!-- Observações -->
        ${agendamento.observacoes ? `
          <div class="hi-appointment-notes">
            <h4 class="hi-section-title">
              <i class="fas fa-sticky-note" aria-hidden="true"></i>
              Observações
            </h4>
            <p class="hi-notes-content">${escapeHtml(agendamento.observacoes)}</p>
          </div>
        ` : ''}

        <!-- Histórico resumido -->
        ${historico && historico.length > 0 ? `
          <div class="hi-patient-history">
            <h4 class="hi-section-title">
              <i class="fas fa-history" aria-hidden="true"></i>
              Últimas Consultas
            </h4>
            <ul class="hi-history-list">
              ${historico.slice(0, 3).map(h => `
                <li class="hi-history-item">
                  <span class="hi-history-date">${formatDate(h.data)}</span>
                  <span class="hi-history-type">${escapeHtml(h.tipo)}</span>
                </li>
              `).join('')}
            </ul>
          </div>
        ` : ''}
      </div>
    `;
  }

  /**
   * Escapa HTML
   */
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * API pública
   */
  const HiPatientDetails = {
    /**
     * Mostra o modal de detalhes do paciente
     * @param {object} data - Dados do paciente e agendamento
     */
    show(data) {
      // Fecha modal anterior se existir
      if (currentModal) {
        currentModal.close();
      }

      const { paciente, agendamento, onConfirm, onReschedule, onCancel, onClose } = data;

      // Define os botões baseado no status
      const buttons = [];

      if (agendamento.status !== 'cancelado' && agendamento.status !== 'realizado') {
        // Botão de confirmar presença
        if (agendamento.status !== 'confirmado') {
          buttons.push({
            text: 'Confirmar Presença',
            variant: 'success',
            icon: 'fas fa-check',
            action: (modal) => {
              if (typeof onConfirm === 'function') {
                onConfirm(data);
              }
              modal.close();
            }
          });
        }

        // Botão de remarcar
        buttons.push({
          text: 'Remarcar',
          variant: 'secondary',
          icon: 'fas fa-calendar-alt',
          action: (modal) => {
            if (typeof onReschedule === 'function') {
              onReschedule(data);
            }
            modal.close();
          }
        });

        // Botão de cancelar
        buttons.push({
          text: 'Cancelar',
          variant: 'ghost',
          icon: 'fas fa-times',
          action: async (modal) => {
            // Confirmação antes de cancelar
            if (typeof HiModal !== 'undefined') {
              const confirmed = await HiModal.confirm(
                'Cancelar Agendamento',
                `Deseja realmente cancelar a consulta de ${paciente.nome}?`,
                { danger: true, confirmText: 'Sim, cancelar', cancelText: 'Não' }
              );
              if (confirmed && typeof onCancel === 'function') {
                onCancel(data);
              }
            } else if (typeof onCancel === 'function') {
              onCancel(data);
            }
            modal.close();
          }
        });
      }

      // Cria o modal
      currentModal = HiModal.create({
        title: 'Detalhes do Paciente',
        content: createModalContent(data),
        size: 'md',
        buttons: buttons,
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
     * Fecha o modal atual
     */
    close() {
      if (currentModal) {
        currentModal.close();
        currentModal = null;
      }
    },

    /**
     * Verifica se o modal está aberto
     */
    isOpen() {
      return currentModal !== null && currentModal.isOpen;
    }
  };

  // Estilos do componente
  const styles = document.createElement('style');
  styles.textContent = `
    .hi-patient-details {
      display: flex;
      flex-direction: column;
      gap: var(--hi-space-4, 16px);
    }

    .hi-patient-header {
      display: flex;
      align-items: center;
      gap: var(--hi-space-4, 16px);
      padding-bottom: var(--hi-space-4, 16px);
      border-bottom: 1px solid var(--hi-border-light, #e5e7eb);
    }

    .hi-patient-avatar {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--hi-primary, #3b82f6), var(--hi-primary-dark, #2563eb));
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 1.5rem;
      flex-shrink: 0;
      overflow: hidden;
    }

    .hi-patient-avatar img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .hi-patient-info {
      flex: 1;
      min-width: 0;
    }

    .hi-patient-name {
      font-size: var(--hi-font-size-xl, 1.25rem);
      font-weight: var(--hi-font-weight-semibold, 600);
      color: var(--hi-text-primary, #1f2937);
      margin: 0 0 var(--hi-space-1, 4px) 0;
    }

    .hi-patient-age {
      font-size: var(--hi-font-size-sm, 0.875rem);
      color: var(--hi-text-secondary, #6b7280);
    }

    .hi-patient-contacts {
      display: flex;
      flex-wrap: wrap;
      gap: var(--hi-space-2, 8px);
    }

    .hi-contact-btn {
      display: inline-flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      padding: var(--hi-space-2, 8px) var(--hi-space-3, 12px);
      border-radius: var(--hi-radius-lg, 12px);
      font-size: var(--hi-font-size-sm, 0.875rem);
      font-weight: var(--hi-font-weight-medium, 500);
      text-decoration: none;
      transition: all var(--hi-transition-fast, 150ms);
      min-height: 40px;
    }

    .hi-contact-btn--phone {
      background-color: var(--hi-primary-50, #eff6ff);
      color: var(--hi-primary, #3b82f6);
    }

    .hi-contact-btn--phone:hover {
      background-color: var(--hi-primary-100, #dbeafe);
    }

    .hi-contact-btn--whatsapp {
      background-color: #dcf8c6;
      color: #128C7E;
    }

    .hi-contact-btn--whatsapp:hover {
      background-color: #c5f0a5;
    }

    .hi-contact-btn--email {
      background-color: var(--hi-gray-100, #f3f4f6);
      color: var(--hi-text-secondary, #6b7280);
    }

    .hi-contact-btn--email:hover {
      background-color: var(--hi-gray-200, #e5e7eb);
      color: var(--hi-text-primary, #1f2937);
    }

    .hi-section-title {
      display: flex;
      align-items: center;
      gap: var(--hi-space-2, 8px);
      font-size: var(--hi-font-size-sm, 0.875rem);
      font-weight: var(--hi-font-weight-semibold, 600);
      color: var(--hi-text-secondary, #6b7280);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin: 0 0 var(--hi-space-3, 12px) 0;
    }

    .hi-section-title i {
      color: var(--hi-primary, #3b82f6);
    }

    .hi-detail-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: var(--hi-space-3, 12px);
    }

    @media (max-width: 480px) {
      .hi-detail-grid {
        grid-template-columns: 1fr;
      }
    }

    .hi-detail-item {
      display: flex;
      align-items: flex-start;
      gap: var(--hi-space-3, 12px);
      padding: var(--hi-space-3, 12px);
      background-color: var(--hi-gray-50, #f9fafb);
      border-radius: var(--hi-radius-md, 8px);
    }

    .hi-detail-item > i {
      color: var(--hi-primary, #3b82f6);
      font-size: 1rem;
      margin-top: 2px;
    }

    .hi-detail-item > div {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .hi-detail-label {
      font-size: var(--hi-font-size-xs, 0.75rem);
      color: var(--hi-text-muted, #9ca3af);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .hi-detail-value {
      font-size: var(--hi-font-size-sm, 0.875rem);
      font-weight: var(--hi-font-weight-medium, 500);
      color: var(--hi-text-primary, #1f2937);
    }

    .hi-appointment-notes {
      background-color: var(--hi-warning-bg, #fffbeb);
      border-radius: var(--hi-radius-lg, 12px);
      padding: var(--hi-space-4, 16px);
      border-left: 4px solid var(--hi-warning, #f59e0b);
    }

    .hi-notes-content {
      margin: 0;
      font-size: var(--hi-font-size-sm, 0.875rem);
      color: var(--hi-text-primary, #1f2937);
      line-height: 1.5;
    }

    .hi-history-list {
      list-style: none;
      margin: 0;
      padding: 0;
    }

    .hi-history-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: var(--hi-space-2, 8px) 0;
      border-bottom: 1px solid var(--hi-border-light, #e5e7eb);
      font-size: var(--hi-font-size-sm, 0.875rem);
    }

    .hi-history-item:last-child {
      border-bottom: none;
    }

    .hi-history-date {
      color: var(--hi-text-secondary, #6b7280);
    }

    .hi-history-type {
      color: var(--hi-text-primary, #1f2937);
      font-weight: var(--hi-font-weight-medium, 500);
    }
  `;
  document.head.appendChild(styles);

  // Expõe globalmente
  global.HiPatientDetails = HiPatientDetails;

})(typeof window !== 'undefined' ? window : this);
