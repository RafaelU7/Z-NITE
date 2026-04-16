import clsx from 'clsx'
import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'success'
type Size = 'sm' | 'md' | 'lg' | 'xl'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  kbd?: string // ex: "F10"
  fullWidth?: boolean
}

const variants: Record<Variant, string> = {
  primary:
    'bg-accent hover:bg-accent-hover text-white border border-accent/50 shadow-lg shadow-accent/20',
  secondary:
    'bg-bg-surface-2 hover:bg-bg-surface-3 text-text-primary border border-border',
  danger:
    'bg-danger/10 hover:bg-danger/20 text-danger-text border border-danger/30',
  ghost:
    'bg-transparent hover:bg-bg-surface-2 text-text-secondary hover:text-text-primary border border-transparent',
  success:
    'bg-success/10 hover:bg-success/20 text-success-text border border-success/30',
}

const sizes: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-5 py-3 text-base gap-2',
  xl: 'px-6 py-4 text-lg gap-3 font-semibold',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  kbd,
  fullWidth,
  children,
  className,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={clsx(
        'relative inline-flex items-center justify-center rounded-lg font-medium',
        'transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        variants[variant],
        sizes[size],
        fullWidth && 'w-full',
        className,
      )}
    >
      {loading ? (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        children
      )}
      {kbd && !loading && (
        <span className="ml-auto rounded border border-current/20 bg-current/10 px-1.5 py-0.5 font-mono text-xs opacity-60">
          {kbd}
        </span>
      )}
    </button>
  )
}
