const VARIANTS = {
  primary:  'bg-saffron-500 hover:bg-saffron-600 text-white shadow-sm',
  secondary:'bg-cardamom-500 hover:bg-cardamom-600 text-white shadow-sm',
  outline:  'border border-beige-300 hover:bg-beige-100 text-gray-700',
  ghost:    'hover:bg-beige-100 text-gray-600',
  danger:   'bg-red-500 hover:bg-red-600 text-white',
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
        font-body transition-colors disabled:opacity-50 disabled:cursor-not-allowed
        focus:outline-none focus:ring-2 focus:ring-saffron-500 focus:ring-offset-1
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
