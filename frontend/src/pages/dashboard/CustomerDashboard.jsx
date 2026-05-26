import OrderCard from '../../components/order/OrderCard'
import MilestoneTimeline from '../../components/milestone/MilestoneTimeline'
import DocumentVault from '../../components/documents/DocumentVault'
import useAuthStore from '../../store/authStore'

const DEMO_ORDER = {
  id: 1, order_code: 'ORD-2025-001', status: 'QA_TESTING',
  commodity_name: 'Turmeric Powder', quantity_kg: 5000,
  destination_country: 'Germany', overall_progress: 44,
  active_stage: 'QA_TESTING', created_at: '2025-05-10',
}

const DEMO_MILESTONES = [
  { id:1, stage_name:'PROCUREMENT',          stage_label:'Procurement',           status:'COMPLETED', completed_at:'2025-05-11T09:00:00Z', completer:{full_name:'Raj Patel'} },
  { id:2, stage_name:'RAW_MATERIAL_VERIFIED',stage_label:'Raw Material Verified',  status:'COMPLETED', completed_at:'2025-05-12T11:30:00Z', completer:{full_name:'Raj Patel'} },
  { id:3, stage_name:'QA_TESTING',           stage_label:'QA Testing',             status:'IN_PROGRESS', completed_at:null },
  { id:4, stage_name:'PACKAGING_STARTED',    stage_label:'Packaging Started',      status:'PENDING' },
  { id:5, stage_name:'PACKAGING_COMPLETED',  stage_label:'Packaging Completed',    status:'PENDING' },
  { id:6, stage_name:'DOCUMENTS_UPLOADED',   stage_label:'Documents Uploaded',     status:'PENDING' },
  { id:7, stage_name:'CONTAINER_LOADING',    stage_label:'Container Loading',      status:'PENDING' },
  { id:8, stage_name:'SHIPMENT_DISPATCHED',  stage_label:'Shipment Dispatched',    status:'PENDING' },
  { id:9, stage_name:'DELIVERED',            stage_label:'Delivered',              status:'PENDING' },
]

const DEMO_DOCS = [
  { id:1, document_type:'INVOICE',  file_name:'invoice_ORD2025001.pdf', uploaded_at:'2025-05-12T10:00:00Z' },
  { id:2, document_type:'COA',      file_name:'coa_turmeric_lot42.pdf', uploaded_at:'2025-05-13T14:00:00Z' },
]

export default function CustomerDashboard() {
  const user = useAuthStore((s) => s.user)

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Greeting */}
      <div>
        <h1 className="font-heading font-bold text-2xl text-gray-900">
          Hello, {user?.full_name?.split(' ')[0]} 👋
        </h1>
        <p className="text-sm text-gray-500 font-body mt-0.5">Track your active spice shipments.</p>
      </div>

      {/* Active order card */}
      <section>
        <h2 className="font-heading font-semibold text-gray-800 text-sm mb-2">Your Active Order</h2>
        <OrderCard order={DEMO_ORDER} />
      </section>

      {/* Timeline section */}
      <section className="bg-white rounded-xl border border-beige-200 shadow-card overflow-hidden">
        <div className="px-5 py-4 border-b border-beige-100">
          <h2 className="font-heading font-semibold text-gray-900">Shipment Timeline</h2>
          <p className="text-xs text-gray-400 font-body mt-0.5">ORD-2025-001 · 44% complete</p>
        </div>

        {/* Progress bar */}
        <div className="px-5 pt-4 pb-2">
          <div className="w-full bg-beige-100 rounded-full h-2">
            <div className="h-full bg-saffron-500 rounded-full" style={{ width: '44%' }} />
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-[11px] text-gray-400">QA Testing in progress</span>
            <span className="text-[11px] font-medium text-saffron-600">44%</span>
          </div>
        </div>

        <div className="px-5 pb-5 pt-3">
          <MilestoneTimeline milestones={DEMO_MILESTONES} />
        </div>
      </section>

      {/* Document vault */}
      <section>
        <h2 className="font-heading font-semibold text-gray-800 text-sm mb-2">Document Vault</h2>
        <div className="bg-white rounded-xl border border-beige-200 shadow-card p-4">
          <DocumentVault
            documents={DEMO_DOCS}
            onDownload={(doc) => alert(`Download: ${doc.file_name}`)}
          />
        </div>
      </section>
    </div>
  )
}
