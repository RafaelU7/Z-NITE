import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { CaixaPage } from '@/features/caixa/pages/CaixaPage'
import { PDVPage } from '@/features/pdv/pages/PDVPage'
import { RequireAuth, RequireCaixa } from '@/shared/ui/Guards'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route
            path="/caixa"
            element={
              <RequireAuth>
                <CaixaPage />
              </RequireAuth>
            }
          />

          <Route
            path="/pdv"
            element={
              <RequireAuth>
                <RequireCaixa>
                  <PDVPage />
                </RequireCaixa>
              </RequireAuth>
            }
          />

          {/* Redirect raiz → login ou pdv */}
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
