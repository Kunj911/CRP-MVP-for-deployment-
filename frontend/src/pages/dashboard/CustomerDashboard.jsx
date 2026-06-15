import { useEffect, useState } from 'react'
import { Loader2, FileText, Download, FileCheck, Sprout } from 'lucide-react'
import OrderCard from '../../components/order/OrderCard'
import MilestoneTimeline from '../../components/milestone/MilestoneTimeline'
import DocumentVault from '../../components/documents/DocumentVault'
import useAuthStore from '../../store/authStore'
import { ordersApi, documentsApi, uploadsApi } from '../../api'

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
    customer_name: order.customer_name || order.company_name,
    commodity_name: order.commodity_name || order.product_name,
    quantity_kg: order.quantity_kg ?? Number(order.quantity || 0),
    destination_country: order.destination_country,
    overall_progress: order.overall_progress ?? STATUS_PROGRESS[status] ?? 0,
    active_stage: order.active_stage || (status === 'DELIVERED' ? null : status),
    created_at: order.created_at,
  }
}

export default function CustomerDashboard() {
  const user = useAuthStore((s) => s.user)
  const [activeOrder, setActiveOrder] = useState(null)
  const [milestones, setMilestones] = useState([])
  const [documents, setDocuments] = useState([])
  const [checklist, setChecklist] = useState([])
  const [loading, setLoading] = useState(true)
  const [timelineLoading, setTimelineLoading] = useState(false)
  const [docsLoading, setDocsLoading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

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
        
        const [timelineRes, docsRes, checklistRes] = await Promise.all([
          ordersApi.getTimeline(nextActiveOrder.id),
          documentsApi.listByOrder(nextActiveOrder.id),
          uploadsApi.getDocumentChecklist(nextActiveOrder.id)
        ])
        
        setMilestones(timelineRes.data?.data?.milestones || [])
        setDocuments(Array.isArray(docsRes.data?.data) ? docsRes.data.data : [])
        setChecklist(Array.isArray(checklistRes.data?.data) ? checklistRes.data.data : [])
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
    const intervalId = window.setInterval(() => fetchDashboardStats(false), 15000)

    return () => {
      window.clearInterval(intervalId)
    }
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

  const requiredChecklist = checklist.filter(c => c.required)
  const requiredCount = requiredChecklist.length
  const approvedRequiredCount = requiredChecklist.filter(c => c.approved).length
  const docProgressPercent = requiredCount > 0 ? Math.round((approvedRequiredCount / requiredCount) * 100) : 0

  const latestInvoice = documents.find(d => d.document_type === 'invoice')
  const latestBL = documents.find(d => d.document_type === 'bill_of_lading')

  if (loading && !activeOrder) {
    return (
      <div className="py-24 text-center flex flex-col items-center justify-center gap-2">
        <Loader2 className="w-8 h-8 animate-spin text-forest-700" />
        <p className="text-sm text-slate-400 font-body">Loading your dashboard...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-forest-700 to-forest-900 p-6 md:p-8">
        <div className="absolute inset-0 opacity-10" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='80' height='80' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M40 5L75 40L40 75L5 40Z' fill='none' stroke='white' stroke-width='1'/%3E%3C/svg%3E")`,
          backgroundSize: '80px 80px',
        }} />
        <div className="relative z-10">
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-white">
            Hello, {user?.full_name?.split(' ')[0]}
          </h1>
          <p className="text-forest-200 text-sm font-body mt-1">
            {isRefreshing ? 'Refreshing your shipments...' : 'Track your agricultural shipments in real time.'}
          </p>
        </div>
      </div>

      {/* Active order card */}
      <section className="animate-slide-up stagger-1">
        <h2 className="font-heading font-semibold text-slate-800 text-sm mb-2">Your Active Order</h2>
        {activeOrder ? (
          <OrderCard order={activeOrder} />
        ) : (
          <div className="bg-white rounded-xl border border-agri-200 shadow-card p-5">
            <p className="text-sm text-slate-500 font-body">No active orders found.</p>
          </div>
        )}
      </section>

      {/* Timeline section */}
      {activeOrder && (
        <section className="bg-white rounded-xl border border-agri-200 shadow-card overflow-hidden animate-slide-up stagger-2">
          <div className="px-5 py-4 border-b border-agri-100">
            <h2 className="font-heading font-semibold text-slate-900">Shipment Timeline</h2>
            <p className="text-xs text-slate-400 font-body mt-0.5">
              {activeOrder.order_code} · {activeOrder.overall_progress}% complete
            </p>
          </div>

          <div className="px-5 pt-4 pb-2">
            <div className="w-full bg-agri-100 rounded-full h-2">
              <div className="h-full bg-forest-700 rounded-full" style={{ width: `${activeOrder.overall_progress}%` }} />
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
              <MilestoneTimeline milestones={milestones} />
            )}
          </div>
        </section>
      )}

      {/* Documentation Progress & Quick Access Widgets */}
      {activeOrder && checklist.length > 0 && (
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white border border-agri-200 rounded-xl p-5 shadow-card space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-heading font-semibold text-slate-800 text-sm">Documentation Progress</h3>
              <FileCheck className="w-5 h-5 text-forest-700" />
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
                  <button
                    onClick={() => handleDownload(latestInvoice)}
                    className="p-1.5 rounded-md hover:bg-agri-100 text-forest-700 hover:text-forest-800 transition-colors"
                    title="Download"
                  >
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
                  <button
                    onClick={() => handleDownload(latestBL)}
                    className="p-1.5 rounded-md hover:bg-agri-100 text-forest-700 hover:text-forest-800 transition-colors"
                    title="Download"
                  >
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

      {/* Document vault */}
      {activeOrder && (
        <section>
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
              <DocumentVault
                documents={documents}
                onDownload={handleDownload}
              />
            )}
          </div>
        </section>
      )}
    </div>
  )
}
