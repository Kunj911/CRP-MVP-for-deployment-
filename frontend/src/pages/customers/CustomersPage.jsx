import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, ChevronRight, ChevronDown, Loader2, AlertCircle, Users, Package } from 'lucide-react'
import Badge from '../../components/ui/Badge'
import { customersApi } from '../../api'

export default function CustomersPage() {
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    let isMounted = true
    async function loadCustomers() {
      try {
        setLoading(true)
        setError(null)
        const res = await customersApi.getActive()
        const data = Array.isArray(res.data) ? res.data : []
        if (isMounted) setCustomers(data)
      } catch (err) {
        console.error('Error fetching active customers:', err)
        if (isMounted) setError('Failed to load customers. Please try again.')
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    loadCustomers()
    return () => { isMounted = false }
  }, [])

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return customers.filter((c) =>
      c.company_name?.toLowerCase().includes(q) ||
      c.contact_person?.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q) ||
      c.phone?.toLowerCase().includes(q)
    )
  }, [customers, search])

  const toggleExpand = (id) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="space-y-5 max-w-6xl">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading font-bold text-xl text-slate-900">Customers</h1>
          <p className="text-sm text-slate-500 font-body">
            {loading ? 'Loading...' : `${customers.length} customers`}
          </p>
        </div>
      </div>

      {/* Search bar */}
      <div className="flex items-center gap-2 bg-white border border-agri-200 rounded-lg px-3 py-2 shadow-card max-w-md">
        <Search size={15} className="text-slate-400 shrink-0" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by company, contact, email, phone…"
          className="flex-1 text-sm text-slate-700 placeholder-slate-400 outline-none bg-transparent font-body"
          disabled={loading}
        />
      </div>

      {/* Main Content */}
      {loading ? (
        <div className="py-24 text-center flex flex-col items-center justify-center gap-2">
          <Loader2 className="w-8 h-8 animate-spin text-forest-700" />
          <p className="text-sm text-slate-400 font-body">Loading customers...</p>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center max-w-md mx-auto space-y-3">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto" />
          <p className="text-sm font-medium text-red-800">{error}</p>
        </div>
      ) : filtered.length ? (
        <div className="bg-white border border-agri-200 rounded-xl shadow-card overflow-hidden">
          {/* Table header */}
          <div className="hidden md:grid grid-cols-12 gap-3 px-5 py-3 bg-agri-50 border-b border-agri-200 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            <div className="col-span-1"></div>
            <div className="col-span-2">Company</div>
            <div className="col-span-2">Contact</div>
            <div className="col-span-2">Email</div>
            <div className="col-span-2">Phone</div>
            <div className="col-span-1">Country</div>
            <div className="col-span-2 text-right">Active Orders</div>
          </div>

          {/* Table rows */}
          {filtered.map((c) => {
            const isExpanded = expandedId === c.id
            return (
              <div key={c.id}>
                {/* Customer row */}
                <div
                  onClick={() => toggleExpand(c.id)}
                  className="grid grid-cols-12 gap-3 px-5 py-3.5 items-center border-b border-agri-100 hover:bg-agri-50/50 cursor-pointer transition-colors last:border-b-0"
                >
                  <div className="col-span-1 text-slate-400">
                    {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm font-medium text-slate-900 truncate">{c.company_name}</p>
                  </div>
                  <div className="col-span-2 text-sm text-slate-600 truncate">
                    {c.contact_person || '-'}
                  </div>
                  <div className="col-span-2 text-sm text-slate-600 truncate">
                    {c.login_email || c.email || '-'}
                  </div>
                  <div className="col-span-2 text-sm text-slate-600 truncate">
                    {c.phone || '-'}
                  </div>
                  <div className="col-span-1 text-sm text-slate-600 truncate">
                    {c.country || '-'}
                  </div>
                  <div className="col-span-2 text-right">
                    <span className={`inline-flex items-center justify-center min-w-[28px] h-7 px-2 rounded-full text-xs font-semibold ${
                      c.active_orders_count > 0
                        ? 'bg-forest-100 text-forest-700'
                        : 'bg-gray-100 text-gray-500'
                    }`}>
                      {c.active_orders_count}
                    </span>
                  </div>
                </div>

                {/* Expanded row — active orders */}
                {isExpanded && (
                  <div className="bg-agri-50/70 border-b border-agri-200 px-5 py-4">
                    {c.active_orders?.length > 0 ? (
                      <div>
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                          <Package size={13} />
                          Active Orders
                        </p>
                        <div className="hidden md:grid grid-cols-12 gap-3 px-3 py-2 bg-white rounded-lg border border-agri-200 text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
                          <div className="col-span-3">Order Code</div>
                          <div className="col-span-3">Product</div>
                          <div className="col-span-2">Quantity</div>
                          <div className="col-span-2">Status</div>
                          <div className="col-span-2"></div>
                        </div>
                        {c.active_orders.map((o) => (
                          <div
                            key={o.id}
                            className="grid grid-cols-12 gap-3 px-3 py-2.5 items-center bg-white border-b border-agri-100 last:border-b-0 rounded-sm text-sm"
                          >
                            <div className="col-span-3">
                              <button
                                onClick={(e) => { e.stopPropagation(); navigate(`/orders/${o.id}`) }}
                                className="text-forest-700 hover:text-forest-800 hover:underline font-mono text-xs font-medium"
                              >
                                {o.order_code}
                              </button>
                            </div>
                            <div className="col-span-3 text-slate-700 truncate text-xs">
                              {o.product_name}
                            </div>
                            <div className="col-span-2 text-slate-600 text-xs">
                              {o.quantity != null ? `${o.quantity} ${o.unit || ''}` : '-'}
                            </div>
                            <div className="col-span-2">
                              <Badge status={o.shipment_status} />
                            </div>
                            <div className="col-span-2 text-right">
                              <button
                                onClick={(e) => { e.stopPropagation(); navigate(`/orders/${o.id}`) }}
                                className="text-[11px] text-forest-600 hover:text-forest-800 font-medium"
                              >
                                View →
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 text-sm text-slate-400 py-2">
                        <Package size={14} />
                        No active orders
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="py-16 text-center">
          <Users size={36} className="text-agri-300 mx-auto mb-3" />
          <p className="text-sm text-slate-400 font-body">No customers match your search.</p>
        </div>
      )}
    </div>
  )
}