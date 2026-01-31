// Horário Inteligente PWA Service Worker
// ==================== VERSIONAMENTO ====================
// IMPORTANTE: Incrementar a cada deploy para forçar atualização
const CACHE_VERSION = '1.2.0';
const CACHE_PREFIX = 'horario-inteligente';
const CACHE_NAME = `${CACHE_PREFIX}-v${CACHE_VERSION}`;
const OFFLINE_URL = '/static/offline.html';

// Arquivos essenciais para cachear
const ESSENTIAL_FILES = [
  '/static/login.html',
  '/static/calendario-unificado.html',
  '/static/minha-agenda.html',
  '/static/perfil.html',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/static/js/push-notifications.js'
];

// ==================== INSTALAÇÃO ====================
self.addEventListener('install', (event) => {
  console.log(`🔧 Service Worker v${CACHE_VERSION}: Instalando...`);

  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('📦 Service Worker: Cacheando arquivos essenciais');
      return cache.addAll(ESSENTIAL_FILES.map(url => new Request(url, { cache: 'reload' })))
        .catch(err => {
          console.warn('⚠️ Alguns arquivos não foram cacheados:', err);
        });
    })
  );

  // Força ativação imediata (nova versão assume controle)
  self.skipWaiting();
});

// ==================== ATIVAÇÃO ====================
self.addEventListener('activate', (event) => {
  console.log(`✅ Service Worker v${CACHE_VERSION}: Ativando...`);

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          // Remove TODOS os caches antigos deste app
          if (cacheName.startsWith(CACHE_PREFIX) && cacheName !== CACHE_NAME) {
            console.log('🗑️ Service Worker: Removendo cache antigo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      // Notifica todos os clientes sobre a nova versão
      return self.clients.matchAll({ type: 'window' }).then((clients) => {
        clients.forEach((client) => {
          client.postMessage({
            type: 'SW_UPDATED',
            version: CACHE_VERSION
          });
        });
      });
    })
  );

  // Assume controle imediatamente de todas as páginas
  return self.clients.claim();
});

// ==================== FETCH (Network First) ====================
self.addEventListener('fetch', (event) => {
  // Ignora requisições que não são GET
  if (event.request.method !== 'GET') {
    return;
  }

  // Ignora requisições para APIs externas e WebSockets
  if (!event.request.url.startsWith(self.location.origin) ||
      event.request.url.includes('/api/') ||
      event.request.url.includes('/ws/')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Se a resposta é válida, cacheia e retorna
        if (response && response.status === 200) {
          const responseClone = response.clone();

          caches.open(CACHE_NAME).then((cache) => {
            // Cacheia apenas páginas HTML e recursos estáticos
            const url = event.request.url;
            if (url.includes('/static/') ||
                url.endsWith('.html') ||
                url.endsWith('.css') ||
                url.endsWith('.js') ||
                url.endsWith('.png') ||
                url.endsWith('.jpg') ||
                url.endsWith('.svg')) {
              cache.put(event.request, responseClone);
            }
          });
        }

        return response;
      })
      .catch(() => {
        // Se falhar, tenta buscar no cache
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            console.log('📦 Service Worker: Servindo do cache:', event.request.url);
            return cachedResponse;
          }

          // Se for uma navegação e não está em cache, mostra página offline
          if (event.request.mode === 'navigate') {
            return caches.match(OFFLINE_URL);
          }

          // Retorna resposta vazia para outros recursos
          return new Response('Recurso não disponível offline', {
            status: 503,
            statusText: 'Service Unavailable'
          });
        });
      })
  );
});

// ==================== MENSAGENS DO CLIENTE ====================
self.addEventListener('message', (event) => {
  // Força atualização imediata
  if (event.data && event.data.type === 'SKIP_WAITING') {
    console.log('⚡ Service Worker: Skip waiting solicitado');
    self.skipWaiting();
  }

  // Limpa todos os caches
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    console.log('🗑️ Service Worker: Limpando todos os caches');
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => caches.delete(cacheName))
        );
      })
    );
  }

  // Retorna versão atual
  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({
      type: 'VERSION',
      version: CACHE_VERSION
    });
  }

  // Verifica se há atualização disponível
  if (event.data && event.data.type === 'CHECK_UPDATE') {
    self.registration.update().then(() => {
      console.log('🔍 Service Worker: Verificação de atualização concluída');
    });
  }
});

// ==================== PUSH NOTIFICATIONS ====================

// Recebimento de Push Notification
self.addEventListener('push', (event) => {
  console.log('📬 Push notification recebida');

  let data = {
    title: 'Horário Inteligente',
    body: 'Nova notificação',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/badge-72x72.png',
    url: '/static/dashboard.html',
    tag: 'default'
  };

  // Parse dos dados da notificação
  if (event.data) {
    try {
      const payload = event.data.json();
      data = {
        title: payload.title || data.title,
        body: payload.body || data.body,
        icon: payload.icon || data.icon,
        badge: payload.badge || data.badge,
        url: payload.url || data.url,
        tag: payload.tag || data.tag,
        timestamp: payload.timestamp || Date.now()
      };
    } catch (e) {
      console.error('Erro ao parsear dados do push:', e);
      data.body = event.data.text() || data.body;
    }
  }

  const options = {
    body: data.body,
    icon: data.icon,
    badge: data.badge,
    tag: data.tag,
    data: {
      url: data.url,
      timestamp: data.timestamp
    },
    vibrate: [200, 100, 200],
    requireInteraction: true,
    actions: [
      {
        action: 'open',
        title: 'Ver detalhes'
      },
      {
        action: 'close',
        title: 'Fechar'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Click na notificação
self.addEventListener('notificationclick', (event) => {
  console.log('🖱️ Notificação clicada:', event.action);

  event.notification.close();

  // Se clicou em fechar, apenas fecha
  if (event.action === 'close') {
    return;
  }

  // URL padrão ou a URL específica da notificação
  const urlToOpen = event.notification.data?.url || '/static/dashboard.html';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((windowClients) => {
        // Procura uma janela já aberta do app
        for (const client of windowClients) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            // Navega para a URL e foca
            client.navigate(urlToOpen);
            return client.focus();
          }
        }
        // Se não encontrou janela aberta, abre uma nova
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// Fechamento da notificação
self.addEventListener('notificationclose', (event) => {
  console.log('❌ Notificação fechada pelo usuário');
});

console.log(`🚀 Horário Inteligente Service Worker v${CACHE_VERSION} carregado!`);
