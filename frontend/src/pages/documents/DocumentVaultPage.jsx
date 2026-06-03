import { useState, useEffect } from 'react'
import { Search, FolderOpen, Loader2 } from 'lucide-react'
import DocumentVault from '../../components/documents/DocumentVault'
import { ordersApi, documentsApi } from '../../api'

export default function DocumentVaultPage() {
  const [search, setSearch] = useState('')
  const [ordersWithDocs, setOrdersWithDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let isMounted = true
    async function loadVault() {
      try {
        setLoading(true)
        setError(null)
        const ordersRes = await ordersApi.list({ page: 1, per_page: 100 })
        const ordersList = Array.isArray(ordersRes.data?.data) ? ordersRes.data.data : []
        
        const docsPromises = ordersList.map(async (order) => {
          try {
            const docsRes = await documentsApi.listByOrder(order.id)
            const documents = Array.isArray(docsRes.data?.data) ? docsRes.data.data : []
            return {
              order_code: order.order_code,
              customer_name: order.company_name || order.customer?.company_name || order.customer_name || 'N/A',
              commodity: order.product_name || order.commodity_name || 'N/A',
              documents: documents,
            }
          } catch (err) {
            console.error(`Error loading docs for order ${order.id}:`, err)
            return null
          }
        })
        
        const results = await Promise.all(docsPromises)
        const filteredResults = results.filter((res) => res !== null && res.documents.length > 0)
        
        if (isMounted) {
          setOrdersWithDocs(filteredResults)
        }
      } catch (err) {
        console.error('Error loading document vault:', err)
        if (isMounted) {
          setError('Failed to load document vault.')
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }
    loadVault()
    return () => {
      isMounted = false
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

  const filtered = ordersWithDocs.filter(o => 
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
          disabled={loading}
        />
      </div>

      {/* Orders with Docs */}
      {loading ? (
        <div className="py-24 text-center flex flex-col items-center justify-center gap-2">
          <Loader2 className="w-8 h-8 animate-spin text-saffron-500" />
          <p className="text-sm text-gray-400 font-body">Loading document vault...</p>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center max-w-md mx-auto">
          <p className="text-sm font-medium text-red-800">{error}</p>
        </div>
      ) : filtered.length > 0 ? (
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
                  onDownload={handleDownload}
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
