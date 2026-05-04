import { useRef, useEffect, useState } from 'react'
import { Search, Loader2 } from 'lucide-react'
import clsx from 'clsx'

interface BarcodeInputProps {
  onScan: (ean: string) => void
  loading?: boolean
  disabled?: boolean
  lastProduct?: string | null
  autoFocusEnabled?: boolean
}

export function BarcodeInput({
  onScan,
  loading,
  disabled,
  lastProduct,
  autoFocusEnabled = true,
}: BarcodeInputProps) {
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // Foco automático quando o scanner pode assumir controle com segurança.
  useEffect(() => {
    if (!loading && !disabled && autoFocusEnabled) {
      inputRef.current?.focus()
    }
  }, [autoFocusEnabled, loading, disabled])

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && value.trim()) {
      onScan(value.trim())
      setValue('')
    }
  }

  return (
    <div className="relative">
      <div
        className={clsx(
          'flex items-center gap-3 rounded-xl border-2 px-4 py-4 transition-all duration-150',
          loading
            ? 'border-pdv-fiscal/40 bg-pdv-surface/80'
            : disabled
              ? 'border-pdv-border/30 bg-pdv-surface/40 opacity-40'
              : value
                ? 'border-pdv-fiscal/80 bg-[#081820] shadow-[0_0_0_3px_rgba(50,200,91,0.18),0_0_32px_rgba(50,200,91,0.10)]'
                : 'border-pdv-border/80 bg-[#081820] focus-within:border-pdv-fiscal/80 focus-within:shadow-[0_0_0_3px_rgba(50,200,91,0.18),0_0_32px_rgba(50,200,91,0.10)]',
        )}
      >
        {loading ? (
          <Loader2 size={22} className="shrink-0 animate-spin text-pdv-fiscal" />
        ) : (
          <Search size={24} className="shrink-0 text-pdv-fiscal" />
        )}

        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || loading}
          placeholder="Leia o código de barras ou digite o código..."
          className="flex-1 bg-transparent text-lg font-medium text-slate-100 placeholder-slate-500 outline-none"
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          data-barcode="true"
          data-lpignore="true"
        />

        {value && (
          <kbd className="shrink-0 rounded border border-slate-600 bg-slate-700 px-2 py-1 font-mono text-xs text-slate-400">
            Enter
          </kbd>
        )}
      </div>

      {/* Último produto lido */}
      {lastProduct && !loading && (
          <p className="absolute -bottom-5 left-4 text-xs text-pdv-fiscal animate-fade-in">
          ✓ {lastProduct}
        </p>
      )}
    </div>
  )
}
