import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Upload, Package } from 'lucide-react'
import MilestoneTimeline from '../../components/milestone/MilestoneTimeline'
import DocumentVault from '../../components/documents/DocumentVault'
import UploadModal from '../../components/upload/UploadModal'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import useAuthStore from '../../store/authStore'

// Demo data
const DEMO_ORDER = { id: 1, order_code: 'ORD-2025-001', status: 'QA_TESTING', commodity_name: 'Turmeric Powder', quantity_kg: 5000, destination_country: 'Germany', customer_name: 'Acme Spices LLC', overall_progress: 44, created_at: '2025-05-10' }
const DEMO_MILESTONES = [
  { id:1, stage_name:'PROCUREMENT',           stage_label:'Procurement',           status:'COMPLETED', completed_at:'2025-05-11T09:00:00Z', completer:{full_name:'Raj Patel'} },
  { id:2, stage_name:'RAW_MATERIAL_VERIFIED', stage_label:'Raw Material Verified', status:'COMPLETED', completed_at:'2025-05-12T11:30:00Z', completer:{full_name:'Raj Patel'} },
  { id:3, stage_name:'QA_TESTING',            stage_label:'QA Testing',            status:'IN_PROGRESS' },
  { id:4, stage_name:'PACKAGING_STARTED',     stage_label:'Packaging Started',     status:'PENDING' },
  { id:5, stage_name:'PACKAGING_COMPLETED',   stage_label:'Packaging Completed',   status:'PENDING' },
  { id:6, stage_name:'DOCUMENTS_UPLOADED',    stage_label:'Documents Uploaded',    status:'PENDING' },
  { id:7, stage_name:'CONTAINER_LOADING',     stage_label:'Container Loading',     status:'PENDING' },
  { id:8, stage_name:'SHIPMENT_DISPATCHED',   stage_label:'Shipment Dispatched',   status:'PENDING' },
  { id:9, stage_name:'DELIVERED',             stage_label:'Delivered',             status:'PENDING' },
]
const DEMO_PHOTOS = [
  { id:1, url:'https://images.unsplash.com/photo-1615485290382-441e4d049cb5?w=400', label:'Procurement' },
  { id:2, url:'https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=400', label:'QA Testing' },
  { id:3, url:'https://images.unsplash.com/photo-1567892737950-30c4db37cd89?w=400', label:'Packaging' },
  { id:4, url:'https://images.unsplash.com/photo-1611288875785-5d403c52b9ef?w=400', label:'Loading' },
]
const DEMO_DOCS = [
  { id:1, document_type:'INVOICE',  file_name:'invoice_ORD2025001.pdf', uploaded_at:'2025-05-12T10:00:00Z' },
  { id:2, document_type:'COA',      file_name:'coa_turmeric_lot42.pdf', uploaded_at:'2025-05-13T14:00:00Z' },
]

const TABS = ['Timeline', 'Photos', 'Documents', 'QA Reports']

export default function OrderDetailPage() {
  const { orderId } = useParams()
  const navigate = useNavigate()
  const isStaff = useAuthStore((s) => s.isStaff())
  const [activeTab, setActiveTab] = useState('Timeline')
  const [uploadOpen, setUploadOpen] = useState(false)

  const order = DEMO_ORDER  // Replace with: useOrder(orderId)

  return (
    <div className="max-w-3xl space-y-4">
      {/* Back + header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
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
              {order.commodity_name} · {order.quantity_kg?.toLocaleString()} kg → {order.destination_country}
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
            <MilestoneTimeline milestones={DEMO_MILESTONES} />
          )}

          {activeTab === 'Photos' && (
            <div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {DEMO_PHOTOS.map((photo) => (
                  <div key={photo.id} className="relative group rounded-xl overflow-hidden aspect-square bg-beige-100">
                    <img src={photo.url} alt={photo.label} className="w-full h-full object-cover" />
                    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-2 py-1.5">
                      <p className="text-[11px] text-white font-body">{photo.label}</p>
                    </div>
                  </div>
                ))}
              </div>
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
            <DocumentVault
              documents={DEMO_DOCS}
              onDownload={(doc) => alert(`Downloading ${doc.file_name}…`)}
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
      />
    </div>
  )
}
