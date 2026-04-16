import clsx from 'clsx'
import { forwardRef } from 'react'
import type { InputHTMLAttributes, ReactNode } from 'react'

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'prefix'> {
  label?: string
  error?: string
  hint?: string
  prefix?: ReactNode
  suffix?: ReactNode
  kbd?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input({
  label,
  error,
  hint,
  prefix,
  suffix,
  kbd,
  className,
  id,
  ...rest
}, ref) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-text-secondary">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {prefix && (
          <span className="absolute left-3 flex items-center text-text-muted">{prefix}</span>
        )}
        <input
          id={inputId}
          ref={ref}
          {...rest}
          className={clsx(
            'w-full rounded-lg border bg-bg-surface-2 text-text-primary placeholder-text-muted',
            'px-3 py-2.5 text-sm transition-all duration-150',
            'focus:outline-none focus:ring-2 focus:ring-accent/60 focus:border-accent/60',
            error
              ? 'border-danger/60 focus:ring-danger/40'
              : 'border-border focus:border-accent/40',
            prefix && 'pl-9',
            suffix && 'pr-10',
            className,
          )}
        />
        {suffix && (
          <span className="absolute right-3 flex items-center text-text-muted">{suffix}</span>
        )}
        {kbd && (
          <span className="absolute right-2 rounded border border-border bg-bg-surface-3 px-1.5 py-0.5 font-mono text-xs text-text-muted">
            {kbd}
          </span>
        )}
      </div>
      {error && <p className="text-xs text-danger-text">{error}</p>}
      {hint && !error && <p className="text-xs text-text-muted">{hint}</p>}
    </div>
  )
})
