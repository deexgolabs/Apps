const CACHE_NAME = 'app-shell-v1'
const APP_SHELL = ['/']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).catch(() => {})
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  )
  self.clients.claim()
})

self.addEventListener('push', (event) => {
  let data = { title: 'Notificação', body: '' }
  try {
    data = event.data.json()
  } catch {}

  event.waitUntil(
    self.registration.showNotification(data.title, { body: data.body })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      if (clients.length > 0) {
        return clients[0].focus()
      }
      return self.clients.openWindow('/')
    })
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)

  // Nunca interceptar assets internos do Next.js (chunks, HMR, devtools) — cachear
  // esses caminhos quebra o hot-reload em dev (chunk desatualizado -> erro -> reload
  // -> intercepta de novo -> loop infinito) e não traz benefício real em produção,
  // já que são hash-versionados pelo próprio Next.
  if (url.pathname.startsWith('/_next/')) return

  const isApi = url.pathname.startsWith('/api/') || url.port === '8000'

  if (isApi) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone))
          return response
        })
        .catch(() => caches.match(request))
    )
    return
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      const networkFetch = fetch(request)
        .then((response) => {
          const clone = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone))
          return response
        })
        .catch(() => cached)
      return cached || networkFetch
    })
  )
})
