const VARIANTS = {
  primary:  'bg-forest-700 hover:bg-forest-800 text-white shadow-sm',
  secondary:'bg-forest-500 hover:bg-forest-600 text-white shadow-sm',
  outline:  'border border-agri-200 hover:bg-agri-100 text-slate-700',
  ghost:    'hover:bg-agri-100 text-slate-600',
  danger:   'bg-red-600 hover:bg-red-700 text-white',
}

const SIZES = {
  sm:  'px-3 py-1.5 text-xs gap-1.5',
  md:  'px-4 py-2 text-sm gap-2',
  lg:  'px-5 py-2.5 text-sm gap-2',
  icon:'w-9 h-9',
}

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon: Icon,
  loading,
  className = '',
  ...props
}) {
  return (
    <button
      className={`
        inline-flex items-center justify-center font-medium rounded-lg
        font-body transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed
        active:scale-[0.97]
        focus:outline-none focus:ring-2 focus:ring-forest-700 focus:ring-offset-1
        ${VARIANTS[variant]} ${SIZES[size]} ${className}
      `}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading ? (
        <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : Icon ? (
        <Icon size={size === 'sm' ? 14 : 16} />
      ) : null}
      {children}
    </button>
  )
}
