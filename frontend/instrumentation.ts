// Carrega a config do Sentry pro lado servidor/edge (App Router). Sem
// NEXT_PUBLIC_SENTRY_DSN definida, os arquivos importados são no-ops.
export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    await import('./sentry.server.config')
  }
  if (process.env.NEXT_RUNTIME === 'edge') {
    await import('./sentry.edge.config')
  }
}
