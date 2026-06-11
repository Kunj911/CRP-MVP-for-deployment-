import { useState } from 'react'
import { FileText, Download, FileSpreadsheet, File, Trash2, AlertTriangle, X, CheckCircle2 } from 'lucide-react'
import dayjs from 'dayjs'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import useAuthStore from '../../store/authStore'

const DOC_TYPE_LABELS = {
  INVOICE:                  'Invoice',
  BL_COPY:                  'Bill of Lading',
  COA:                      'Certificate of Analysis',
  PHYTOSANITARY_CERTIFICATE:'Phytosanitary Certificate',
  LAB_REPORT:               'Lab Report',
  PACKING_LIST:             'Packing List',
  OTHER:                    'Document',
}

function DocIcon({ name }) {
  const ext = name?.split('.').pop()?.toLowerCase()
  if (ext === 'pdf')  return <FileText size={20} className="text-red-500" />
  if (ext === 'xlsx') return <FileSpreadsheet size={20} className="text-cardamom-600" />
  return <File size={20} className="text-gray-400" />
}

export default function DocumentVault({ documents = [], onDownload, onDelete }) {
  const role = useAuthStore((s) => s.user?.role)
  const canDelete = ['SUPER_ADMIN', 'ADMIN'].includes(role)
  const [deleteTarget, setDeleteTarget] = useState(null)

  if (!documents.length) {
    return (
      <div className="py-12 text-center">
        <FileText size={40} className="text-beige-300 mx-auto mb-3" />
        <p className="text-sm text-gray-400 font-body">No documents uploaded yet.</p>
      </div>
    )
  }

  function confirmDelete(doc) {
    setDeleteTarget(doc)
  }

  async function handleConfirmDelete() {
    if (!deleteTarget) return
    try {
      await onDelete?.(deleteTarget)
    } finally {
      setDeleteTarget(null)
    }
  }

  return (
    <>
      <div className="space-y-2">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="flex items-center gap-3 bg-white border border-beige-200 rounded-xl p-3.5 hover:border-saffron-200 transition-colors"
          >
            {/* Icon */}
            <div className="w-10 h-10 rounded-lg bg-beige-100 flex items-center justify-center shrink-0">
              <DocIcon name={doc.file_name} />
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800 truncate font-heading">
                {DOC_TYPE_LABELS[doc.document_type] ?? doc.document_type}
              </p>
              <p className="text-[11px] text-gray-400 font-body truncate">
                {doc.file_name} · {dayjs(doc.uploaded_at).format('DD MMM YYYY')}
              </p>
              {doc.status && (
                <span className={`inline-block text-[10px] mt-0.5 px-1.5 py-0.5 rounded font-medium ${
                  doc.status === 'approved' ? 'bg-cardamom-50 text-cardamom-600' :
                  doc.status === 'rejected' ? 'bg-red-50 text-red-600' :
                  'bg-beige-100 text-gray-500'
                }`}>
                  {doc.status}
                </span>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="sm"
                icon={Download}
                onClick={() => onDownload?.(doc)}
              >
                <span className="hidden sm:inline">Download</span>
              </Button>
              {canDelete && (
                <button
                  onClick={() => confirmDelete(doc)}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                  title="Delete document"
                >
                  <Trash2 size={15} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setDeleteTarget(null)} />
          <div className="relative bg-white w-full max-w-sm mx-4 rounded-2xl shadow-xl p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center shrink-0">
                <AlertTriangle size={20} className="text-red-500" />
              </div>
              <div>
                <h3 className="font-heading font-semibold text-gray-900">Delete Document</h3>
                <p className="text-xs text-gray-500 font-body">This action cannot be undone.</p>
              </div>
              <button onClick={() => setDeleteTarget(null)} className="ml-auto w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:bg-beige-100">
                <X size={16} />
              </button>
            </div>

            <div className="bg-beige-50 rounded-xl p-3 space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Asset</span>
                <span className="font-medium text-gray-800">{deleteTarget.file_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Type</span>
                <span className="font-medium text-gray-800">{DOC_TYPE_LABELS[deleteTarget.document_type] ?? deleteTarget.document_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Uploaded</span>
                <span className="font-medium text-gray-800">{dayjs(deleteTarget.uploaded_at).format('DD MMM YYYY')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Status</span>
                <span className={`font-medium ${
                  deleteTarget.status === 'approved' ? 'text-cardamom-600' :
                  deleteTarget.status === 'rejected' ? 'text-red-600' :
                  'text-gray-800'
                }`}>
                  {deleteTarget.status || 'uploaded'}
                </span>
              </div>
            </div>

            <div className="flex gap-3">
              <Button variant="outline" className="flex-1" onClick={() => setDeleteTarget(null)}>
                Cancel
              </Button>
              <Button
                className="flex-1 bg-red-600 hover:bg-red-700 text-white"
                onClick={handleConfirmDelete}
              >
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
