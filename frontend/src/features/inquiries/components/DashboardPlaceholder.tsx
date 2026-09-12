'use client'

import { Box, Container, Stack, Typography } from '@mui/material'
import { useTranslation } from 'react-i18next'

/** 画面の実体は明日（SCR-02 引合一覧）。ここは 0-5 の疎通確認。 */
export function DashboardPlaceholder() {
  const { t } = useTranslation()
  return (
    <Container component="main" sx={{ py: 4 }}>
      <Stack spacing={2}>
        <Typography variant="h1">{t('app.title')}</Typography>
        <Box>
          <Typography variant="body1">{t('dashboard.placeholder')}</Typography>
        </Box>
      </Stack>
    </Container>
  )
}
