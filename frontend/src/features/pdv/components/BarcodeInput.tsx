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
          'flex items-center gap-3 rounded-xl border-2 bg-bg-surface-2 px-4 py-3',
          'transition-all duration-150',
          loading
            ? 'border-accent/30 bg-accent/5'
            : disabled
              ? 'border-border/30 opacity-40'
              : value
                ? 'border-accent/70 shadow-lg shadow-accent/10'
                : 'border-border focus-within:border-accent/70 focus-within:shadow-lg focus-within:shadow-accent/10',
        )}
      >
        {loading ? (
          <Loader2 size={20} className="shrink-0 animate-spin text-accent" />
        ) : (
          <Search size={20} className="shrink-0 text-text-muted" />
        )}

        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || loading}
          placeholder="Leia o código de barras ou digite o código..."
          className="flex-1 bg-transparent text-lg font-medium text-text-primary placeholder-text-muted/60 outline-none"
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          data-barcode="true"
          data-lpignore="true"
        />

        {value && (
          <kbd className="shrink-0 rounded border border-border bg-bg-surface-3 px-2 py-1 font-mono text-xs text-text-muted">
            Enter
          </kbd>
        )}
      </div>

      {/* Último produto lido */}
      {lastProduct && !loading && (
        <p className="absolute -bottom-5 left-4 text-xs text-success-text animate-fade-in">
          ✓ {lastProduct}
        </p>
      )}
    </div>
  )
}
