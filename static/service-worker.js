// Horário Inteligente PWA Service Worker
// Versão: 1.0.0

const CACHE_NAME = 'horario-inteligente-v1.0.0';
const OFFLINE_URL = '/static/offline.html';

// Arquivos essenciais para cachear
const ESSENTIAL_FILES = [
  '/static/login.html',
  '/static/calendario-unificado.html',
  '/static/minha-agenda.html',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// Instalação do Service Worker
self.addEventListener('install', (event) => {
  console.log('🔧 Service Worker: Instalando...');

  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('📦 Service Worker: Cacheando arquivos essenciais');
      // Cacheia arquivos essenciais (ignora erros)
      return cache.addAll(ESSENTIAL_FILES.map(url => new Request(url, { cache: 'reload' })))
        .catch(err => {
          console.warn('⚠️ Alguns arquivos não foram cacheados:', err);
        });
    })
  );

  // Força ativação imediata
  self.skipWaiting();
});

// Ativação do Service Worker
self.addEventListener('activate', (event) => {
  console.log('✅ Service Worker: Ativando...');

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('🗑️ Service Worker: Removendo cache antigo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );

  // Assume controle imediatamente
  return self.clients.claim();
});

// Interceptação de requisições (estratégia: Network First, fallback para Cache)
self.addEventListener('fetch', (event) => {
  // Ignora requisições que não são GET
  if (event.request.method !== 'GET') {
    return;
  }

  // Ignora requisições para APIs externas
  if (!event.request.url.startsWith(self.location.origin)) {
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
            if (event.request.url.includes('/static/') ||
                event.request.url.endsWith('.html') ||
                event.request.url.endsWith('.css') ||
                event.request.url.endsWith('.js')) {
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

// Mensagens do cliente
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => caches.delete(cacheName))
        );
      })
    );
  }
});

console.log('🚀 ProSaúde Service Worker carregado!');
