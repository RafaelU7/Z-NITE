/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_EMPRESA_ID: string
  readonly VITE_CAIXA_ID: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
