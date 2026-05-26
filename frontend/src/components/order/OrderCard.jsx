import { useNavigate } from 'react-router-dom'
import { ArrowRight, Package } from 'lucide-react'
import Badge from '../ui/Badge'
import dayjs from 'dayjs'

/* Progress bar inside card */
function ProgressBar({ value }) {
  return (
    <div className="w-full bg-beige-200 rounded-full h-1.5 overflow-hidden">
      <div
        className="h-full bg-saffron-500 rounded-full transition-all"
        style={{ width: `${Math.min(value, 100)}%` }}
      />
    </div>
  )
}

export default function OrderCard({ order }) {
  const navigate = useNavigate()
  const progress = order.overall_progress ?? 0

  return (
    <div
      onClick={() => navigate(`/orders/${order.id}`)}
      className="
        bg-white rounded-xl border border-beige-200 p-4 cursor-pointer
        shadow-card hover:shadow-card-hover hover:-translate-y-0.5
        transition-all duration-200
      "
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-saffron-50 border border-saffron-100 flex items-center justify-center shrink-0">
            <Package size={17} className="text-saffron-600" />
          </div>
          <div>
            <p className="font-heading font-semibold text-gray-900 text-sm leading-tight">
              {order.order_code}
            </p>
            <p className="text-[11px] text-gray-400 mt-0.5 font-body">
              {order.customer_name ?? 'Customer'}
            </p>
          </div>
        </div>
        <Badge status={order.status} />
      </div>

      {/* Commodity info */}
      <p className="text-sm text-gray-700 mb-1 font-body truncate">
        <span className="font-medium">{order.commodity_name ?? 'Commodity'}</span>
        {order.quantity_kg && (
          <span className="text-gray-400 ml-1 font-data text-xs">
            · {order.quantity_kg.toLocaleString()} kg
          </span>
        )}
      </p>

      {/* Destination */}
      {order.destination_country && (
        <p className="text-xs text-gray-400 mb-3 font-body">
          → {order.destination_country}
        </p>
      )}

      {/* Progress bar */}
      <ProgressBar value={progress} />
      <div className="flex justify-between items-center mt-1.5">
        <span className="text-[11px] text-gray-400 font-body">
          {order.active_stage?.replace(/_/g, ' ') ?? 'Not started'}
        </span>
        <span className="text-[11px] font-medium text-saffron-600">{progress}%</span>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-beige-100">
        <span className="text-[11px] text-gray-400">
          {order.created_at ? dayjs(order.created_at).format('DD MMM YYYY') : '—'}
        </span>
        <ArrowRight size={14} className="text-gray-400" />
      </div>
    </div>
  )
}
