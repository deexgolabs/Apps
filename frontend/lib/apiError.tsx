import toast from 'react-hot-toast'

// Erros 403 de limite de plano sempre terminam com "Faça upgrade..." (ver
// PLAN_LIMITS no backend) — quando é esse caso, o toast vira clicável.
export function showApiError(error: any, fallback: string) {
  const detail = error?.response?.data?.detail
  const message = typeof detail === 'string' ? detail : fallback

  if (error?.response?.status === 403 && typeof detail === 'string' && detail.toLowerCase().includes('upgrade')) {
    toast.error(
      (t) => (
        <span>
          {message}{' '}
          <a
            href="/dashboard/billing"
            className="underline font-semibold"
            onClick={() => toast.dismiss(t.id)}
          >
            Fazer upgrade
          </a>
        </span>
      ),
      { duration: 6000 }
    )
    return
  }

  toast.error(message)
}
