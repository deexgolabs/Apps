import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import GuidedTour from './GuidedTour'

const STEPS = [
  { selector: '[data-tour="a"]', title: 'Passo A', text: 'Texto A' },
  { selector: '[data-tour="b"]', title: 'Passo B', text: 'Texto B' },
]

function renderWithTargets(props: Partial<React.ComponentProps<typeof GuidedTour>> = {}) {
  return render(
    <div>
      <div data-tour="a">alvo A</div>
      <div data-tour="b">alvo B</div>
      <GuidedTour storageKey="test_tour_seen" steps={STEPS} {...props} />
    </div>
  )
}

describe('GuidedTour', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not show anything if already seen', () => {
    localStorage.setItem('test_tour_seen', '1')
    renderWithTargets()
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(screen.queryByText('Passo A')).not.toBeInTheDocument()
  })

  it('shows the first step after the initial delay', () => {
    renderWithTargets()
    act(() => {
      vi.advanceTimersByTime(500)
    })
    expect(screen.getByText('Passo A')).toBeInTheDocument()
  })

  it('marks the tour as seen and hides it when skipped', () => {
    renderWithTargets()
    act(() => {
      vi.advanceTimersByTime(500)
    })
    fireEvent.click(screen.getByText('Pular'))
    expect(localStorage.getItem('test_tour_seen')).toBe('1')
    expect(screen.queryByText('Passo A')).not.toBeInTheDocument()
  })

  it('advances through steps and calls onStepChange, finishing on the last step', () => {
    const onStepChange = vi.fn()
    renderWithTargets({ onStepChange })
    act(() => {
      vi.advanceTimersByTime(500)
    })
    expect(onStepChange).toHaveBeenCalledWith(0)

    fireEvent.click(screen.getByText('Próximo'))
    act(() => {
      vi.advanceTimersByTime(100)
    })
    expect(onStepChange).toHaveBeenCalledWith(1)
    expect(screen.getByText('Passo B')).toBeInTheDocument()
    expect(screen.getByText('Concluir')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Concluir'))
    expect(localStorage.getItem('test_tour_seen')).toBe('1')
    expect(screen.queryByText('Passo B')).not.toBeInTheDocument()
  })
})
