import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Upload, Package, Loader2, AlertCircle } from 'lucide-react'
import MilestoneTimeline from '../../components/milestone/MilestoneTimeline'
import DocumentChecklist from '../../components/documents/DocumentChecklist'
import UploadModal from '../../components/upload/UploadModal'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import useAuthStore from '../../store/authStore'
import { ordersApi, uploadsApi, documentsApi } from '../../api'

const TABS = ['Timeline', 'Photos', 'Documents', 'QA Reports']

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

export default function OrderDetailPage() {
  const { orderId } = useParams()
  const navigate = useNavigate()
  const isStaff = useAuthStore((s) => s.isStaff())
  const [activeTab, setActiveTab] = useState('Timeline')
  const [uploadOpen, setUploadOpen] = useState(false)

  const [order, setOrder] = useState(null)
  const [milestones, setMilestones] = useState([])
  const [photos, setPhotos] = useState([])
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = async () => {
    try {
      setError(null)
      
      // Fetch order details
      const orderRes = await ordersApi.getById(orderId)
      const rawOrder = orderRes.data?.data
      if (!rawOrder) {
        throw new Error('Order not found')
      }

      // Fetch timeline (milestones + progress)
      const timelineRes = await ordersApi.getTimeline(orderId)
      const timeline = timelineRes.data?.data

      // Fetch photos
      const photosRes = await uploadsApi.listMediaByOrder(orderId)
      const rawPhotos = Array.isArray(photosRes.data?.data) ? photosRes.data.data : []

      // Fetch documents
      const docsRes = await documentsApi.listByOrder(orderId)
      const rawDocs = Array.isArray(docsRes.data?.data) ? docsRes.data.data : []

      // Normalize order details
      const status = rawOrder.shipment_status || rawOrder.status
      setOrder({
        id: rawOrder.id,
        order_code: rawOrder.order_code,
        status: status,
        commodity_name: rawOrder.product_name || rawOrder.commodity_name,
        quantity_kg: Number(rawOrder.quantity || 0),
        destination_country: rawOrder.customer?.country,
        overall_progress: timeline?.overall_progress ?? STATUS_PROGRESS[status] ?? 0,
        customer_name: rawOrder.customer?.company_name,
        created_at: rawOrder.created_at,
      })

      // Set milestones
      setMilestones(timeline?.milestones || [])

      // Set photos
      setPhotos(
        rawPhotos.map((p) => ({
          id: p.id,
          url: p.file_url,
          label: p.media_type?.replace(/_/g, ' ') || 'Photo',
        }))
      )

      // Set documents
      setDocuments(rawDocs)
    } catch (err) {
      console.error('Error fetching order details:', err)
      const status = err.response?.status
      if (status === 404) {
        setError('Order not found or access denied.')
      } else {
        setError('Failed to load order details. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setLoading(true)
    loadData()
  }, [orderId])

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

  if (loading) {
    return (
      <div className="py-32 text-center flex flex-col items-center justify-center gap-2">
        <Loader2 className="w-8 h-8 animate-spin text-saffron-500" />
        <p className="text-sm text-gray-400 font-body">Loading shipment details...</p>
      </div>
    )
  }

  if (error || !order) {
    return (
      <div className="max-w-md mx-auto py-16 text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
        <h2 className="font-heading font-semibold text-lg text-gray-900">Access Denied or Not Found</h2>
        <p className="text-sm text-gray-500 font-body">{error || 'This order does not exist.'}</p>
        <Button onClick={() => navigate('/orders')}>Back to Orders</Button>
      </div>
    )
  }

  return (
    <div className="max-w-3xl space-y-4">
      {/* Back + header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/orders')}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-beige-200 text-gray-500 transition-colors shrink-0"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="font-heading font-bold text-xl text-gray-900">{order.order_code}</h1>
              <Badge status={order.status} size="md" />
            </div>
            <p className="text-sm text-gray-500 font-body">
              {order.commodity_name} · {order.quantity_kg?.toLocaleString()} kg
              {order.destination_country ? ` → ${order.destination_country}` : ''}
            </p>
          </div>
        </div>
        {isStaff && (
          <Button icon={Upload} size="sm" onClick={() => setUploadOpen(true)}>
            Upload
          </Button>
        )}
      </div>

      {/* Progress strip */}
      <div className="bg-white rounded-xl border border-beige-200 px-4 py-3 flex items-center gap-4 shadow-card">
        <div className="flex-1">
          <div className="flex justify-between mb-1">
            <span className="text-[11px] text-gray-500 font-body">Overall Progress</span>
            <span className="text-[11px] font-semibold text-saffron-600">{order.overall_progress}%</span>
          </div>
          <div className="w-full bg-beige-100 rounded-full h-2">
            <div className="h-full bg-saffron-500 rounded-full" style={{ width: `${order.overall_progress}%` }} />
          </div>
        </div>
        <div className="text-right shrink-0">
          <p className="text-[11px] text-gray-400 font-body">Customer</p>
          <p className="text-sm font-medium text-gray-800 font-heading">{order.customer_name}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-beige-200 shadow-card overflow-hidden">
        {/* Tab bar */}
        <div className="flex border-b border-beige-100 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2 -mb-px ${
                activeTab === tab
                  ? 'border-saffron-500 text-saffron-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="p-5">
          {activeTab === 'Timeline' && (
            <MilestoneTimeline milestones={milestones} />
          )}

          {activeTab === 'Photos' && (
            <div>
              {photos.length ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                  {photos.map((photo) => (
                    <div key={photo.id} className="relative group rounded-xl overflow-hidden aspect-square bg-beige-100">
                      <img src={photo.url} alt={photo.label} className="w-full h-full object-cover" />
                      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-2 py-1.5">
                        <p className="text-[11px] text-white font-body">{photo.label}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400 py-6 text-center font-body">
                  No photos uploaded yet for this order.
                </p>
              )}
              {isStaff && (
                <button
                  onClick={() => setUploadOpen(true)}
                  className="mt-3 w-full border-2 border-dashed border-beige-300 rounded-xl py-4 text-sm text-gray-500 hover:border-saffron-400 hover:text-saffron-600 transition-colors flex items-center justify-center gap-2"
                >
                  <Upload size={16} /> Add Photos
                </button>
              )}
            </div>
          )}

          {activeTab === 'Documents' && (
            <DocumentChecklist
              orderId={order.id}
              orderCode={order.order_code}
              onTimelineUpdate={loadData}
            />
          )}

          {activeTab === 'QA Reports' && (
            <div className="py-8 text-center">
              <Package size={36} className="text-beige-300 mx-auto mb-3" />
              <p className="text-sm text-gray-400 font-body">No QA reports yet for this order.</p>
            </div>
          )}
        </div>
      </div>

      {/* Upload modal */}
      <UploadModal
        isOpen={uploadOpen}
        onClose={() => setUploadOpen(false)}
        orderId={order.id}
        orderCode={order.order_code}
        onSuccess={loadData}
      />
    </div>
  )
}
