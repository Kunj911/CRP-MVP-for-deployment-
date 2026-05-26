import { FileText, Download, FileSpreadsheet, File } from 'lucide-react'
import dayjs from 'dayjs'
import Badge from '../ui/Badge'
import Button from '../ui/Button'

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

export default function DocumentVault({ documents = [], onDownload }) {
  if (!documents.length) {
    return (
      <div className="py-12 text-center">
        <FileText size={40} className="text-beige-300 mx-auto mb-3" />
        <p className="text-sm text-gray-400 font-body">No documents uploaded yet.</p>
      </div>
    )
  }

  return (
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
          </div>

          {/* Download */}
          <Button
            variant="outline"
            size="sm"
            icon={Download}
            onClick={() => onDownload?.(doc)}
          >
            <span className="hidden sm:inline">Download</span>
          </Button>
        </div>
      ))}
    </div>
  )
}
