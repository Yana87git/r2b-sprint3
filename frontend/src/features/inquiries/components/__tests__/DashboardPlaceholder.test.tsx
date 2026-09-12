import { render, screen } from '@testing-library/react'
import { DashboardPlaceholder } from '../DashboardPlaceholder'
import '@/shared/i18n'

describe('DashboardPlaceholder', () => {
  it('見出しを翻訳経由で表示する', () => {
    render(<DashboardPlaceholder />)
    expect(screen.getByRole('heading', { name: '引合書整理エージェント' })).toBeInTheDocument()
  })
})
