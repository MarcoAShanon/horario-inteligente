/**
 * Push Notifications Module
 * Horário Inteligente SaaS
 *
 * Gerencia push notifications via Web Push API (PWA).
 * Gratuito e instantâneo - alternativa ao WhatsApp (R$0,04/msg).
 */

const PushNotifications = {
    // Estado
    isSupported: false,
    isSubscribed: false,
    subscription: null,

    /**
     * Inicializa o módulo de push notifications
     * @returns {Promise<boolean>} true se suportado e pronto
     */
    async init() {
        // Verifica suporte do navegador
        if (!('serviceWorker' in navigator)) {
            console.warn('Service Worker não suportado');
            return false;
        }

        if (!('PushManager' in window)) {
            console.warn('Push API não suportada');
            return false;
        }

        if (!('Notification' in window)) {
            console.warn('Notifications API não suportada');
            return false;
        }

        this.isSupported = true;

        // Verifica status atual da subscription
        try {
            const registration = await navigator.serviceWorker.ready;
            this.subscription = await registration.pushManager.getSubscription();
            this.isSubscribed = !!this.subscription;

            console.log('📱 Push Notifications:', this.isSubscribed ? 'Ativo' : 'Inativo');
            return true;
        } catch (err) {
            console.error('Erro ao verificar subscription:', err);
            return false;
        }
    },

    /**
     * Verifica se o navegador suporta push notifications
     * @returns {boolean}
     */
    checkSupport() {
        return this.isSupported;
    },

    /**
     * Retorna o status atual da permissão
     * @returns {string} 'granted', 'denied' ou 'default'
     */
    getPermissionStatus() {
        if (!('Notification' in window)) {
            return 'unsupported';
        }
        return Notification.permission;
    },

    /**
     * Solicita permissão para notificações
     * @returns {Promise<string>} Status da permissão
     */
    async requestPermission() {
        if (!this.isSupported) {
            throw new Error('Push notifications não suportadas neste navegador');
        }

        const permission = await Notification.requestPermission();
        console.log('Permissão de notificação:', permission);
        return permission;
    },

    /**
     * Busca a chave pública VAPID do servidor
     * @returns {Promise<string>} Chave pública VAPID
     */
    async getVapidPublicKey() {
        const token = localStorage.getItem('token');
        if (!token) {
            throw new Error('Usuário não autenticado');
        }

        const response = await fetch('/api/push/vapid-public-key', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao buscar chave VAPID');
        }

        const data = await response.json();
        return data.publicKey;
    },

    /**
     * Converte chave VAPID de base64url para Uint8Array
     * @param {string} base64String - Chave em base64url
     * @returns {Uint8Array}
     */
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    },

    /**
     * Ativa notificações push para o usuário
     * @returns {Promise<Object>} Resultado da operação
     */
    async subscribe() {
        if (!this.isSupported) {
            return { success: false, error: 'Push notifications não suportadas' };
        }

        try {
            // Solicita permissão se necessário
            const permission = await this.requestPermission();
            if (permission !== 'granted') {
                return {
                    success: false,
                    error: 'Permissão de notificação negada',
                    permission: permission
                };
            }

            // Busca chave VAPID do servidor
            const vapidPublicKey = await this.getVapidPublicKey();
            const applicationServerKey = this.urlBase64ToUint8Array(vapidPublicKey);

            // Cria subscription
            const registration = await navigator.serviceWorker.ready;
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: applicationServerKey
            });

            // Envia subscription para o servidor
            const token = localStorage.getItem('token');
            const subscriptionJson = subscription.toJSON();

            const response = await fetch('/api/push/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    endpoint: subscriptionJson.endpoint,
                    keys: {
                        p256dh: subscriptionJson.keys.p256dh,
                        auth: subscriptionJson.keys.auth
                    }
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.subscription = subscription;
                this.isSubscribed = true;
                console.log('✅ Push notifications ativadas!');
                return { success: true, message: result.message };
            } else {
                // Reverte a subscription local se falhou no servidor
                await subscription.unsubscribe();
                throw new Error(result.detail || result.error || 'Erro ao salvar subscription');
            }

        } catch (err) {
            console.error('Erro ao ativar notificações:', err);
            return { success: false, error: err.message };
        }
    },

    /**
     * Desativa notificações push
     * @returns {Promise<Object>} Resultado da operação
     */
    async unsubscribe() {
        if (!this.subscription) {
            return { success: true, message: 'Já desativado' };
        }

        try {
            const endpoint = this.subscription.endpoint;

            // Remove subscription do navegador
            await this.subscription.unsubscribe();

            // Notifica servidor
            const token = localStorage.getItem('token');
            await fetch('/api/push/unsubscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ endpoint: endpoint })
            });

            this.subscription = null;
            this.isSubscribed = false;
            console.log('🔕 Push notifications desativadas');
            return { success: true, message: 'Notificações desativadas' };

        } catch (err) {
            console.error('Erro ao desativar notificações:', err);
            return { success: false, error: err.message };
        }
    },

    /**
     * Alterna estado das notificações
     * @returns {Promise<Object>} Resultado da operação
     */
    async toggle() {
        if (this.isSubscribed) {
            return await this.unsubscribe();
        } else {
            return await this.subscribe();
        }
    },

    /**
     * Envia notificação de teste
     * @returns {Promise<Object>} Resultado do teste
     */
    async sendTest() {
        const token = localStorage.getItem('token');
        if (!token) {
            return { success: false, error: 'Usuário não autenticado' };
        }

        try {
            const response = await fetch('/api/push/test', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            const result = await response.json();
            return result;

        } catch (err) {
            console.error('Erro ao enviar teste:', err);
            return { success: false, error: err.message };
        }
    },

    /**
     * Busca status das subscriptions do usuário
     * @returns {Promise<Object>} Status das subscriptions
     */
    async getStatus() {
        const token = localStorage.getItem('token');
        if (!token) {
            return { subscriptions: 0, enabled: false };
        }

        try {
            const response = await fetch('/api/push/status', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                return await response.json();
            }
            return { subscriptions: 0, enabled: false };

        } catch (err) {
            console.error('Erro ao buscar status:', err);
            return { subscriptions: 0, enabled: false };
        }
    },

    /**
     * Atualiza UI com base no estado atual
     * @param {Object} elements - Elementos da UI {toggle, statusText, testBtn}
     */
    async updateUI(elements) {
        const { toggle, statusText, testBtn, statusBadge } = elements;

        if (!this.isSupported) {
            if (toggle) toggle.disabled = true;
            if (statusText) statusText.textContent = 'Não suportado neste navegador';
            if (testBtn) testBtn.disabled = true;
            return;
        }

        const permission = this.getPermissionStatus();
        const serverStatus = await this.getStatus();

        if (permission === 'denied') {
            if (toggle) {
                toggle.checked = false;
                toggle.disabled = true;
            }
            if (statusText) {
                statusText.textContent = 'Bloqueado pelo navegador. Altere nas configurações.';
                statusText.className = 'text-danger';
            }
            if (testBtn) testBtn.disabled = true;
            return;
        }

        // Atualiza toggle
        if (toggle) {
            toggle.checked = this.isSubscribed && serverStatus.enabled;
            toggle.disabled = false;
        }

        // Atualiza texto de status
        if (statusText) {
            if (this.isSubscribed && serverStatus.enabled) {
                statusText.textContent = `Ativo em ${serverStatus.subscriptions} dispositivo(s)`;
                statusText.className = 'text-success';
            } else {
                statusText.textContent = 'Desativado';
                statusText.className = 'text-muted';
            }
        }

        // Atualiza badge
        if (statusBadge) {
            if (this.isSubscribed && serverStatus.enabled) {
                statusBadge.textContent = 'Ativo';
                statusBadge.className = 'badge bg-success';
            } else {
                statusBadge.textContent = 'Inativo';
                statusBadge.className = 'badge bg-secondary';
            }
        }

        // Atualiza botão de teste
        if (testBtn) {
            testBtn.disabled = !this.isSubscribed || !serverStatus.enabled;
        }
    }
};

// Exporta para uso global
window.PushNotifications = PushNotifications;
