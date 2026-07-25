export interface FreteRule {
  prefix: string
  price: number
}

export function parseFreteRules(regras: string): FreteRule[] {
  return (regras || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [prefix, price] = line.split(':')
      return { prefix: (prefix || '').trim(), price: parseFloat(price) }
    })
    .filter((r) => r.prefix && !isNaN(r.price))
}

/** Primeira regra cujo prefixo bate com o CEP — mesma semântica do backend
 * (compute_frete em app/utils.py), não é "maior prefixo primeiro". */
export function computeFrete(regras: string, cep: string): number {
  if (!cep) return 0
  const rules = parseFreteRules(regras)
  const match = rules.find((r) => cep.startsWith(r.prefix))
  return match ? match.price : 0
}
