import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
dayjs.extend(relativeTime)
import {
  Package, Truck, CheckCircle, FileWarning,
  Loader2, Sprout, Clock, ArrowRight,
  ChevronRight, AlertCircle, Activity,
  FileText, Image, Upload, Download,
} from 'lucide-react'
import OrderCard from '../../components/order/OrderCard'
import MilestoneTimeline from '../../components/milestone/MilestoneTimeline'
import DocumentVault from '../../components/documents/DocumentVault'
import useAuthStore from '../../store/authStore'
import { ordersApi, documentsApi, uploadsApi } from '../../api'
import { useEffect, useState } from 'react'

const STATUS_COLORS = {
  CREATED: '#94a3b8',
  PROCUREMENT: '#f59e0b',
  QA_TESTING: '#8b5cf6',
  PACKAGING: '#3b82f6',
  DOCUMENTATION: '#06b6d4',
  READY_FOR_SHIPMENT: '#10b981',
  SHIPPED: '#22c55e',
  SHIPMENT_DISPATCHED: '#16a34a',
  DELIVERED: '#15803d',
  CANCELLED: '#ef4444',
}

const STATUS_LABELS = {
  CREATED: 'Created',
  PROCUREMENT: 'Processing',
  QA_TESTING: 'QA Testing',
  PACKAGING: 'Packaging',
  DOCUMENTATION: 'Documentation',
  READY_FOR_SHIPMENT: 'Ready to Ship',
  SHIPPED: 'Shipped',
  SHIPMENT_DISPATCHED: 'Dispatched',
  DELIVERED: 'Delivered',
  CANCELLED: 'Cancelled',
}

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

const CHART_COLORS = ['#3b82f6', '#f59e0b', '#8b5cf6', '#06b6d4', '#10b981']

function countByStatus(data) {
  if (!data?.orders_by_status?.length) return []
  const sorted = [...data.orders_by_status].sort((a, b) => b.count - a.count)
  return sorted.map((s) => ({
    name: STATUS_LABELS[s.status] || s.status,
    value: s.count,
    color: STATUS_COLORS[s.status] || '#94a3b8',
  }))
}

function KpiCard({ icon: Icon, label, value, color, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-agri-200 shadow-card p-4 animate-pulse">
        <div className="h-8 w-20 bg-agri-100 rounded mb-2" />
        <div className="h-4 w-24 bg-agri-100 rounded" />
      </div>
    )
  }
  return (
    <div className="bg-white rounded-xl border border-agri-200 shadow-card p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0`} style={{ backgroundColor: `${color}15` }}>
        <Icon size={20} style={{ color }} />
      </div>
      <div>
        <p className="text-2xl font-heading font-bold text-slate-900">{value}</p>
        <p className="text-xs text-slate-500 font-body">{label}</p>
      </div>
    </div>
  )
}

function emptyState(message, icon) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      {icon}
      <p className="text-sm text-slate-400 font-body mt-2">{message}</p>
    </div>
  )
}

function normalizeOrder(order) {
  const status = order.status || order.shipment_status
  return {
    id: order.id,
    order_code: order.order_code,
    status,
    customer_name: order.customer_name || order.company_name,
    commodity_name: order.commodity_name || order.product_name,
    quantity_kg: order.quantity_kg ?? Number(order.quantity || 0),
    destination_country: order.destination_country,
    overall_progress: order.overall_progress ?? STATUS_PROGRESS[status] ?? 0,
    active_stage: order.active_stage || (status === 'DELIVERED' ? null : status),
    created_at: order.created_at,
    product_count: order.product_count ?? undefined,
  }
}

function ActivityIcon({ type }) {
  const lower = (type || '').toLowerCase()
  if (lower.includes('status') || lower.includes('stage') || lower.includes('move')) {
    return <Activity size={14} className="text-blue-500" />
  }
  if (lower.includes('photo') || lower.includes('image') || lower.includes('upload')) {
    return lower.includes('photo') ? <Image size={14} className="text-amber-500" /> : <Upload size={14} className="text-violet-500" />
  }
  if (lower.includes('document') || lower.includes('file') || lower.includes('cert')) {
    return <FileText size={14} className="text-cyan-500" />
  }
  return <Clock size={14} className="text-slate-400" />
}

