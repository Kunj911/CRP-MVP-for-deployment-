import { useEffect, useMemo, useState } from 'react'
import { Package, Upload, AlertTriangle, TrendingUp, CheckCircle, ArrowRight, Eye, FileWarning } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import OrderCard from '../../components/order/OrderCard'
import useAuthStore from '../../store/authStore'
import { ordersApi } from '../../api'

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

const DOC_TYPE_LABELS = {
  invoice:                  'Invoice',
  bill_of_lading:           'Bill of Lading',
  certificate_of_analysis:  'Certificate of Analysis (COA)',
  phytosanitary_certificate:'Phytosanitary Certificate',
  lab_report:               'Lab Report',
  packing_list:             'Packing List',
  product_specification:    'Product Spec',
  insurance_certificate:    'Insurance Certificate',
  purchase_order:           'Purchase Order (PO)',
  certificate_of_origin:    'Certificate of Origin (COO)',
  other:                    'Other',
}

function normalizeOrder(order) {
  const status = order.status || order.shipment_status
  return {
    id: order.id,
    order_code: order.order_code,
    customer_name: order.customer_name || order.company_name,
    status,
    commodity_name: order.commodity_name || order.product_name,
    quantity_kg: order.quantity_kg ?? Number(order.quantity || 0),
    destination_country: order.destination_country,
    overall_progress: order.overall_progress ?? STATUS_PROGRESS[status] ?? 0,
    active_stage: order.active_stage || (status === 'DELIVERED' ? null : status),
    created_at: order.created_at,
  }
}

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
  const navigate = useNavigate()
  const [orders, setOrders] = useState([])
  const [stats, setStats] = useState({
    active_orders_count: 0,
    dispatched_orders_count: 0,
    docs_uploaded_today: 0,
    pending_reviews_count: 0,
    orders_missing_required_documents: []
  })
  const [isRefreshing, setIsRefreshing] = useState(false)

  useEffect(() => {
    let isMounted = true

    async function fetchDashboardData() {
      setIsRefreshing(true)
      try {
        const [ordersRes, statsRes] = await Promise.all([
          ordersApi.list({ page: 1, per_page: 20 }),
          ordersApi.getDashboardStats()
        ])
        
        const data = Array.isArray(ordersRes.data?.data) ? ordersRes.data.data : []
        const dashboardStats = statsRes.data?.data
        
        if (isMounted) {
          setOrders(data.map(normalizeOrder))
          if (dashboardStats) {
            setStats(dashboardStats)
          }
        }
      } catch (err) {
        console.error('Failed to fetch dashboard stats:', err)
      } finally {
        if (isMounted) setIsRefreshing(false)
      }
    }

    fetchDashboardData()
    const intervalId = window.setInterval(fetchDashboardData, 15000)

    return () => {
      isMounted = false
      window.clearInterval(intervalId)
    }
  }, [])

  const activeOrders = useMemo(
    () => orders.filter((o) => !['DELIVERED', 'CANCELLED'].includes(o.status)),
    [orders]
  )

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Greeting */}
      <div>
        <h1 className="font-heading font-bold text-2xl text-gray-900">
          Good morning, {user?.full_name?.split(' ')[0]} 👋
        </h1>
        <p className="text-sm text-gray-500 font-body mt-0.5">
          {isRefreshing ? 'Refreshing export overview...' : "Here's your export overview for today."}
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon={Package}       label="Active Orders"      value={stats.active_orders_count}     color="bg-saffron-50 text-saffron-600" />
        <StatCard icon={TrendingUp}    label="Dispatched"         value={stats.dispatched_orders_count} color="bg-cardamom-50 text-cardamom-600" />
        <StatCard icon={Upload}        label="Uploads Today"      value={stats.docs_uploaded_today}     color="bg-cinnamon-50 text-cinnamon-500" />
        <StatCard icon={AlertTriangle} label="Pending Reviews"    value={stats.pending_reviews_count}   color="bg-amber-50 text-amber-600" />
      </div>

      {/* Active shipments */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-heading font-semibold text-gray-900">Active Shipments</h2>
          <button onClick={() => navigate('/orders')} className="text-sm text-saffron-600 hover:text-saffron-700 font-body">View all →</button>
        </div>
        
        {activeOrders.length === 0 ? (
          <div className="bg-white rounded-xl border border-beige-200 p-5 shadow-card text-center">
            <p className="text-sm text-gray-500 font-body">No active shipments in progress.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
            {activeOrders.slice(0, 6).map((order) => (
              <OrderCard key={order.id} order={order} />
            ))}
          </div>
        )}
      </div>

      {/* Orders Missing Required Documents */}
      <div>
        <h2 className="font-heading font-semibold text-gray-900 mb-3 flex items-center gap-1.5">
          <FileWarning className="w-5 h-5 text-amber-500" /> Orders Missing Required Documents
        </h2>
        
        {stats.orders_missing_required_documents.length === 0 ? (
          <div className="bg-white rounded-xl border border-beige-200 p-5 shadow-card flex items-center gap-3">
            <CheckCircle className="text-cardamom-500 shrink-0" size={20} />
            <p className="text-sm text-gray-600 font-body">All active orders have their required documentation complete and approved!</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-beige-200 shadow-card overflow-hidden divide-y divide-beige-100">
            {stats.orders_missing_required_documents.map((item) => (
              <div key={item.order_id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-beige-50/20 transition-colors">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => navigate(`/orders/${item.order_id}`)}
                      className="font-heading font-semibold text-gray-900 hover:text-saffron-600 transition-colors"
                    >
                      {item.order_code}
                    </button>
                    <span className="text-xs text-gray-400 font-body">· {item.customer_name}</span>
                    <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-beige-100 text-gray-600 font-body">
                      {item.status?.replace(/_/g, ' ')}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-[11px] text-gray-500 font-body">Missing Required:</span>
                    {item.missing_documents.map((docType) => (
                      <span key={docType} className="inline-flex text-[9px] font-medium px-2 py-0.5 rounded bg-red-50 text-red-600 border border-red-100 font-body">
                        {DOC_TYPE_LABELS[docType] ?? docType}
                      </span>
                    ))}
                  </div>
                </div>

                <button
                  onClick={() => navigate(`/orders/${item.order_id}`)}
                  className="self-start sm:self-center text-xs font-semibold text-saffron-600 hover:text-saffron-700 flex items-center gap-1 font-heading shrink-0 transition-colors"
                >
                  Manage Docs <ArrowRight size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent activity */}
      <div>
        <h2 className="font-heading font-semibold text-gray-900 mb-3">Recent Activity</h2>
        <div className="bg-white rounded-xl border border-beige-200 divide-y divide-beige-100 shadow-card overflow-hidden">
          {[
            { text: 'QA Report submitted for ORD-2026-MC04', time: '2h ago',  dot: 'bg-blue-400' },
            { text: 'Documents uploaded for ORD-2026-MC03',  time: '5h ago',  dot: 'bg-saffron-400' },
            { text: 'ORD-2026-MC02 shipment dispatched',     time: '1d ago',  dot: 'bg-cardamom-500' },
            { text: 'New order created: ORD-2026-MC05',      time: '2d ago',  dot: 'bg-gray-400' },
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
