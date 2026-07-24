export function endUserSessionKey(appId: string) {
  return `end_user_session_${appId}`
}

// Se o cliente final estiver logado (login_cadastro), anexa o token na criação
// do pedido pra ele aparecer em "Meus pedidos" — opcional, formulário funciona
// igual pra visitante sem conta.
export function endUserAuthHeader(appId: string): Record<string, string> {
  const saved = localStorage.getItem(endUserSessionKey(appId))
  if (!saved) return {}
  try {
    const { token } = JSON.parse(saved)
    return token ? { Authorization: `Bearer ${token}` } : {}
  } catch {
    return {}
  }
}