function formatActivityTime(timestamp) {
  if (!timestamp) return ''
  const d = dayjs(timestamp)
  const now = dayjs()
  if (d.isAfter(now.subtract(1, 'hour'))) return d.fromNow()
  if (d.isAfter(now.subtract(1, 'day'))) return d.format('HH:mm')
  return d.format('DD MMM')
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const { name, value, color } = payload[0].payload
  return (
    <div className="bg-white border border-agri-200 shadow-lg rounded-lg px-3 py-2 text-xs font-body">
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
        <span className="font-medium text-slate-700">{name}</span>
      </div>
      <p className="text-slate-500 mt-0.5">{value} order{value !== 1 ? 's' : ''}</p>
    </div>
  )
}

export default function CustomerDashboard() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const [activeOrder, setActiveOrder] = useState(null)
  const [milestones, setMilestones] = useState([])
  const [documents, setDocuments] = useState([])
  const [checklist, setChecklist] = useState([])
  const [loading, setLoading] = useState(true)
  const [timelineLoading, setTimelineLoading] = useState(false)
  const [docsLoading, setDocsLoading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const { data: dashRaw, isLoading: dashLoading, isError: dashError } = useQuery({
    queryKey: ['client-dashboard'],
    queryFn: () => ordersApi.getClientDashboard().then((r) => r.data?.data),
    refetchInterval: 60000,
    staleTime: 30000,
    retry: 2,
  })

  const dashboardData = dashRaw || {}
  const chartData = useMemo(() => countByStatus(dashboardData), [dashboardData])
  const topProducts = dashboardData.top_products || []
  const recentActivity = dashboardData.recent_activity || []
  const recentOrders = dashboardData.recent_orders || []
  const kpis = [
    { icon: Package, label: 'Total Orders', value: dashboardData.total_orders ?? '—', color: '#3b82f6' },
    { icon: Truck, label: 'Active Orders', value: dashboardData.active_orders ?? '—', color: '#f59e0b' },
    { icon: CheckCircle, label: 'Completed', value: dashboardData.completed_orders ?? '—', color: '#22c55e' },
    { icon: FileWarning, label: 'Pending Documents', value: dashboardData.pending_documents ?? '—', color: '#ef4444' },
  ]

  const fetchDashboardStats = async (showLoading = false) => {
    if (showLoading && !activeOrder) setLoading(true)
    setIsRefreshing(true)
    try {
      const res = await ordersApi.list({ page: 1, per_page: 5 })
      const data = Array.isArray(res.data?.data) ? res.data.data.map(normalizeOrder) : []
      const nextActiveOrder = data.find((order) => !['DELIVERED', 'CANCELLED'].includes(order.status)) || data[0] || null

      setActiveOrder(nextActiveOrder)
      setLoading(false)

      if (nextActiveOrder) {
        setTimelineLoading(true)
        setDocsLoading(true)

        const [timelineRes, docsRes, checklistRes, orderDetailRes] = await Promise.all([
          ordersApi.getTimeline(nextActiveOrder.id),
          documentsApi.listByOrder(nextActiveOrder.id),
          uploadsApi.getDocumentChecklist(nextActiveOrder.id),
          ordersApi.getById(nextActiveOrder.id),
        ])

        setMilestones(timelineRes.data?.data?.milestones || [])
        setDocuments(Array.isArray(docsRes.data?.data) ? docsRes.data.data : [])
        setChecklist(Array.isArray(checklistRes.data?.data) ? checklistRes.data.data : [])

        const products = orderDetailRes.data?.data?.products || []
        if (products.length > 0) {
          const topProduct = products.reduce((best, p) =>
            (p.quantity || 0) > (best.quantity || 0) ? p : best
          )
          setActiveOrder({
            ...nextActiveOrder,
            commodity_name: topProduct.product_name,
            quantity_kg: Number(topProduct.quantity || 0),
            product_count: products.length,
          })
        }
      } else {
        setMilestones([])
        setDocuments([])
        setChecklist([])
      }
    } catch (err) {
      console.error('Error fetching dashboard stats:', err)
    } finally {
      setLoading(false)
      setTimelineLoading(false)
      setDocsLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    fetchDashboardStats(true)
    const intervalId = window.setInterval(() => fetchDashboardStats(false), 60000)
    return () => window.clearInterval(intervalId)
  }, [])

  const handleDownload = async (doc) => {
    try {
      const response = await documentsApi.download(doc.id)
      const blob = new Blob([response.data], { type: response.headers['content-type'] || 'application/octet-stream' })
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      link.download = doc.file_name || 'document.pdf'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(link.href)
    } catch (error) {
      console.error('Download failed:', error)
      alert('Failed to download file.')
    }
  }

  const requiredChecklist = checklist.filter((c) => c.required)
  const requiredCount = requiredChecklist.length
  const approvedRequiredCount = requiredChecklist.filter((c) => c.approved).length
  const docProgressPercent = requiredCount > 0 ? Math.round((approvedRequiredCount / requiredCount) * 100) : 0
  const latestInvoice = documents.find((d) => d.document_type === 'invoice')
  const latestBL = documents.find((d) => d.document_type === 'bill_of_lading')

  const showLoading = (loading && !activeOrder) || dashLoading

  if (showLoading) {
    return (
      <div className="py-24 text-center flex flex-col items-center justify-center gap-2">
        <Loader2 className="w-8 h-8 animate-spin text-forest-700" />
        <p className="text-sm text-slate-400 font-body">Loading your dashboard...</p>
      </div>
    )
  }

  if (dashError && !dashboardData.total_orders) {
    return (
      <div className="py-24 text-center flex flex-col items-center justify-center gap-2">
        <AlertCircle className="w-8 h-8 text-red-400" />
        <p className="text-sm text-slate-500 font-body">Unable to load dashboard data. Please try again later.</p>
      </div>
    )
  }

  const hasNoOrders = !dashLoading && !dashboardData.total_orders

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-forest-700 to-forest-900 p-6 md:p-8">
        <div className="absolute inset-0 opacity-10" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='80' height='80' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M40 5L75 40L40 75L5 40Z' fill='none' stroke='white' stroke-width='1'/%3E%3C/svg%3E")`,
          backgroundSize: '80px 80px',
        }} />
        <div className="relative z-10">
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-white">
            Hello, {user?.full_name?.split(' ')[0] || 'there'}
          </h1>
          <p className="text-forest-200 text-sm font-body mt-1">
            {isRefreshing ? 'Refreshing your shipments...' : 'Track your agricultural shipments in real time.'}
          </p>
        </div>
      </div>

      {/* Section 1 — KPI Summary Cards */}
      <section className="animate-slide-up stagger-1">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {kpis.map((kpi) => (
            <KpiCard key={kpi.label} {...kpi} loading={dashLoading} />
          ))}
        </div>
      </section>

      {hasNoOrders ? (
        <>
          <section className="bg-white rounded-xl border border-agri-200 shadow-card p-8 animate-slide-up stagger-2">
            {emptyState(
              'You don\'t have any orders yet. Once orders are created, your dashboard will display shipment charts, product insights, and activity updates here.',
              <Package size={40} className="text-agri-300" />
            )}
          </section>
          <section className="animate-slide-up stagger-3">
            <h2 className="font-heading font-semibold text-slate-800 text-sm mb-2">Active Order</h2>
            {activeOrder ? <OrderCard order={activeOrder} /> : (
              <div className="bg-white rounded-xl border border-agri-200 shadow-card p-5">
                <p className="text-sm text-slate-500 font-body">No active orders found.</p>
              </div>
            )}
          </section>
        </>
      ) : (
        <>
          {/* Section 2 — Chart Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-slide-up stagger-2">
            {/* Shipment Status Chart */}
            <section className="bg-white rounded-xl border border-agri-200 shadow-card p-4">
              <div className="flex items-center gap-2 border-b border-agri-100 pb-3 mb-3">
                <Truck size={16} className="text-forest-700" />
                <h2 className="font-heading font-semibold text-sm text-slate-900">Shipment Status</h2>
              </div>
              {chartData.length === 0 ? (
                emptyState('No shipment data yet.', <AlertCircle size={32} className="text-agri-300" />)
              ) : (
                <div className="flex items-center justify-center">
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={85}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        {chartData.map((entry, i) => (
                          <Cell key={i} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-1.5 min-w-[120px]">
                    {chartData.map((entry) => (
                      <div key={entry.name} className="flex items-center gap-2 text-xs font-body">
                        <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: entry.color }} />
                        <span className="text-slate-600 truncate">{entry.name}</span>
                        <span className="font-medium text-slate-800 ml-auto">{entry.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>

            {/* Top Products Widget */}
            <section className="bg-white rounded-xl border border-agri-200 shadow-card p-4">
              <div className="flex items-center gap-2 border-b border-agri-100 pb-3 mb-3">
                <Package size={16} className="text-forest-700" />
                <h2 className="font-heading font-semibold text-sm text-slate-900">Top Products</h2>
              </div>
              {topProducts.length === 0 ? (
                emptyState('No product data available yet.', <Package size={32} className="text-agri-300" />)
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={topProducts} layout="vertical" margin={{ left: 0, right: 20, top: 5, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
                    <YAxis type="category" dataKey="product_name" width={100} tick={{ fontSize: 11 }} tickFormatter={(v) => v.length > 14 ? v.slice(0, 14) + '…' : v} />
                    <Tooltip
                      contentStyle={{ fontSize: 12, border: '1px solid #e2e8f0', borderRadius: 8 }}
                      formatter={(val, name, props) => [`${Number(val).toLocaleString()} ${props.payload.unit || 'kg'}`, 'Total']}
                    />
                    <Bar dataKey="total_quantity" radius={[0, 4, 4, 0]}>
                      {topProducts.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </section>
          </div>

          {/* Section 3 — Activity + Orders Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-slide-up stagger-3">
            {/* Recent Activity Feed */}
            <section className="bg-white rounded-xl border border-agri-200 shadow-card p-4">
              <div className="flex items-center gap-2 border-b border-agri-100 pb-3 mb-3">
                <Clock size={16} className="text-forest-700" />
                <h2 className="font-heading font-semibold text-sm text-slate-900">Recent Activity</h2>
              </div>
              {recentActivity.length === 0 ? (
                emptyState('No recent activity.', <Clock size={32} className="text-agri-300" />)
              ) : (
                <div className="space-y-0 max-h-[280px] overflow-y-auto">
                  {recentActivity.map((event, i) => (
                    <div
                      key={event.order_id + '-' + i}
                      className="flex items-start gap-3 py-2.5 border-b border-agri-50 last:border-0"
                    >
                      <div className="w-7 h-7 rounded-full bg-agri-50 border border-agri-100 flex items-center justify-center shrink-0 mt-0.5">
                        <ActivityIcon type={event.type} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-slate-700 font-body leading-snug">{event.description}</p>
                        <p className="text-[10px] text-slate-400 font-body mt-0.5">
                          {formatActivityTime(event.timestamp)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* Quick Order Snapshot */}
            <section className="bg-white rounded-xl border border-agri-200 shadow-card p-4">
              <div className="flex items-center justify-between border-b border-agri-100 pb-3 mb-3">
                <div className="flex items-center gap-2">
                  <Sprout size={16} className="text-forest-700" />
                  <h2 className="font-heading font-semibold text-sm text-slate-900">Recent Orders</h2>
                </div>
                <button
                  onClick={() => navigate('/orders')}
                  className="text-xs text-forest-700 font-medium font-body hover:underline flex items-center gap-0.5"
                >
                  View All <ChevronRight size={12} />
                </button>
              </div>
              {recentOrders.length === 0 ? (
                emptyState('No orders yet.', <Sprout size={32} className="text-agri-300" />)
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-body">
                    <thead>
                      <tr className="text-left text-slate-400 border-b border-agri-50">
                        <th className="pb-2 pr-3 font-medium">Order</th>
                        <th className="pb-2 pr-3 font-medium">Status</th>
                        <th className="pb-2 pr-3 font-medium hidden sm:table-cell">Progress</th>
                        <th className="pb-2 font-medium hidden md:table-cell">Updated</th>
                        <th className="pb-2" />
                      </tr>
                    </thead>
                    <tbody>
                      {recentOrders.map((order) => {
                        const statusColor = STATUS_COLORS[order.status] || '#94a3b8'
                        const statusLabel = STATUS_LABELS[order.status] || order.status
                        return (
                          <tr
                            key={order.id}
                            onClick={() => navigate(`/orders/${order.id}`)}
                            className="border-b border-agri-50 last:border-0 hover:bg-agri-50/50 cursor-pointer transition-colors"
                          >
                            <td className="py-2.5 pr-3">
                              <span className="font-semibold text-slate-800">{order.order_code}</span>
                            </td>
                            <td className="py-2.5 pr-3">
                              <span
                                className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium"
                                style={{ backgroundColor: `${statusColor}12`, color: statusColor }}
                              >
                                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: statusColor }} />
                                {statusLabel}
                              </span>
                            </td>
                            <td className="py-2.5 pr-3 hidden sm:table-cell">
                              <div className="flex items-center gap-2">
                                <div className="w-16 bg-agri-100 rounded-full h-1.5 overflow-hidden">
                                  <div
                                    className="h-full rounded-full"
                                    style={{ width: `${order.overall_progress || 0}%`, backgroundColor: statusColor }}
                                  />
                                </div>
                                <span className="text-[10px] text-slate-500 font-medium">{order.overall_progress || 0}%</span>
                              </div>
                            </td>
                            <td className="py-2.5 pr-3 text-slate-400 hidden md:table-cell">
                              {order.created_at ? dayjs(order.created_at).format('DD MMM YYYY') : '—'}
                            </td>
                            <td className="py-2.5">
                              <ArrowRight size={12} className="text-slate-300" />
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>

          {/* Section 4 — Existing Active Order Detail */}
          <section className="animate-slide-up stagger-4">
            <h2 className="font-heading font-semibold text-slate-800 text-sm mb-2">Active Order Detail</h2>
            {activeOrder ? (
              <OrderCard order={activeOrder} />
            ) : (
              <div className="bg-white rounded-xl border border-agri-200 shadow-card p-5">
                <p className="text-sm text-slate-500 font-body">No active orders found.</p>
              </div>
            )}
          </section>

          {activeOrder && (
            <section className="bg-white rounded-xl border border-agri-200 shadow-card overflow-hidden animate-slide-up stagger-4">
              <div className="px-5 py-4 border-b border-agri-100">
                <h2 className="font-heading font-semibold text-slate-900">Shipment Timeline</h2>
                <p className="text-xs text-slate-400 font-body mt-0.5">
                  {activeOrder.order_code} · {activeOrder.overall_progress}% complete
                </p>
              </div>
              <div className="px-5 pt-4 pb-2">
                <div className="w-full bg-agri-100 rounded-full h-2">
                  <div className="h-full bg-forest-700 rounded-full transition-all duration-300" style={{ width: `${activeOrder.overall_progress}%` }} />
                </div>
                <div className="flex justify-between mt-1">
                  <span className="text-[11px] text-slate-400">
                    {activeOrder.active_stage?.replace(/_/g, ' ') ?? 'No active stage'}
                  </span>
                  <span className="text-[11px] font-medium text-forest-700">{activeOrder.overall_progress}%</span>
                </div>
              </div>
              <div className="px-5 pb-5 pt-3">
                {timelineLoading ? (
                  <div className="py-6 text-center flex flex-col items-center justify-center gap-1.5">
                    <Loader2 className="w-5 h-5 animate-spin text-forest-700" />
                    <span className="text-xs text-slate-400 font-body">Loading timeline...</span>
                  </div>
                ) : (
                  <MilestoneTimeline milestones={milestones} orderId={activeOrder.id} onStageComplete={() => fetchDashboardStats(false)} />
                )}
              </div>
            </section>
          )}

          {activeOrder && checklist.length > 0 && (
            <section className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-slide-up stagger-4">
              <div className="bg-white border border-agri-200 rounded-xl p-5 shadow-card space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-heading font-semibold text-slate-800 text-sm">Documentation Progress</h3>
                  <FileWarning className="w-5 h-5 text-forest-700" />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-xs font-body text-slate-500">
                    <span>Checklist Approved</span>
                    <span className="font-semibold text-slate-700">{approvedRequiredCount} of {requiredCount} Required</span>
                  </div>
                  <div className="w-full bg-agri-100 rounded-full h-2">
                    <div className="h-full bg-forest-500 rounded-full transition-all duration-300" style={{ width: `${docProgressPercent}%` }} />
                  </div>
                  <p className="text-[11px] text-slate-400 font-body">
                    {docProgressPercent === 100 ? 'All required documents have been verified and approved!' : 'Awaiting verification/approval of remaining required files.'}
                  </p>
                </div>
              </div>
              <div className="bg-white border border-agri-200 rounded-xl p-5 shadow-card space-y-4">
                <h3 className="font-heading font-semibold text-slate-800 text-sm">Quick Access Documents</h3>
                <div className="grid grid-cols-1 gap-2.5">
                  <div className="flex items-center justify-between p-2 rounded-lg bg-agri-50 border border-agri-100">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="w-4 h-4 text-indigo-500 shrink-0" />
                      <span className="text-xs font-medium text-slate-700 truncate">Commercial Invoice</span>
                    </div>
                    {latestInvoice ? (
                      <button onClick={() => handleDownload(latestInvoice)} className="p-1.5 rounded-md hover:bg-agri-100 text-forest-700 hover:text-forest-800 transition-colors" title="Download">
                        <Download size={14} />
                      </button>
                    ) : (
                      <span className="text-[10px] font-semibold text-slate-400 bg-gray-100 px-2 py-0.5 rounded-full">Pending</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-agri-50 border border-agri-100">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="w-4 h-4 text-forest-700 shrink-0" />
                      <span className="text-xs font-medium text-slate-700 truncate">Bill of Lading (BL)</span>
                    </div>
                    {latestBL ? (
                      <button onClick={() => handleDownload(latestBL)} className="p-1.5 rounded-md hover:bg-agri-100 text-forest-700 hover:text-forest-800 transition-colors" title="Download">
                        <Download size={14} />
                      </button>
                    ) : (
                      <span className="text-[10px] font-semibold text-slate-400 bg-gray-100 px-2 py-0.5 rounded-full">Pending</span>
                    )}
                  </div>
                </div>
              </div>
            </section>
          )}

          {activeOrder && (
            <section className="animate-slide-up stagger-4">
              <div className="flex items-center justify-between mb-2">
                <h2 className="font-heading font-semibold text-slate-800 text-sm">Approved Documents</h2>
                <span className="text-[11px] text-slate-400 font-body">Only approved customer-visible files</span>
              </div>
              <div className="bg-white rounded-xl border border-agri-200 shadow-card p-4">
                {docsLoading ? (
                  <div className="py-6 text-center flex flex-col items-center justify-center gap-1.5">
                    <Loader2 className="w-5 h-5 animate-spin text-forest-700" />
                    <span className="text-xs text-slate-400 font-body">Loading documents...</span>
                  </div>
                ) : (
                  <DocumentVault documents={documents} onDownload={handleDownload} />
                )}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
