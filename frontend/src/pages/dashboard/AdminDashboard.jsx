import { useEffect, useMemo, useState } from 'react'
import { Package, Upload, AlertTriangle, TrendingUp, CheckCircle, ArrowRight, FileWarning, Sprout } from 'lucide-react'
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
    <div className="bg-white rounded-xl border border-agri-200 p-4 flex items-center gap-3 shadow-card hover:shadow-card-hover transition-shadow">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${color}`}>
        <Icon size={18} />
      </div>
      <div>
        <p className="text-2xl font-bold font-heading text-slate-900">{value}</p>
        <p className="text-xs text-slate-500 font-body">{label}</p>
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
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-forest-800 via-forest-700 to-forest-900 p-6 md:p-8">
        <div className="absolute inset-0 opacity-10" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='80' height='80' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M40 5L75 40L40 75L5 40Z' fill='none' stroke='white' stroke-width='1'/%3E%3C/svg%3E")`,
          backgroundSize: '80px 80px',
        }} />
        <div className="relative z-10 flex items-center justify-between">
          <div>
            <h1 className="font-heading font-bold text-2xl md:text-3xl text-white">
              Good morning, {user?.full_name?.split(' ')[0]}
            </h1>
            <p className="text-forest-200 text-sm font-body mt-1 max-w-md">
              {isRefreshing ? 'Refreshing your farm overview...' : 'Track your agricultural shipments and documentation at a glance.'}
            </p>
          </div>
          <div className="hidden md:flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-xl px-4 py-3 border border-white/20">
            <Sprout className="w-5 h-5 text-forest-300" />
            <span className="text-white text-sm font-medium font-heading">Harvest Season</span>
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="animate-slide-up stagger-1"><StatCard icon={Package} label="Active Orders" value={stats.active_orders_count} color="bg-forest-50 text-forest-700" /></div>
        <div className="animate-slide-up stagger-2"><StatCard icon={TrendingUp} label="Dispatched" value={stats.dispatched_orders_count} color="bg-forest-100 text-forest-700" /></div>
        <div className="animate-slide-up stagger-3"><StatCard icon={Upload} label="Uploads Today" value={stats.docs_uploaded_today} color="bg-amber-50 text-amber-700" /></div>
        <div className="animate-slide-up stagger-4"><StatCard icon={AlertTriangle} label="Pending Reviews" value={stats.pending_reviews_count} color="bg-orange-50 text-orange-600" /></div>
      </div>

      {/* Active shipments */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-heading font-semibold text-slate-900">Active Shipments</h2>
          <button onClick={() => navigate('/orders')} className="text-sm text-forest-700 hover:text-forest-800 font-body font-medium">View all →</button>
        </div>
        
        {activeOrders.length === 0 ? (
          <div className="bg-white rounded-xl border border-agri-200 p-5 shadow-card text-center">
            <p className="text-sm text-slate-500 font-body">No active shipments in progress.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
            {activeOrders.slice(0, 6).map((order, i) => (
              <div key={order.id} className="animate-fade-in" style={{ animationDelay: `${i * 0.06}s` }}>
                <OrderCard order={order} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Orders Missing Required Documents */}
      <div>
        <h2 className="font-heading font-semibold text-slate-900 mb-3 flex items-center gap-1.5">
          <FileWarning className="w-5 h-5 text-amber-500" /> Orders Missing Required Documents
        </h2>
        
        {stats.orders_missing_required_documents.length === 0 ? (
          <div className="bg-white rounded-xl border border-agri-200 p-5 shadow-card flex items-center gap-3">
            <CheckCircle className="text-forest-500 shrink-0" size={20} />
            <p className="text-sm text-slate-600 font-body">All active orders have their required documentation complete and approved!</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-agri-200 shadow-card overflow-hidden divide-y divide-agri-100">
            {stats.orders_missing_required_documents.map((item) => (
              <div key={item.order_id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-agri-50/20 transition-colors">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => navigate(`/orders/${item.order_id}`)}
                      className="font-heading font-semibold text-slate-900 hover:text-forest-700 transition-colors"
                    >
                      {item.order_code}
                    </button>
                    <span className="text-xs text-slate-400 font-body">· {item.customer_name}</span>
                    <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-agri-100 text-slate-600 font-body">
                      {item.status?.replace(/_/g, ' ')}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-[11px] text-slate-500 font-body">Missing Required:</span>
                    {item.missing_documents.map((docType) => (
                      <span key={docType} className="inline-flex text-[9px] font-medium px-2 py-0.5 rounded bg-red-50 text-red-600 border border-red-100 font-body">
                        {DOC_TYPE_LABELS[docType] ?? docType}
                      </span>
                    ))}
                  </div>
                </div>

                <button
                  onClick={() => navigate(`/orders/${item.order_id}`)}
                  className="self-start sm:self-center text-xs font-semibold text-forest-700 hover:text-forest-800 flex items-center gap-1 font-heading shrink-0 transition-colors"
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
        <h2 className="font-heading font-semibold text-slate-900 mb-3">Recent Activity</h2>
        <div className="bg-white rounded-xl border border-agri-200 divide-y divide-agri-100 shadow-card overflow-hidden">
          {[
            { text: 'QA Report submitted for ORD-2026-MC04', time: '2h ago',  dot: 'bg-blue-400' },
            { text: 'Documents uploaded for ORD-2026-MC03',  time: '5h ago',  dot: 'bg-forest-500' },
            { text: 'ORD-2026-MC02 shipment dispatched',     time: '1d ago',  dot: 'bg-forest-700' },
            { text: 'New order created: ORD-2026-MC05',      time: '2d ago',  dot: 'bg-slate-400' },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-3">
              <span className={`w-2 h-2 rounded-full shrink-0 ${item.dot}`} />
              <p className="text-sm text-slate-700 font-body flex-1">{item.text}</p>
              <span className="text-[11px] text-slate-400 shrink-0">{item.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
