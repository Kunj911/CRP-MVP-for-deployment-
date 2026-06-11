import { useEffect, useState } from 'react'
import { Search, Upload, Image, FileText, CheckCircle2, Loader2 } from 'lucide-react'
import Button from '../../components/ui/Button'
import { ordersApi, uploadsApi } from '../../api'
import useAuthStore from '../../store/authStore'

const PHOTO_CATS = [
  { value: 'PROCUREMENT_IMAGE', label: '🌾 Procurement', hint: 'Raw material sourcing' },
  { value: 'PACKAGING_IMAGE',   label: '📦 Packaging',   hint: 'Packaging process'    },
  { value: 'QA_IMAGE',          label: '🧪 QA Testing',  hint: 'Quality checks'       },
  { value: 'LOADING_IMAGE',     label: '🚢 Loading',     hint: 'Container loading'    },
]

export default function UploadPage() {
  const role = useAuthStore((s) => s.user?.role)
  const isWarehouse = role === 'WAREHOUSE'
  const isDocs = role === 'DOCUMENTATION'
  const TABS = [
    ...(!isDocs ? [{ key: 'photo', label: '📷 Photo' }] : []),
    ...(!isWarehouse ? [{ key: 'document', label: '📄 Document' }] : []),
  ]
  const [step, setStep] = useState(1)     // 1: select order, 2: select type, 3: upload
  const [uploadTab, setUploadTab] = useState('photo')
  const [orders, setOrders] = useState([])
  const [ordersLoading, setOrdersLoading] = useState(true)
  const [selectedOrder, setSelectedOrder] = useState(null)
  const [selectedCat, setSelectedCat] = useState(null)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [done, setDone] = useState(false)
  const [search, setSearch] = useState('')

  useEffect(() => {
    let isMounted = true
    async function loadOrders() {
      try {
        setOrdersLoading(true)
        const res = await ordersApi.list({ page: 1, per_page: 100 })
        const data = Array.isArray(res.data?.data) ? res.data.data : []
        if (isMounted) {
          // Filter to active orders only
          setOrders(data.filter((o) => !['DELIVERED', 'CANCELLED'].includes(o.shipment_status || o.status)))
        }
      } catch (err) {
        console.error('Error fetching orders for upload:', err)
      } finally {
        if (isMounted) {
          setOrdersLoading(false)
        }
      }
    }
    loadOrders()
    return () => {
      isMounted = false
    }
  }, [])

  const filtered = orders.filter(
    (o) =>
      o.order_code.toUpperCase().includes(search.toUpperCase()) ||
      (o.product_name || o.commodity_name || '').toLowerCase().includes(search.toLowerCase())
  )

  function handleFile(e) {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    if (f.type.startsWith('image/')) setPreview(URL.createObjectURL(f))
  }

  async function handleUpload() {
    if (!file || !selectedOrder || !selectedCat) return
    setUploading(true)
    try {
      if (uploadTab === 'photo') {
        await uploadsApi.uploadPhoto(file, selectedOrder.id, selectedCat)
      } else {
        await uploadsApi.uploadDocument(file, selectedOrder.id, selectedCat)
      }
      setDone(true)
    } catch (err) {
      console.error('Upload failed:', err)
      alert(err.response?.data?.error?.message || 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  function reset() {
    setStep(1)
    setSelectedOrder(null)
    setSelectedCat(null)
    setFile(null)
    setPreview(null)
    setDone(false)
    setSearch('')
  }

  return (
    <div className="max-w-lg mx-auto space-y-5">
      <div>
        <h1 className="font-heading font-bold text-xl text-gray-900">Upload</h1>
        <p className="text-sm text-gray-500 font-body">Attach photos and documents to an order.</p>
      </div>

      {/* Step indicator */}
      {!done && (
        <div className="flex items-center gap-2">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                  step > s
                    ? 'bg-cardamom-500 text-white'
                    : step === s
                    ? 'bg-saffron-500 text-white'
                    : 'bg-beige-200 text-gray-400'
                }`}
              >
                {step > s ? <CheckCircle2 size={14} /> : s}
              </div>
              {s < 3 && <div className={`flex-1 h-0.5 w-10 ${step > s ? 'bg-cardamom-400' : 'bg-beige-200'}`} />}
            </div>
          ))}
          <p className="text-xs text-gray-500 ml-2 font-body">
            {step === 1 ? 'Select Order' : step === 2 ? 'Choose Type' : 'Upload File'}
          </p>
        </div>
      )}

      {/* DONE */}
      {done && (
        <div className="bg-white border border-beige-200 rounded-xl p-8 flex flex-col items-center gap-3 shadow-card text-center">
          <div className="w-16 h-16 rounded-full bg-cardamom-50 flex items-center justify-center">
            <CheckCircle2 size={36} className="text-cardamom-500" />
          </div>
          <p className="font-heading font-semibold text-gray-900 text-lg">Upload Complete!</p>
          <p className="text-sm text-gray-500 font-body">
            File saved to <strong>{selectedOrder?.order_code}</strong>.
          </p>
          <div className="flex gap-3 w-full mt-2">
            <Button variant="outline" className="flex-1" onClick={reset}>
              Upload Another
            </Button>
            <Button className="flex-1" onClick={() => (window.location.href = `/orders/${selectedOrder?.id}`)}>
              View Order
            </Button>
          </div>
        </div>
      )}

      {/* STEP 1: Order selection */}
      {!done && step === 1 && (
        <div className="bg-white rounded-xl border border-beige-200 shadow-card overflow-hidden">
          <div className="p-4 border-b border-beige-100">
            <div className="flex items-center gap-2 bg-beige-100 rounded-lg px-3 py-2">
              <Search size={14} className="text-gray-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search order…"
                className="bg-transparent text-sm outline-none flex-1 font-body text-gray-700 placeholder-gray-400"
              />
            </div>
          </div>
          {ordersLoading ? (
            <div className="py-12 text-center flex flex-col items-center justify-center gap-2">
              <Loader2 className="w-6 h-6 animate-spin text-saffron-500" />
              <p className="text-xs text-gray-400 font-body">Loading active orders...</p>
            </div>
          ) : (
            <div className="divide-y divide-beige-100 max-h-96 overflow-y-auto">
              {filtered.length ? (
                filtered.map((o) => (
                  <button
                    key={o.id}
                    onClick={() => {
                      setSelectedOrder(o)
                      setStep(2)
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-beige-50 text-left transition-colors"
                  >
                    <div className="w-9 h-9 rounded-lg bg-saffron-50 border border-saffron-100 flex items-center justify-center shrink-0 text-saffron-500">
                      <Search size={15} />
                    </div>
                    <div>
                      <p className="text-sm font-semibold font-heading text-gray-900">{o.order_code}</p>
                      <p className="text-[11px] text-gray-400 font-body">{o.product_name || o.commodity_name}</p>
                    </div>
                  </button>
                ))
              ) : (
                <div className="py-8 text-center text-sm text-gray-400 font-body">No active orders found.</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* STEP 2: Type selection */}
      {!done && step === 2 && (
        <div className="bg-white rounded-xl border border-beige-200 shadow-card p-4 space-y-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide font-body">
            Order: <strong className="text-gray-800">{selectedOrder?.order_code}</strong>
          </p>

          {/* Tab */}
          {TABS.length > 1 && (
          <div className="flex bg-beige-100 rounded-lg p-1 gap-1">
            {TABS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => {
                  setUploadTab(key)
                  setSelectedCat(null)
                }}
                className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                  uploadTab === key ? 'bg-white shadow-sm text-saffron-700' : 'text-gray-500'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          )}

          {uploadTab === 'photo' ? (
            <div className="grid grid-cols-2 gap-2">
              {PHOTO_CATS.map((c) => (
                <button
                  key={c.value}
                  onClick={() => {
                    setSelectedCat(c.value)
                    setStep(3)
                  }}
                  className="p-3 rounded-xl border-2 border-beige-200 text-left hover:border-saffron-400 hover:bg-saffron-50 transition-all"
                >
                  <p className="text-sm font-medium text-gray-700">{c.label}</p>
                  <p className="text-[11px] text-gray-400 mt-0.5">{c.hint}</p>
                </button>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {['INVOICE', 'BL_COPY', 'COA', 'PHYTOSANITARY_CERTIFICATE', 'LAB_REPORT', 'PACKING_LIST'].map((t) => (
                <button
                  key={t}
                  onClick={() => {
                    setSelectedCat(t)
                    setStep(3)
                  }}
                  className="w-full px-4 py-3 rounded-xl border-2 border-beige-200 text-left text-sm font-medium text-gray-700 hover:border-saffron-400 hover:bg-saffron-50 transition-all"
                >
                  {t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                </button>
              ))}
            </div>
          )}
          <button onClick={() => setStep(1)} className="text-sm text-gray-400 hover:text-gray-600">
            ← Back
          </button>
        </div>
      )}

      {/* STEP 3: File upload */}
      {!done && step === 3 && (
        <div className="bg-white rounded-xl border border-beige-200 shadow-card p-4 space-y-4">
          <p className="text-xs text-gray-500 font-body uppercase tracking-wide">
            {selectedOrder?.order_code} · <strong className="text-gray-700">{selectedCat?.replace(/_/g, ' ')}</strong>
          </p>

          {/* Drop zone */}
          <label className="block cursor-pointer">
            <input
              type="file"
              className="hidden"
              accept={uploadTab === 'photo' ? 'image/*' : '.pdf,.xlsx,.docx'}
              onChange={handleFile}
            />
            {preview ? (
              <div className="relative rounded-xl overflow-hidden aspect-video">
                <img src={preview} alt="" className="w-full h-full object-cover" />
                <div className="absolute top-2 right-2">
                  <button
                    onClick={(e) => {
                      e.preventDefault()
                      setFile(null)
                      setPreview(null)
                    }}
                    className="w-7 h-7 bg-white/90 rounded-full flex items-center justify-center text-gray-600 text-xs shadow"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ) : file ? (
              <div className="flex items-center gap-3 p-3 rounded-xl border border-beige-200 bg-beige-50">
                <FileText size={20} className="text-gray-400 shrink-0" />
                <p className="text-sm text-gray-700 truncate flex-1">{file.name}</p>
                <button
                  onClick={(e) => {
                    e.preventDefault()
                    setFile(null)
                  }}
                  className="text-gray-400 text-xs hover:text-red-500"
                >
                  ✕
                </button>
              </div>
            ) : (
              <div className="border-2 border-dashed border-beige-300 rounded-xl p-10 flex flex-col items-center gap-2 hover:border-saffron-400 hover:bg-saffron-50/30 transition-colors">
                <Upload size={28} className="text-saffron-400" />
                <p className="text-sm text-gray-600 font-body font-medium">Tap to select</p>
                <p className="text-[11px] text-gray-400">
                  {uploadTab === 'photo' ? 'JPEG, PNG, WebP, HEIC' : 'PDF, XLSX, DOCX'}
                </p>
              </div>
            )}
          </label>

          <div className="flex gap-3">
            <Button variant="outline" className="flex-1" onClick={() => setStep(2)}>
              Back
            </Button>
            <Button className="flex-1" loading={uploading} disabled={!file} onClick={handleUpload}>
              {uploading ? 'Uploading…' : 'Upload'}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
