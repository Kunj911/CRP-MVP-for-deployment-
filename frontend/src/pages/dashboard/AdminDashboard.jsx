import { Package, Upload, AlertTriangle, TrendingUp } from 'lucide-react'
import OrderCard from '../../components/order/OrderCard'
import useAuthStore from '../../store/authStore'

// Demo data — replace with TanStack Query hooks
const DEMO_ORDERS = [
  { id: 1, order_code: 'ORD-2025-001', customer_name: 'Acme Spices LLC', status: 'QA_TESTING',          commodity_name: 'Turmeric Powder',    quantity_kg: 5000, destination_country: 'Germany',   overall_progress: 44, active_stage: 'QA_TESTING',           created_at: '2025-05-10' },
  { id: 2, order_code: 'ORD-2025-002', customer_name: 'Spice World GmbH', status: 'SHIPMENT_DISPATCHED', commodity_name: 'Cumin Seeds',        quantity_kg: 2500, destination_country: 'Netherlands',overall_progress: 78, active_stage: 'SHIPMENT_DISPATCHED',  created_at: '2025-05-05' },
  { id: 3, order_code: 'ORD-2025-003', customer_name: 'Gulf Flavors Co.',  status: 'PROCUREMENT',         commodity_name: 'Black Pepper Whole', quantity_kg: 8000, destination_country: 'UAE',        overall_progress: 11, active_stage: 'PROCUREMENT',          created_at: '2025-05-14' },
  { id: 4, order_code: 'ORD-2025-004', customer_name: 'Eastern Herbs Inc', status: 'DELIVERED',           commodity_name: 'Coriander Seeds',    quantity_kg: 3200, destination_country: 'Canada',    overall_progress: 100, active_stage: null,                  created_at: '2025-04-28' },
]

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-white rounded-xl border border-beige-200 p-4 flex items-center gap-3 shadow-card">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${color}`}>
        <Icon size={18} />
      </div>
      <div>
        <p className="text-2xl font-bold font-heading text-gray-900">{value}</p>
        <p className="text-xs text-gray-500 font-body">{label}</p>
      </div>
    </div>
  )
}

export default function AdminDashboard() {
  const user = useAuthStore((s) => s.user)
  const active    = DEMO_ORDERS.filter((o) => o.status !== 'DELIVERED' && o.status !== 'CANCELLED')
  const dispatched= DEMO_ORDERS.filter((o) => o.status === 'SHIPMENT_DISPATCHED')

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Greeting */}
      <div>
        <h1 className="font-heading font-bold text-2xl text-gray-900">
          Good morning, {user?.full_name?.split(' ')[0]} 👋
        </h1>
        <p className="text-sm text-gray-500 font-body mt-0.5">Here's your export overview for today.</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon={Package}       label="Active Orders"      value={active.length}     color="bg-saffron-50 text-saffron-600" />
        <StatCard icon={TrendingUp}    label="Dispatched"         value={dispatched.length} color="bg-cardamom-50 text-cardamom-600" />
        <StatCard icon={AlertTriangle} label="Pending Uploads"    value={3}                 color="bg-amber-50 text-amber-600" />
        <StatCard icon={Upload}        label="Docs This Month"    value={12}                color="bg-cinnamon-50 text-cinnamon-500" />
      </div>

      {/* Active shipments */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-heading font-semibold text-gray-900">Active Shipments</h2>
          <a href="/orders" className="text-sm text-saffron-600 hover:text-saffron-700 font-body">View all →</a>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {active.map((order) => (
            <OrderCard key={order.id} order={order} />
          ))}
        </div>
      </div>

      {/* Recent activity */}
      <div>
        <h2 className="font-heading font-semibold text-gray-900 mb-3">Recent Activity</h2>
        <div className="bg-white rounded-xl border border-beige-200 divide-y divide-beige-100 shadow-card overflow-hidden">
          {[
            { text: 'QA Report submitted for ORD-2025-001', time: '2h ago',  dot: 'bg-blue-400' },
            { text: 'Documents uploaded for ORD-2025-002',  time: '5h ago',  dot: 'bg-saffron-400' },
            { text: 'ORD-2025-002 shipment dispatched',     time: '1d ago',  dot: 'bg-cardamom-500' },
            { text: 'New order created: ORD-2025-003',      time: '2d ago',  dot: 'bg-gray-400' },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-3">
              <span className={`w-2 h-2 rounded-full shrink-0 ${item.dot}`} />
              <p className="text-sm text-gray-700 font-body flex-1">{item.text}</p>
              <span className="text-[11px] text-gray-400 shrink-0">{item.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
