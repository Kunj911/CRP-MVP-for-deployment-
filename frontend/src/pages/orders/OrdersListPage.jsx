import { useState } from 'react'
import { Search, Filter, Plus } from 'lucide-react'
import OrderCard from '../../components/order/OrderCard'
import Button from '../../components/ui/Button'
import useAuthStore from '../../store/authStore'
import { useNavigate } from 'react-router-dom'

const ALL_ORDERS = [
  { id:1, order_code:'ORD-2025-001', customer_name:'Acme Spices LLC',  status:'QA_TESTING',          commodity_name:'Turmeric Powder',    quantity_kg:5000, destination_country:'Germany',    overall_progress:44,  active_stage:'QA_TESTING',          created_at:'2025-05-10' },
  { id:2, order_code:'ORD-2025-002', customer_name:'Spice World GmbH', status:'SHIPMENT_DISPATCHED', commodity_name:'Cumin Seeds',        quantity_kg:2500, destination_country:'Netherlands',overall_progress:78,  active_stage:'SHIPMENT_DISPATCHED', created_at:'2025-05-05' },
  { id:3, order_code:'ORD-2025-003', customer_name:'Gulf Flavors Co.', status:'PROCUREMENT',         commodity_name:'Black Pepper Whole', quantity_kg:8000, destination_country:'UAE',        overall_progress:11,  active_stage:'PROCUREMENT',         created_at:'2025-05-14' },
  { id:4, order_code:'ORD-2025-004', customer_name:'Eastern Herbs Inc',status:'DELIVERED',           commodity_name:'Coriander Seeds',    quantity_kg:3200, destination_country:'Canada',     overall_progress:100, active_stage:null,                  created_at:'2025-04-28' },
]

const STATUS_FILTERS = ['All','Active','SHIPMENT_DISPATCHED','DELIVERED']

export default function OrdersListPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const isAdmin = useAuthStore((s) => s.isAdmin())
  const navigate = useNavigate()

  const filtered = ALL_ORDERS.filter((o) => {
    const matchSearch = o.order_code.toLowerCase().includes(search.toLowerCase()) ||
      o.customer_name.toLowerCase().includes(search.toLowerCase()) ||
      o.commodity_name.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'All'
      ? true
      : statusFilter === 'Active'
        ? !['DELIVERED','CANCELLED'].includes(o.status)
        : o.status === statusFilter
    return matchSearch && matchStatus
  })

  return (
    <div className="space-y-5 max-w-5xl">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading font-bold text-xl text-gray-900">Orders</h1>
          <p className="text-sm text-gray-500 font-body">{ALL_ORDERS.length} total shipments</p>
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
          />
        </div>

        <div className="flex gap-1 bg-white border border-beige-200 rounded-lg p-1 shadow-card">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                statusFilter === f
                  ? 'bg-saffron-500 text-white'
                  : 'text-gray-500 hover:bg-beige-100'
              }`}
            >
              {f === 'SHIPMENT_DISPATCHED' ? 'Dispatched' : f}
            </button>
          ))}
        </div>
      </div>

      {/* Order grid */}
      {filtered.length ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {filtered.map((order) => <OrderCard key={order.id} order={order} />)}
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
