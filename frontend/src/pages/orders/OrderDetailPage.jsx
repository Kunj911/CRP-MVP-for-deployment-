import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Upload, Loader2, AlertCircle, Trash2, Edit3 } from 'lucide-react'
import MilestoneTimeline from '../../components/milestone/MilestoneTimeline'
import DocumentChecklist from '../../components/documents/DocumentChecklist'
import UploadModal from '../../components/upload/UploadModal'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import useAuthStore from '../../store/authStore'
import { ordersApi, uploadsApi, documentsApi } from '../../api'

const TABS = ['Timeline', 'Photos', 'Documents']

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
  const [editOpen, setEditOpen] = useState(false)
  const [editForm, setEditForm] = useState({ product_name: '', quantity: '', unit: '', notes: '' })
  const [saving, setSaving] = useState(false)

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
        product_name: rawOrder.product_name || rawOrder.commodity_name || '',
        quantity: rawOrder.quantity || 0,
        unit: rawOrder.unit || 'KG',
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

  const handleDeleteMedia = async (photoId) => {
    if (!confirm('Delete this photo? This action cannot be undone.')) return
    try {
      await uploadsApi.deleteMedia(photoId)
      setPhotos((prev) => prev.filter((p) => p.id !== photoId))
    } catch (err) {
      console.error('Delete photo failed:', err)
      alert(err.response?.data?.error?.message || 'Failed to delete photo.')
    }
  }

  const handleOpenEdit = () => {
    setEditForm({
      product_name: order.product_name || '',
      quantity: order.quantity || '',
      unit: order.unit || 'KG',
      notes: order.notes || '',
    })
    setEditOpen(true)
  }

  const handleEditSave = async () => {
    setSaving(true)
    try {
      await ordersApi.update(orderId, {
        product_name: editForm.product_name,
        quantity: Number(editForm.quantity),
        unit: editForm.unit,
        notes: editForm.notes,
      })
      setEditOpen(false)
      await loadData()
    } catch (err) {
      console.error('Update failed:', err)
      alert(err.response?.data?.error?.message || 'Failed to update order.')
    } finally {
      setSaving(false)
    }
  }

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
        <Loader2 className="w-8 h-8 animate-spin text-forest-700" />
        <p className="text-sm text-slate-400 font-body">Loading shipment details...</p>
      </div>
    )
  }

  if (error || !order) {
    return (
      <div className="max-w-md mx-auto py-16 text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
        <h2 className="font-heading font-semibold text-lg text-slate-900">Access Denied or Not Found</h2>
        <p className="text-sm text-slate-500 font-body">{error || 'This order does not exist.'}</p>
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
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-agri-100 text-slate-500 transition-colors shrink-0"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="font-heading font-bold text-xl text-slate-900">{order.order_code}</h1>
              <Badge status={order.status} size="md" />
            </div>
            <p className="text-sm text-slate-500 font-body">
              {order.product_name} · {Number(order.quantity).toLocaleString()} {order.unit}
              {order.destination_country ? ` → ${order.destination_country}` : ''}
            </p>
          </div>
        </div>
        {isStaff && (
          <div className="flex gap-2">
            <Button icon={Edit3} size="sm" variant="outline" onClick={handleOpenEdit}>
              Edit
            </Button>
            <Button icon={Upload} size="sm" onClick={() => setUploadOpen(true)}>
              Upload
            </Button>
          </div>
        )}
      </div>

      {/* Progress strip */}
      <div className="bg-white rounded-xl border border-agri-200 px-4 py-3 flex items-center gap-4 shadow-card">
        <div className="flex-1">
          <div className="flex justify-between mb-1">
            <span className="text-[11px] text-slate-500 font-body">Overall Progress</span>
            <span className="text-[11px] font-semibold text-forest-700">{order.overall_progress}%</span>
          </div>
          <div className="w-full bg-agri-100 rounded-full h-2">
            <div className="h-full bg-forest-700 rounded-full" style={{ width: `${order.overall_progress}%` }} />
          </div>
        </div>
        <div className="text-right shrink-0">
          <p className="text-[11px] text-slate-400 font-body">Customer</p>
          <p className="text-sm font-medium text-slate-800 font-heading">{order.customer_name}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-agri-200 shadow-card overflow-hidden">
        <div className="flex border-b border-agri-100 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2 -mb-px ${
                activeTab === tab
                  ? 'border-forest-700 text-forest-800'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
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
                    <div key={photo.id} className="relative group rounded-xl overflow-hidden aspect-square bg-agri-100">
                      <img src={photo.url} alt={photo.label} className="w-full h-full object-cover" />
                      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-2 py-1.5">
                        <p className="text-[11px] text-white font-body">{photo.label}</p>
                      </div>
                      {isStaff && (
                        <button
                          onClick={() => handleDeleteMedia(photo.id)}
                          className="absolute top-1.5 right-1.5 w-7 h-7 rounded-lg bg-black/50 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600/80"
                          title="Delete photo"
                        >
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400 py-6 text-center font-body">
                  No photos uploaded yet for this order.
                </p>
              )}
              {isStaff && (
                <button
                  onClick={() => setUploadOpen(true)}
                  className="mt-3 w-full border-2 border-dashed border-agri-300 rounded-xl py-4 text-sm text-slate-500 hover:border-forest-500 hover:text-forest-700 transition-colors flex items-center justify-center gap-2"
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

      {/* Edit Order Modal */}
      {editOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setEditOpen(false)} />
          <div className="relative bg-white rounded-xl p-5 w-full max-w-md mx-4 shadow-xl space-y-4">
            <h3 className="font-heading font-semibold text-slate-900 text-base">Edit Order</h3>
            <p className="text-xs text-slate-400 font-body -mt-2">{order.order_code}</p>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Product Name</label>
                <input
                  type="text"
                  value={editForm.product_name}
                  onChange={(e) => setEditForm({ ...editForm, product_name: e.target.value })}
                  className="w-full px-3 py-2 border border-agri-300 rounded-lg text-sm focus:outline-none focus:border-forest-500"
                />
              </div>
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-slate-600 mb-1">Quantity</label>
                  <input
                    type="number"
                    value={editForm.quantity}
                    onChange={(e) => setEditForm({ ...editForm, quantity: e.target.value })}
                    className="w-full px-3 py-2 border border-agri-300 rounded-lg text-sm focus:outline-none focus:border-forest-500"
                  />
                </div>
                <div className="w-24">
                  <label className="block text-xs font-medium text-slate-600 mb-1">Unit</label>
                  <input
                    type="text"
                    value={editForm.unit}
                    onChange={(e) => setEditForm({ ...editForm, unit: e.target.value })}
                    className="w-full px-3 py-2 border border-agri-300 rounded-lg text-sm focus:outline-none focus:border-forest-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Notes</label>
                <textarea
                  rows={3}
                  value={editForm.notes}
                  onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                  className="w-full px-3 py-2 border border-agri-300 rounded-lg text-sm focus:outline-none focus:border-forest-500 font-body resize-none"
                />
              </div>
            </div>

            <div className="flex gap-2.5 pt-1">
              <Button variant="outline" className="flex-1" onClick={() => setEditOpen(false)} disabled={saving}>
                Cancel
              </Button>
              <Button className="flex-1" loading={saving} onClick={handleEditSave}>
                Save
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
