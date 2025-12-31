/**
 * Analytics Tracker - Horário Inteligente
 * Sistema próprio de analytics para rastreamento de visitantes
 */
(function() {
    'use strict';

    const HI_ANALYTICS = {
        endpoint: '/api/analytics/track',
        sessionKey: 'hi_session_id',
        visitorKey: 'hi_visitor_id',
        startTime: Date.now(),
        maxScrollDepth: 0,

        /**
         * Gera um ID único (fingerprint simplificado)
         */
        generateId: function() {
            const array = new Uint32Array(4);
            crypto.getRandomValues(array);
            return Array.from(array, x => x.toString(16).padStart(8, '0')).join('');
        },

        /**
         * Gera fingerprint do navegador para identificar visitante único
         */
        generateVisitorId: function() {
            const components = [
                navigator.userAgent,
                navigator.language,
                screen.width + 'x' + screen.height,
                screen.colorDepth,
                new Date().getTimezoneOffset(),
                navigator.hardwareConcurrency || 'unknown',
                navigator.deviceMemory || 'unknown'
            ];

            // Hash simples dos componentes
            let hash = 0;
            const str = components.join('|');
            for (let i = 0; i < str.length; i++) {
                const char = str.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash;
            }

            return Math.abs(hash).toString(16) + '-' + this.generateId().substring(0, 16);
        },

        /**
         * Obtém ou cria ID do visitante (persistente via localStorage)
         */
        getVisitorId: function() {
            let visitorId = localStorage.getItem(this.visitorKey);
            if (!visitorId) {
                visitorId = this.generateVisitorId();
                localStorage.setItem(this.visitorKey, visitorId);
            }
            return visitorId;
        },

        /**
         * Obtém ou cria ID da sessão (por sessão do navegador)
         */
        getSessionId: function() {
            let sessionId = sessionStorage.getItem(this.sessionKey);
            if (!sessionId) {
                sessionId = this.generateId();
                sessionStorage.setItem(this.sessionKey, sessionId);
            }
            return sessionId;
        },

        /**
         * Detecta tipo de dispositivo
         */
        getDeviceType: function() {
            const ua = navigator.userAgent.toLowerCase();
            if (/tablet|ipad|playbook|silk/i.test(ua)) {
                return 'tablet';
            }
            if (/mobile|iphone|ipod|android|blackberry|opera mini|iemobile/i.test(ua)) {
                return 'mobile';
            }
            return 'desktop';
        },

        /**
         * Detecta navegador
         */
        getBrowser: function() {
            const ua = navigator.userAgent;
            if (ua.indexOf('Chrome') > -1 && ua.indexOf('Edg') === -1) return 'Chrome';
            if (ua.indexOf('Safari') > -1 && ua.indexOf('Chrome') === -1) return 'Safari';
            if (ua.indexOf('Firefox') > -1) return 'Firefox';
            if (ua.indexOf('Edg') > -1) return 'Edge';
            if (ua.indexOf('Opera') > -1 || ua.indexOf('OPR') > -1) return 'Opera';
            return 'Outro';
        },

        /**
         * Detecta sistema operacional
         */
        getOS: function() {
            const ua = navigator.userAgent;
            if (ua.indexOf('Win') > -1) return 'Windows';
            if (ua.indexOf('Mac') > -1) return 'macOS';
            if (ua.indexOf('Linux') > -1 && ua.indexOf('Android') === -1) return 'Linux';
            if (ua.indexOf('Android') > -1) return 'Android';
            if (ua.indexOf('iPhone') > -1 || ua.indexOf('iPad') > -1) return 'iOS';
            return 'Outro';
        },

        /**
         * Extrai parâmetros UTM da URL
         */
        getUTMParams: function() {
            const params = new URLSearchParams(window.location.search);
            return {
                utm_source: params.get('utm_source'),
                utm_medium: params.get('utm_medium'),
                utm_campaign: params.get('utm_campaign')
            };
        },

        /**
         * Detecta página atual
         */
        getCurrentPage: function() {
            const path = window.location.pathname;
            if (path === '/' || path === '/index.html' || path === '/static/index.html') {
                return 'landing';
            }
            if (path.includes('/demo/') || path.includes('/demo')) {
                return 'demo';
            }
            if (path.includes('/dashboard-demo')) {
                return 'demo_dashboard';
            }
            if (path.includes('/precos') || path.includes('/pricing')) {
                return 'precos';
            }
            if (path.includes('/contato')) {
                return 'contato';
            }
            return 'outro';
        },

        /**
         * Envia dados para o servidor
         */
        track: function(evento, eventoDados) {
            const utm = this.getUTMParams();

            const data = {
                visitor_id: this.getVisitorId(),
                session_id: this.getSessionId(),
                pagina: this.getCurrentPage(),
                url_path: window.location.pathname,
                referrer: document.referrer || null,
                utm_source: utm.utm_source,
                utm_medium: utm.utm_medium,
                utm_campaign: utm.utm_campaign,
                dispositivo: this.getDeviceType(),
                navegador: this.getBrowser(),
                sistema_operacional: this.getOS(),
                evento: evento || 'pageview',
                evento_dados: eventoDados ? JSON.stringify(eventoDados) : null,
                tempo_na_pagina: null,
                scroll_depth: null
            };

            // Usar sendBeacon se disponível (mais confiável para eventos de saída)
            // Importante: usar Blob com tipo application/json para FastAPI aceitar
            if (navigator.sendBeacon) {
                const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
                navigator.sendBeacon(this.endpoint, blob);
            } else {
                fetch(this.endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                    keepalive: true
                }).catch(function() {});
            }
        },

        /**
         * Rastreia pageview
         */
        trackPageview: function() {
            this.track('pageview');
        },

        /**
         * Rastreia evento customizado
         */
        trackEvent: function(evento, dados) {
            this.track(evento, dados);
        },

        /**
         * Rastreia clique em elemento
         */
        trackClick: function(elemento, evento) {
            this.track(evento || 'click', { element: elemento });
        },

        /**
         * Rastreia scroll depth
         */
        trackScroll: function() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
            const scrollPercent = Math.round((scrollTop / scrollHeight) * 100);

            if (scrollPercent > this.maxScrollDepth) {
                this.maxScrollDepth = scrollPercent;
            }
        },

        /**
         * Rastreia saída da página
         */
        trackExit: function() {
            const tempoNaPagina = Math.round((Date.now() - this.startTime) / 1000);

            const data = {
                visitor_id: this.getVisitorId(),
                session_id: this.getSessionId(),
                pagina: this.getCurrentPage(),
                url_path: window.location.pathname,
                evento: 'exit',
                tempo_na_pagina: tempoNaPagina,
                scroll_depth: this.maxScrollDepth
            };

            if (navigator.sendBeacon) {
                const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
                navigator.sendBeacon(this.endpoint, blob);
            }
        },

        /**
         * Configura rastreamento automático de cliques em CTAs
         */
        setupClickTracking: function() {
            const self = this;

            // Botões de Demo
            document.querySelectorAll('a[href*="demo"], button[data-action="demo"]').forEach(function(el) {
                el.addEventListener('click', function() {
                    self.trackEvent('click_demo', { text: el.textContent.trim() });
                });
            });

            // Botões de Contato
            document.querySelectorAll('a[href*="contato"], a[href^="mailto:"], button[data-action="contato"]').forEach(function(el) {
                el.addEventListener('click', function() {
                    self.trackEvent('click_contato', { text: el.textContent.trim() });
                });
            });

            // Links de WhatsApp
            document.querySelectorAll('a[href*="whatsapp"], a[href*="wa.me"]').forEach(function(el) {
                el.addEventListener('click', function() {
                    self.trackEvent('click_whatsapp', { text: el.textContent.trim() });
                });
            });

            // Formulário de contato
            document.querySelectorAll('form').forEach(function(form) {
                form.addEventListener('submit', function() {
                    self.trackEvent('form_submit', { form_id: form.id || 'unknown' });
                });
            });
        },

        /**
         * Inicializa o tracker
         */
        init: function() {
            const self = this;

            // Pageview inicial
            this.trackPageview();

            // Setup click tracking
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    self.setupClickTracking();
                });
            } else {
                this.setupClickTracking();
            }

            // Track scroll
            let scrollTimeout;
            window.addEventListener('scroll', function() {
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(function() {
                    self.trackScroll();
                }, 100);
            });

            // Track exit
            window.addEventListener('beforeunload', function() {
                self.trackExit();
            });

            // Visibilidade da página (para quando o usuário muda de aba)
            document.addEventListener('visibilitychange', function() {
                if (document.visibilityState === 'hidden') {
                    self.trackExit();
                }
            });
        }
    };

    // Expor globalmente para uso manual
    window.HI_ANALYTICS = HI_ANALYTICS;

    // Auto-inicializar
    HI_ANALYTICS.init();

})();
