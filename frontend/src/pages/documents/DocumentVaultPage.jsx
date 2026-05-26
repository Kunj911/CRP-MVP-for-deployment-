import { useState } from 'react'
import { Search, Filter, FolderOpen } from 'lucide-react'
import DocumentVault from '../../components/documents/DocumentVault'

// Demo data
const DEMO_ORDERS_WITH_DOCS = [
  {
    order_code: 'ORD-2025-001',
    customer_name: 'Acme Spices LLC',
    commodity: 'Turmeric Powder',
    documents: [
      { id:1, document_type:'INVOICE',  file_name:'invoice_ORD2025001.pdf', uploaded_at:'2025-05-12T10:00:00Z' },
      { id:2, document_type:'COA',      file_name:'coa_turmeric_lot42.pdf', uploaded_at:'2025-05-13T14:00:00Z' },
    ]
  },
  {
    order_code: 'ORD-2025-002',
    customer_name: 'Spice World GmbH',
    commodity: 'Cumin Seeds',
    documents: [
      { id:3, document_type:'BL_COPY',  file_name:'bl_7749294.pdf', uploaded_at:'2025-05-14T09:30:00Z' },
      { id:4, document_type:'PACKING_LIST', file_name:'packing_list_v2.xlsx', uploaded_at:'2025-05-14T09:45:00Z' },
    ]
  }
]

export default function DocumentVaultPage() {
  const [search, setSearch] = useState('')

  const filtered = DEMO_ORDERS_WITH_DOCS.filter(o => 
    o.order_code.toLowerCase().includes(search.toLowerCase()) ||
    o.customer_name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading font-bold text-xl text-gray-900">Document Vault</h1>
        <p className="text-sm text-gray-500 font-body">Secure access to all shipment documents.</p>
      </div>

      {/* Search */}
      <div className="flex items-center gap-2 bg-white border border-beige-200 rounded-lg px-3 py-2 shadow-card max-w-md">
        <Search size={16} className="text-gray-400 shrink-0" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by order or customer…"
          className="flex-1 text-sm text-gray-700 placeholder-gray-400 outline-none bg-transparent font-body"
        />
      </div>

      {/* Orders with Docs */}
      {filtered.length > 0 ? (
        <div className="space-y-5">
          {filtered.map(order => (
            <div key={order.order_code} className="bg-white rounded-xl border border-beige-200 shadow-card overflow-hidden">
              <div className="px-5 py-4 border-b border-beige-100 bg-beige-50/50 flex justify-between items-center">
                <div>
                  <h2 className="font-heading font-semibold text-gray-900">{order.order_code}</h2>
                  <p className="text-xs text-gray-500 font-body">{order.customer_name} · {order.commodity}</p>
                </div>
                <span className="text-[11px] font-medium text-cardamom-600 bg-cardamom-50 px-2 py-1 rounded-md">
                  {order.documents.length} Files
                </span>
              </div>
              <div className="p-4 bg-white">
                <DocumentVault 
                  documents={order.documents} 
                  onDownload={(doc) => alert(`Secure download initiated for ${doc.file_name}`)}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="py-16 text-center bg-white rounded-xl border border-beige-200 shadow-sm">
          <FolderOpen size={36} className="text-beige-300 mx-auto mb-3" />
          <p className="text-sm text-gray-400 font-body">No documents found matching your search.</p>
        </div>
      )}
    </div>
  )
}
