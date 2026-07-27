import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// @testing-library/react só registra a limpeza automática entre testes
// quando detecta um `afterEach` global — como vitest.config.ts não liga
// `globals: true` (cada arquivo importa describe/it/afterEach do 'vitest'
// explicitamente), precisa registrar aqui manualmente, senão o DOM de um
// teste vaza pro próximo (getByRole encontra elementos duplicados).
afterEach(() => {
  cleanup()
})

// O Node 22+ expõe um localStorage global próprio (Storage do node:internal)
// que, nesse ambiente de teste, aparece tanto em globalThis quanto em
// window mas sem implementar a Storage API inteira (ex: sem .clear()) —
// então nem sempre dá pra confiar no localStorage "de fábrica" do jsdom.
// Substitui por uma implementação mínima e completa, em memória, garantindo
// que getItem/setItem/removeItem/clear/length se comportem como no browser
// tanto pro componente sob teste quanto pros próprios testes.
class MemoryStorage implements Storage {
  private store = new Map<string, string>()

  get length() {
    return this.store.size
  }

  clear(): void {
    this.store.clear()
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? this.store.get(key)! : null
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null
  }

  removeItem(key: string): void {
    this.store.delete(key)
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value))
  }
}

const memoryStorage = new MemoryStorage()

for (const target of [globalThis, typeof window !== 'undefined' ? window : undefined]) {
  if (!target) continue
  Object.defineProperty(target, 'localStorage', {
    value: memoryStorage,
    writable: true,
    configurable: true,
  })
}
