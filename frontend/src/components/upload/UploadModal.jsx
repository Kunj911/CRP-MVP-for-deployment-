import { useState, useRef } from 'react'
import { X, Upload, Image, FileText, CheckCircle2 } from 'lucide-react'
import Button from '../ui/Button'

const PHOTO_CATEGORIES = [
  { value: 'PROCUREMENT_IMAGE', label: '🌾 Procurement',  color: 'bg-amber-50 border-amber-200' },
  { value: 'PACKAGING_IMAGE',   label: '📦 Packaging',    color: 'bg-purple-50 border-purple-200' },
  { value: 'QA_IMAGE',          label: '🧪 QA Testing',   color: 'bg-blue-50 border-blue-200' },
  { value: 'LOADING_IMAGE',     label: '🚢 Loading',      color: 'bg-saffron-50 border-saffron-200' },
]

const DOC_TYPES = [
  { value: 'INVOICE',                   label: 'Invoice' },
  { value: 'BL_COPY',                   label: 'Bill of Lading' },
  { value: 'COA',                        label: 'Certificate of Analysis' },
  { value: 'PHYTOSANITARY_CERTIFICATE', label: 'Phytosanitary Certificate' },
  { value: 'LAB_REPORT',                label: 'Lab Report' },
  { value: 'PACKING_LIST',              label: 'Packing List' },
]

export default function UploadModal({ isOpen, onClose, orderId, orderCode }) {
  const [tab, setTab] = useState('photo')          // 'photo' | 'document'
  const [category, setCategory] = useState(null)
  const [docType, setDocType] = useState(null)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [done, setDone] = useState(false)
  const fileInputRef = useRef()

  if (!isOpen) return null

  function handleFile(e) {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    if (tab === 'photo' && f.type.startsWith('image/')) {
      setPreview(URL.createObjectURL(f))
    }
  }

  async function handleUpload() {
    if (!file || (tab === 'photo' && !category) || (tab === 'document' && !docType)) return
    setUploading(true)
    // Simulate — replace with real API call
    await new Promise((r) => setTimeout(r, 1500))
    setUploading(false)
    setDone(true)
  }

  function handleClose() {
    setTab('photo'); setCategory(null); setDocType(null)
    setFile(null); setPreview(null); setDone(false)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/40" onClick={handleClose} />

      {/* Sheet */}
      <div className="relative bg-white w-full md:w-[480px] md:rounded-2xl rounded-t-2xl max-h-[90vh] overflow-y-auto shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-beige-200">
          <div>
            <h2 className="font-heading font-semibold text-gray-900 text-base">Upload Files</h2>
            <p className="text-[11px] text-gray-400 font-body">{orderCode}</p>
          </div>
          <button onClick={handleClose} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-beige-100 text-gray-500">
            <X size={18} />
          </button>
        </div>

        {/* Done state */}
        {done ? (
          <div className="flex flex-col items-center py-12 px-5 gap-3">
            <div className="w-16 h-16 rounded-full bg-cardamom-50 flex items-center justify-center">
              <CheckCircle2 size={36} className="text-cardamom-500" />
            </div>
            <p className="font-heading font-semibold text-gray-900">Upload Successful!</p>
            <p className="text-sm text-gray-400 text-center font-body">File has been saved to order {orderCode}.</p>
            <div className="flex gap-3 mt-2 w-full">
              <Button variant="outline" className="flex-1" onClick={handleClose}>Done</Button>
              <Button className="flex-1" onClick={() => { setFile(null); setPreview(null); setDone(false) }}>
                Upload Another
              </Button>
            </div>
          </div>
        ) : (
          <div className="px-5 py-4 space-y-5">
            {/* Tab switcher */}
            <div className="flex bg-beige-100 rounded-lg p-1 gap-1">
              {[{ key:'photo', label:'📷 Photo', icon: Image }, { key:'document', label:'📄 Document', icon: FileText }].map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => { setTab(key); setFile(null); setPreview(null); setCategory(null); setDocType(null) }}
                  className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                    tab === key ? 'bg-white shadow-sm text-saffron-700' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Step 1: Category or Doc type */}
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                {tab === 'photo' ? 'Photo Category' : 'Document Type'}
              </p>
              <div className="grid grid-cols-2 gap-2">
                {(tab === 'photo' ? PHOTO_CATEGORIES : DOC_TYPES).map((item) => {
                  const selected = tab === 'photo' ? category === item.value : docType === item.value
                  return (
                    <button
                      key={item.value}
                      onClick={() => tab === 'photo' ? setCategory(item.value) : setDocType(item.value)}
                      className={`p-3 text-left rounded-xl border-2 text-sm font-medium transition-all ${
                        selected
                          ? 'border-saffron-500 bg-saffron-50 text-saffron-800'
                          : `border-beige-200 bg-white text-gray-600 hover:border-beige-300 ${item.color ?? ''}`
                      }`}
                    >
                      {item.label}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Step 2: File drop zone */}
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">File</p>
              <input
                ref={fileInputRef}
                type="file"
                accept={tab === 'photo' ? 'image/*' : '.pdf,.xlsx,.docx'}
                className="hidden"
                onChange={handleFile}
              />
              {preview ? (
                <div className="relative rounded-xl overflow-hidden border border-beige-200 h-48">
                  <img src={preview} alt="preview" className="w-full h-full object-cover" />
                  <button
                    onClick={() => { setFile(null); setPreview(null) }}
                    className="absolute top-2 right-2 w-7 h-7 bg-white/90 rounded-full flex items-center justify-center shadow"
                  >
                    <X size={14} />
                  </button>
                </div>
              ) : file ? (
                <div className="flex items-center gap-3 p-3 rounded-xl border border-beige-200 bg-beige-50">
                  <FileText size={20} className="text-gray-400 shrink-0" />
                  <p className="text-sm text-gray-700 truncate">{file.name}</p>
                  <button onClick={() => setFile(null)} className="ml-auto text-gray-400 hover:text-red-500">
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full border-2 border-dashed border-beige-300 rounded-xl p-8 flex flex-col items-center gap-2 hover:border-saffron-400 hover:bg-saffron-50/30 transition-colors"
                >
                  <Upload size={24} className="text-saffron-400" />
                  <span className="text-sm text-gray-500 font-body">Tap to select file</span>
                  <span className="text-[11px] text-gray-400">
                    {tab === 'photo' ? 'JPEG, PNG, WebP, HEIC · max 10MB' : 'PDF, XLSX, DOCX · max 25MB'}
                  </span>
                </button>
              )}
            </div>

            {/* Upload button */}
            <Button
              className="w-full"
              loading={uploading}
              disabled={!file || (tab === 'photo' ? !category : !docType)}
              onClick={handleUpload}
            >
              {uploading ? 'Uploading…' : 'Upload'}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
