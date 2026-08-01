// Hash de visitante anônimo pra contar visitas únicas no painel de analytics
// do dono -- gerado e guardado só no localStorage do navegador, nunca deriva
// de IP nem de nenhum dado pessoal (LGPD-safe).
function visitorHashKey(appId: string) {
  return `visitor_hash_${appId}`
}

export function getOrCreateVisitorHash(appId: string): string {
  if (typeof window === 'undefined') return ''
  const key = visitorHashKey(appId)
  let hash = localStorage.getItem(key)
  if (!hash) {
    hash =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
    localStorage.setItem(key, hash)
  }
  return hash
}
