import { useEffect, useState, useMemo } from 'react'
import { Search, Filter, Plus, Loader2, AlertCircle } from 'lucide-react'
import OrderCard from '../../components/order/OrderCard'
import Button from '../../components/ui/Button'
import useAuthStore from '../../store/authStore'
import { useNavigate } from 'react-router-dom'
import { ordersApi } from '../../api'

const STATUS_FILTERS = ['All', 'Active', 'SHIPPED', 'DELIVERED']

const STATUS_PROGRESS = {
  CREATED: 5,
  PROCUREMENT: 15,
  QA_TESTING: 35,
  PACKAGING: 50,
  DOCUMENTATION: 65,
  READY_FOR_SHIPMENT: 78,
  SHIPPED: 90,
  SHIPMENT_DISPATCHED: 90,
  DELIVERED: 100,
}

function normalizeOrder(order) {
  const status = order.status || order.shipment_status
  return {
    id: order.id,
    order_code: order.order_code,
    status,
    customer_name: order.company_name || order.customer_name,
    commodity_name: order.product_name || order.commodity_name,
    quantity_kg: order.quantity_kg ?? Number(order.quantity || 0),
    destination_country: order.destination_country,
    overall_progress: order.overall_progress ?? STATUS_PROGRESS[status] ?? 0,
    active_stage: order.active_stage || (status === 'DELIVERED' ? null : status),
    created_at: order.created_at,
  }
}

export default function OrdersListPage() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const isAdmin = useAuthStore((s) => s.isAdmin())
  const navigate = useNavigate()

  useEffect(() => {
    let isMounted = true
    async function loadOrders() {
      try {
        setLoading(true)
        setError(null)
        const res = await ordersApi.list({ page: 1, per_page: 100 })
        const data = Array.isArray(res.data?.data) ? res.data.data.map(normalizeOrder) : []
        if (isMounted) {
          setOrders(data)
        }
      } catch (err) {
        console.error('Error fetching orders:', err)
        if (isMounted) {
          setError('Failed to load orders. Please try again.')
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    loadOrders()
    return () => {
      isMounted = false
    }
  }, [])

  const filtered = useMemo(() => {
    return orders.filter((o) => {
      const matchSearch =
        o.order_code.toLowerCase().includes(search.toLowerCase()) ||
        (o.customer_name || '').toLowerCase().includes(search.toLowerCase()) ||
        (o.commodity_name || '').toLowerCase().includes(search.toLowerCase())
      const matchStatus =
        statusFilter === 'All'
          ? true
          : statusFilter === 'Active'
          ? !['DELIVERED', 'CANCELLED'].includes(o.status)
          : o.status === statusFilter
      return matchSearch && matchStatus
    })
  }, [orders, search, statusFilter])

  return (
    <div className="space-y-5 max-w-5xl">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading font-bold text-xl text-gray-900">Orders</h1>
          <p className="text-sm text-gray-500 font-body">
            {loading ? 'Loading shipments...' : `${orders.length} total shipments`}
          </p>
        </div>
        {isAdmin && (
          <Button icon={Plus} size="sm" onClick={() => navigate('/orders/new')}>
            New Order
          </Button>
        )}
      </div>

      {/* Search + filter bar */}
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="flex items-center gap-2 bg-white border border-beige-200 rounded-lg px-3 py-2 flex-1 shadow-card">
          <Search size={15} className="text-gray-400 shrink-0" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by order code, customer, commodity…"
            className="flex-1 text-sm text-gray-700 placeholder-gray-400 outline-none bg-transparent font-body"
            disabled={loading}
          />
        </div>

        <div className="flex gap-1 bg-white border border-beige-200 rounded-lg p-1 shadow-card">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              disabled={loading}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                statusFilter === f
                  ? 'bg-saffron-500 text-white'
                  : 'text-gray-500 hover:bg-beige-100'
              }`}
            >
              {f === 'SHIPPED' ? 'Dispatched' : f}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="py-24 text-center flex flex-col items-center justify-center gap-2">
          <Loader2 className="w-8 h-8 animate-spin text-saffron-500" />
          <p className="text-sm text-gray-400 font-body">Fetching shipments...</p>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center max-w-md mx-auto space-y-3">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto" />
          <p className="text-sm font-medium text-red-800">{error}</p>
        </div>
      ) : filtered.length ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {filtered.map((order) => (
            <OrderCard key={order.id} order={order} />
          ))}
        </div>
      ) : (
        <div className="py-16 text-center">
          <Filter size={36} className="text-beige-300 mx-auto mb-3" />
          <p className="text-sm text-gray-400 font-body">No orders match your filters.</p>
        </div>
      )}
    </div>
  )
}
