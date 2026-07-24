import * as Sentry from '@sentry/nextjs'

// Sem NEXT_PUBLIC_SENTRY_DSN (padrão), isso não faz nada — nenhum evento é
// coletado nem enviado. Defina a variável no .env pra ativar de verdade.
if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
    tracesSampleRate: 0.1,
  })
}
