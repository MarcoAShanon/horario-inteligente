/**
 * CSRF Protection Utility
 * Sistema Horário Inteligente
 *
 * Este módulo gerencia tokens CSRF para proteção contra ataques Cross-Site Request Forgery
 */

const CSRFManager = {
    tokenCookieName: 'csrf_token',
    headerName: 'X-CSRF-Token',

    /**
     * Obtém o token CSRF do cookie
     * @returns {string|null} Token CSRF ou null se não encontrado
     */
    getToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === this.tokenCookieName) {
                return decodeURIComponent(value);
            }
        }
        return null;
    },

    /**
     * Solicita um novo token CSRF do servidor
     * @returns {Promise<string|null>} Token CSRF ou null em caso de erro
     */
    async fetchToken() {
        try {
            const response = await fetch('/api/csrf-token', {
                method: 'GET',
                credentials: 'include'  // Importante para receber o cookie
            });

            if (response.ok) {
                const data = await response.json();
                // Armazenar o token em memória para uso nos headers
                this._token = data.csrf_token;
                return this._token;
            }
            console.error('Erro ao obter token CSRF:', response.status);
            return null;
        } catch (error) {
            console.error('Erro ao obter token CSRF:', error);
            return null;
        }
    },

    /**
     * Token armazenado em memória
     */
    _token: null,

    /**
     * Garante que um token CSRF válido existe
     * Busca um novo se necessário
     * @returns {Promise<string|null>}
     */
    async ensureToken() {
        // Primeiro verificar token em memória
        if (this._token) {
            return this._token;
        }
        // Se não tem, buscar do servidor
        return await this.fetchToken();
    },

    /**
     * Adiciona o header CSRF a um objeto de headers
     * @param {Object} headers - Objeto de headers existente
     * @returns {Object} Headers com token CSRF adicionado
     */
    addToHeaders(headers = {}) {
        const token = this._token || this.getToken();
        if (token) {
            headers[this.headerName] = token;
        }
        return headers;
    },

    /**
     * Wrapper para fetch que automaticamente adiciona o token CSRF
     * @param {string} url - URL da requisição
     * @param {Object} options - Opções do fetch
     * @returns {Promise<Response>}
     */
    async fetch(url, options = {}) {
        // Garantir que temos um token
        await this.ensureToken();

        // Adicionar headers CSRF para métodos que modificam dados
        const method = (options.method || 'GET').toUpperCase();
        if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
            options.headers = this.addToHeaders(options.headers || {});
        }

        // Sempre incluir credentials para cookies
        options.credentials = options.credentials || 'include';

        return fetch(url, options);
    },

    /**
     * Inicializa o CSRF manager
     * Deve ser chamado quando a página carrega
     */
    async init() {
        // Buscar token CSRF ao carregar a página
        await this.ensureToken();

        // Interceptar submissões de formulários
        this.interceptForms();

        console.log('CSRFManager inicializado');
    },

    /**
     * Intercepta formulários para adicionar token CSRF
     */
    interceptForms() {
        document.addEventListener('submit', async (event) => {
            const form = event.target;

            // Ignorar formulários com action externa
            const action = form.getAttribute('action') || '';
            if (action.startsWith('http') && !action.includes(window.location.host)) {
                return;
            }

            // Adicionar campo hidden com token CSRF se não existir
            let csrfInput = form.querySelector('input[name="csrf_token"]');
            if (!csrfInput) {
                csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrf_token';
                form.appendChild(csrfInput);
            }

            // Atualizar valor do token
            const token = await this.ensureToken();
            if (token) {
                csrfInput.value = token;
            }
        });
    }
};

// Configurar axios se disponível
if (typeof axios !== 'undefined') {
    // Interceptor para adicionar token CSRF em todas as requisições
    axios.interceptors.request.use(async (config) => {
        const method = config.method.toUpperCase();

        if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
            const token = CSRFManager._token || await CSRFManager.fetchToken();
            if (token) {
                config.headers[CSRFManager.headerName] = token;
            }
        }

        return config;
    }, (error) => {
        return Promise.reject(error);
    });

    // Interceptor para lidar com erros CSRF (403)
    axios.interceptors.response.use(
        (response) => response,
        async (error) => {
            if (error.response && error.response.status === 403) {
                const data = error.response.data;
                if (data && data.error === 'csrf_error') {
                    // Tentar renovar o token e repetir a requisição
                    console.warn('Token CSRF expirado, renovando...');
                    await CSRFManager.fetchToken();

                    // Repetir requisição original
                    const config = error.config;
                    config.headers[CSRFManager.headerName] = CSRFManager._token;
                    return axios(config);
                }
            }
            return Promise.reject(error);
        }
    );
}

// Exportar para uso global
window.CSRFManager = CSRFManager;

// Auto-inicializar quando o DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => CSRFManager.init());
} else {
    CSRFManager.init();
}
