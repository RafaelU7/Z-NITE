import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { CaixaPage } from '@/features/caixa/pages/CaixaPage'
import { PDVPage } from '@/features/pdv/pages/PDVPage'
import { GerencialLayout } from '@/features/gerencial/pages/GerencialLayout'
import { DashboardPage } from '@/features/gerencial/pages/DashboardPage'
import { ProdutosPage } from '@/features/gerencial/pages/ProdutosPage'
import { UsuariosPage } from '@/features/gerencial/pages/UsuariosPage'
import { CaixasPage } from '@/features/gerencial/pages/CaixasPage'
import { SessoesPage } from '@/features/gerencial/pages/SessoesPage'
import { RequireAuth, RequireCaixa, RequireGerente } from '@/shared/ui/Guards'

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
          {/* Login dedicado para retaguarda — mesma tela, URL separada */}
          <Route path="/gerencial/login" element={<LoginPage />} />

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

          {/* Retaguarda gerencial */}
          <Route
            path="/gerencial"
            element={
              <RequireGerente>
                <GerencialLayout />
              </RequireGerente>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="produtos" element={<ProdutosPage />} />
            <Route path="usuarios" element={<UsuariosPage />} />
            <Route path="caixas" element={<CaixasPage />} />
            <Route path="sessoes" element={<SessoesPage />} />
          </Route>

          {/* Redirect raiz → login ou pdv */}
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
