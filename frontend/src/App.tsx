import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { SetupWizard } from '@/features/auth/components/SetupWizard'
import { CaixaPage } from '@/features/caixa/pages/CaixaPage'
import { PDVPage } from '@/features/pdv/pages/PDVPage'
import { GerencialLayout } from '@/features/gerencial/pages/GerencialLayout'
import { DashboardPage } from '@/features/gerencial/pages/DashboardPage'
import { ProdutosPage } from '@/features/gerencial/pages/ProdutosPage'
import { UsuariosPage } from '@/features/gerencial/pages/UsuariosPage'
import { CaixasPage } from '@/features/gerencial/pages/CaixasPage'
import { SessoesPage } from '@/features/gerencial/pages/SessoesPage'
import { RequireAuth, RequireCaixa, RequireGerente } from '@/shared/ui/Guards'
import { getSetupStatus } from '@/services/api/setup'
import { Loader2 } from 'lucide-react'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

function AppRoutes() {
  const [setupVerificado, setSetupVerificado] = useState(false)
  const [necessitaSetup, setNecessitaSetup] = useState(false)

  useEffect(() => {
    getSetupStatus()
      .then((s) => setNecessitaSetup(s.necessita_setup))
      .catch(() => {/* se falhar, assume que não precisa de setup */})
      .finally(() => setSetupVerificado(true))
  }, [])

  if (!setupVerificado) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-base">
        <Loader2 size={28} className="animate-spin text-accent" />
      </div>
    )
  }

  if (necessitaSetup) {
    return (
      <SetupWizard
        onConcluido={() => {
          setNecessitaSetup(false)
        }}
      />
    )
  }

  return (
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

      {/* Redirect raiz → login */}
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
