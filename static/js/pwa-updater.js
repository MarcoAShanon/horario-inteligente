/**
 * PWA Update Manager
 * Horário Inteligente SaaS
 *
 * Gerencia atualizações do Service Worker e notifica o usuário
 * quando uma nova versão está disponível.
 */

const PWAUpdater = {
    // Estado
    registration: null,
    updateAvailable: false,
    currentVersion: null,
    newVersion: null,

    /**
     * Inicializa o gerenciador de atualizações
     */
    async init() {
        if (!('serviceWorker' in navigator)) {
            console.warn('Service Worker não suportado');
            return false;
        }

        try {
            // Registrar Service Worker
            this.registration = await navigator.serviceWorker.register('/static/service-worker.js');
            console.log('✅ Service Worker registrado:', this.registration.scope);

            // Escutar mensagens do Service Worker
            navigator.serviceWorker.addEventListener('message', (event) => {
                this.handleMessage(event.data);
            });

            // Verificar se há SW esperando para ativar
            if (this.registration.waiting) {
                this.onUpdateFound(this.registration.waiting);
            }

            // Escutar por novas atualizações
            this.registration.addEventListener('updatefound', () => {
                const newWorker = this.registration.installing;
                if (newWorker) {
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            this.onUpdateFound(newWorker);
                        }
                    });
                }
            });

            // Verificar atualizações a cada 5 minutos
            setInterval(() => this.checkForUpdate(), 5 * 60 * 1000);

            // Obter versão atual
            this.getVersion();

            return true;
        } catch (err) {
            console.error('Erro ao registrar Service Worker:', err);
            return false;
        }
    },

    /**
     * Processa mensagens do Service Worker
     */
    handleMessage(data) {
        if (!data || !data.type) return;

        switch (data.type) {
            case 'SW_UPDATED':
                this.newVersion = data.version;
                this.showUpdateNotification();
                break;

            case 'VERSION':
                this.currentVersion = data.version;
                console.log('📱 PWA Versão:', this.currentVersion);
                break;
        }
    },

    /**
     * Chamado quando uma atualização é encontrada
     */
    onUpdateFound(worker) {
        console.log('🔄 Nova versão do PWA disponível!');
        this.updateAvailable = true;
        this.showUpdateNotification();
    },

    /**
     * Exibe notificação de atualização para o usuário
     */
    showUpdateNotification() {
        // Evitar mostrar múltiplas vezes
        if (document.getElementById('pwa-update-toast')) return;

        const toast = document.createElement('div');
        toast.id = 'pwa-update-toast';
        toast.className = 'pwa-update-toast';
        toast.innerHTML = `
            <div class="pwa-update-content">
                <div class="pwa-update-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>
                    </svg>
                </div>
                <div class="pwa-update-text">
                    <strong>Nova versão disponível!</strong>
                    <p>Clique em atualizar para usar a versão mais recente.</p>
                </div>
                <div class="pwa-update-actions">
                    <button class="pwa-update-btn pwa-update-btn-primary" onclick="PWAUpdater.applyUpdate()">
                        Atualizar
                    </button>
                    <button class="pwa-update-btn pwa-update-btn-secondary" onclick="PWAUpdater.dismissNotification()">
                        Depois
                    </button>
                </div>
            </div>
        `;

        // Adicionar estilos se não existirem
        if (!document.getElementById('pwa-update-styles')) {
            const styles = document.createElement('style');
            styles.id = 'pwa-update-styles';
            styles.textContent = `
                .pwa-update-toast {
                    position: fixed;
                    bottom: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    z-index: 99999;
                    background: #1e293b;
                    color: white;
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
                    padding: 16px 20px;
                    max-width: 420px;
                    width: calc(100% - 40px);
                    animation: slideUp 0.3s ease-out;
                }
                @keyframes slideUp {
                    from {
                        opacity: 0;
                        transform: translateX(-50%) translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateX(-50%) translateY(0);
                    }
                }
                .pwa-update-content {
                    display: flex;
                    align-items: flex-start;
                    gap: 12px;
                }
                .pwa-update-icon {
                    flex-shrink: 0;
                    width: 40px;
                    height: 40px;
                    background: #3b82f6;
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .pwa-update-icon svg {
                    width: 24px;
                    height: 24px;
                    color: white;
                }
                .pwa-update-text {
                    flex: 1;
                }
                .pwa-update-text strong {
                    display: block;
                    font-size: 15px;
                    margin-bottom: 4px;
                }
                .pwa-update-text p {
                    font-size: 13px;
                    color: #94a3b8;
                    margin: 0;
                }
                .pwa-update-actions {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                    flex-shrink: 0;
                }
                .pwa-update-btn {
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: 500;
                    cursor: pointer;
                    border: none;
                    transition: all 0.2s;
                }
                .pwa-update-btn-primary {
                    background: #3b82f6;
                    color: white;
                }
                .pwa-update-btn-primary:hover {
                    background: #2563eb;
                }
                .pwa-update-btn-secondary {
                    background: transparent;
                    color: #94a3b8;
                }
                .pwa-update-btn-secondary:hover {
                    color: white;
                }
                @media (max-width: 480px) {
                    .pwa-update-toast {
                        bottom: 70px; /* Acima da bottom nav */
                    }
                    .pwa-update-content {
                        flex-wrap: wrap;
                    }
                    .pwa-update-actions {
                        flex-direction: row;
                        width: 100%;
                        margin-top: 12px;
                    }
                    .pwa-update-btn {
                        flex: 1;
                    }
                }
            `;
            document.head.appendChild(styles);
        }

        document.body.appendChild(toast);
    },

    /**
     * Aplica a atualização (recarrega a página)
     */
    applyUpdate() {
        // Enviar mensagem para o novo SW assumir controle
        if (this.registration && this.registration.waiting) {
            this.registration.waiting.postMessage({ type: 'SKIP_WAITING' });
        }

        // Recarregar a página após um pequeno delay
        setTimeout(() => {
            window.location.reload(true);
        }, 100);
    },

    /**
     * Descarta a notificação de atualização
     */
    dismissNotification() {
        const toast = document.getElementById('pwa-update-toast');
        if (toast) {
            toast.style.animation = 'slideDown 0.3s ease-in forwards';
            setTimeout(() => toast.remove(), 300);
        }

        // Adicionar animação de saída
        if (!document.querySelector('#pwa-update-styles-exit')) {
            const styles = document.createElement('style');
            styles.id = 'pwa-update-styles-exit';
            styles.textContent = `
                @keyframes slideDown {
                    from {
                        opacity: 1;
                        transform: translateX(-50%) translateY(0);
                    }
                    to {
                        opacity: 0;
                        transform: translateX(-50%) translateY(20px);
                    }
                }
            `;
            document.head.appendChild(styles);
        }
    },

    /**
     * Verifica se há atualização disponível
     */
    async checkForUpdate() {
        if (this.registration) {
            try {
                await this.registration.update();
                console.log('🔍 Verificação de atualização concluída');
            } catch (err) {
                console.warn('Erro ao verificar atualização:', err);
            }
        }
    },

    /**
     * Obtém a versão atual do Service Worker
     */
    getVersion() {
        if (navigator.serviceWorker.controller) {
            const messageChannel = new MessageChannel();
            messageChannel.port1.onmessage = (event) => {
                if (event.data && event.data.type === 'VERSION') {
                    this.currentVersion = event.data.version;
                    console.log('📱 PWA Versão:', this.currentVersion);
                }
            };
            navigator.serviceWorker.controller.postMessage(
                { type: 'GET_VERSION' },
                [messageChannel.port2]
            );
        }
    },

    /**
     * Força limpeza de cache e atualização
     */
    async forceUpdate() {
        if (navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_CACHE' });
        }

        // Aguardar um momento e recarregar
        setTimeout(() => {
            window.location.reload(true);
        }, 500);
    }
};

// Exporta para uso global
window.PWAUpdater = PWAUpdater;

// Auto-inicializa quando o DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => PWAUpdater.init());
} else {
    PWAUpdater.init();
}
