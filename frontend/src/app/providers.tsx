'use client'

import { useState, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter'
import { tokens } from '@/shared/theme/tokens'
import '@/shared/i18n'

// 脱・標準MUI（.claude/rules/design-guidelines.md）。既定の青・紫・Roboto・大文字ボタン・影を残さない
const theme = createTheme({
  palette: {
    primary: {
      light: tokens.colors.main[300],
      main: tokens.colors.main[700],
      dark: tokens.colors.main[900],
      contrastText: tokens.colors.main[100],
    },
    secondary: { main: tokens.colors.main[500] },
    error: { main: tokens.colors.error },
    background: { default: tokens.colors.background, paper: tokens.colors.surface },
    text: { primary: tokens.colors.text.primary, secondary: tokens.colors.text.secondary },
    divider: tokens.colors.main[300],
  },
  typography: {
    fontFamily: tokens.typography.fontBody,
    fontSize: tokens.typography.size.md,
    h1: { fontFamily: tokens.typography.fontHeading, fontSize: tokens.typography.size.xl, fontWeight: tokens.typography.weight.heading },
    h2: { fontFamily: tokens.typography.fontHeading, fontSize: tokens.typography.size.lg, fontWeight: tokens.typography.weight.heading },
    h3: { fontFamily: tokens.typography.fontHeading, fontSize: tokens.typography.size.md, fontWeight: tokens.typography.weight.heading },
    body1: { fontSize: tokens.typography.size.md },
    body2: { fontSize: tokens.typography.size.sm },
    caption: { fontSize: tokens.typography.size.xs, color: tokens.colors.text.meta },
    button: { fontWeight: tokens.typography.weight.label },
  },
  shape: { borderRadius: tokens.radius },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { textTransform: 'none' } },
    },
    // 影は使わず罫線で区切る（03-spec 3章「影は使わない」）
    MuiCard: { defaultProps: { variant: 'outlined' } },
    MuiPaper: { defaultProps: { variant: 'outlined' } },
  },
})

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, refetchOnWindowFocus: false },
          mutations: { retry: 1 },
        },
      }),
  )

  return (
    <AppRouterCacheProvider>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
        </ThemeProvider>
      </QueryClientProvider>
    </AppRouterCacheProvider>
  )
}
