import { useState, useEffect } from 'react'
import { FileText, Download, Check, X, Upload, AlertCircle, RefreshCw, Trash2 } from 'lucide-react'
import dayjs from 'dayjs'
import useAuthStore from '../../store/authStore'
import { uploadsApi, documentsApi } from '../../api'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import UploadModal from '../upload/UploadModal'

const DOC_TYPE_LABELS = {
  invoice:                  'Invoice',
  bill_of_lading:           'Bill of Lading',
  certificate_of_analysis:  'Certificate of Analysis (COA)',
  phytosanitary_certificate:'Phytosanitary Certificate',
  lab_report:               'Lab Report',
  packing_list:             'Packing List',
  product_specification:    'Product Specification',
  insurance_certificate:    'Insurance Certificate',
  purchase_order:           'Purchase Order (PO)',
  certificate_of_origin:    'Certificate of Origin (COO)',
  other:                    'Other Document',
}

export default function DocumentChecklist({ orderId, orderCode, onTimelineUpdate }) {
  const { user } = useAuthStore()
  const isStaff = useAuthStore((s) => s.isStaff())
  
  const canReview = user && ['QA', 'ADMIN', 'SUPER_ADMIN'].includes(user.role)
  const canUpload = user && ['DOCUMENTATION', 'ADMIN', 'SUPER_ADMIN'].includes(user.role)
  const canDelete = user && ['SUPER_ADMIN', 'ADMIN'].includes(user.role)

  const [checklist, setChecklist] = useState([])
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  // Rejection modal/state
  const [rejectingItem, setRejectingItem] = useState(null)
  const [remarks, setRemarks] = useState('')
  const [submittingReject, setSubmittingReject] = useState(false)

  // Upload modal state
  const [uploadOpen, setUploadOpen] = useState(false)
  const [preselectedDocType, setPreselectedDocType] = useState(null)

  const loadChecklistData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const checklistRes = await uploadsApi.getDocumentChecklist(orderId)
      const rawChecklist = Array.isArray(checklistRes.data?.data) ? checklistRes.data.data : []
      
      const docsRes = await documentsApi.listByOrder(orderId)
      const rawDocs = Array.isArray(docsRes.data?.data) ? docsRes.data.data : []
      
      setChecklist(rawChecklist)
      setDocuments(rawDocs)
    } catch (err) {
      console.error('Failed to load document checklist:', err)
      setError('Could not retrieve documentation checklist.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (orderId) {
      loadChecklistData()
    }
  }, [orderId])

  const handleDownload = async (docId, fileName) => {
    try {
      const response = await documentsApi.download(docId)
      const blob = new Blob([response.data], { type: response.headers['content-type'] || 'application/octet-stream' })
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      link.download = fileName || 'document.pdf'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(link.href)
    } catch (err) {
      console.error('Download failed:', err)
      alert('Failed to download file.')
    }
  }

  const handleApprove = async (docId) => {
    if (!confirm('Are you sure you want to approve this document? This will make it visible to the customer and update the checklist.')) {
      return
    }
    try {
      await documentsApi.approve(docId)
      await loadChecklistData()
      if (onTimelineUpdate) onTimelineUpdate()
    } catch (err) {
      console.error('Approval failed:', err)
      alert(err.response?.data?.error?.message || 'Failed to approve document.')
    }
  }

  const handleRejectSubmit = async () => {
    if (!remarks.trim()) {
      alert('Rejection remarks are required.')
      return
    }
    setSubmittingReject(true)
    try {
      await documentsApi.reject(rejectingItem.document_id, remarks)
      setRejectingItem(null)
      setRemarks('')
      await loadChecklistData()
      if (onTimelineUpdate) onTimelineUpdate()
    } catch (err) {
      console.error('Rejection failed:', err)
      alert(err.response?.data?.error?.message || 'Failed to reject document.')
    } finally {
      setSubmittingReject(false)
    }
  }

  const handleDelete = async (docId, fileName) => {
    if (!confirm(`Delete "${fileName || 'this document'}"? This action cannot be undone.`)) return
    try {
      await documentsApi.delete(docId)
      await loadChecklistData()
      if (onTimelineUpdate) onTimelineUpdate()
    } catch (err) {
      console.error('Delete failed:', err)
      alert(err.response?.data?.error?.message || 'Failed to delete document.')
    }
  }

  const handleOpenUpload = (docType) => {
    setPreselectedDocType(docType)
    setUploadOpen(true)
  }

  const formatSize = (bytes) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1048576).toFixed(1)} MB`
  }

  if (loading && !checklist.length) {
    return (
      <div className="py-12 text-center flex flex-col items-center justify-center gap-2">
        <RefreshCw className="w-6 h-6 animate-spin text-saffron-500" />
        <p className="text-sm text-gray-400 font-body">Loading checklist...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-12 text-center text-red-500 font-body flex flex-col items-center gap-2">
        <AlertCircle size={24} />
        <p>{error}</p>
        <Button size="sm" variant="outline" onClick={loadChecklistData}>Retry</Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-heading font-semibold text-gray-800 text-sm">Export Documentation Checklist</h3>
        <span className="text-xs text-gray-400 font-body">
          {checklist.filter(item => item.approved).length} / {checklist.filter(item => item.required).length} Required Approved
        </span>
      </div>

      <div className="overflow-x-auto border border-beige-200 rounded-xl bg-white shadow-sm">
        <table className="min-w-full divide-y divide-beige-100 text-left text-sm font-body">
          <thead className="bg-beige-50 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Document Category</th>
              <th className="px-4 py-3">Requirement</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">File Details</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-beige-100 bg-white">
            {checklist.map((item) => {
              // Match with loaded documents to get rich details (like filename and status)
              const matchedDoc = documents.find(d => d.id === item.document_id)
              
              // Determine status badge
              let statusLabel = 'Pending'
              let statusBadgeType = 'PENDING'
              
              if (item.approved) {
                statusLabel = 'Approved'
                statusBadgeType = 'approved'
              } else if (matchedDoc) {
                if (matchedDoc.status === 'rejected') {
                  statusLabel = 'Rejected'
                  statusBadgeType = 'rejected'
                } else {
                  statusLabel = 'Under Review'
                  statusBadgeType = 'under_review'
                }
              } else if (item.required) {
                statusLabel = 'Required'
                statusBadgeType = 'QA_TESTING' // Blue/orange warning style
              } else {
                statusLabel = 'Optional'
                statusBadgeType = 'PENDING'
              }

              return (
                <tr key={item.id} className="hover:bg-beige-50/30 transition-colors">
                  {/* Category */}
                  <td className="px-4 py-3.5 font-medium text-gray-800 font-heading">
                    {DOC_TYPE_LABELS[item.document_type] ?? item.document_type}
                  </td>
                  
                  {/* Required / Optional */}
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    {item.required ? (
                      <span className="inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded-full bg-saffron-50 text-saffron-700 border border-saffron-100">
                        Required
                      </span>
                    ) : (
                      <span className="inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded-full bg-gray-50 text-gray-400 border border-gray-100">
                        Optional
                      </span>
                    )}
                  </td>
                  
                  {/* Status Badge */}
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    <Badge status={statusBadgeType} size="sm" />
                  </td>
                  
                  {/* File details */}
                  <td className="px-4 py-3.5">
                    {matchedDoc ? (
                      <div className="max-w-[200px] sm:max-w-xs">
                        <p className="text-xs text-gray-700 truncate font-heading" title={matchedDoc.file_name}>
                          {matchedDoc.file_name}
                        </p>
                        <p className="text-[10px] text-gray-400 mt-0.5">
                          {formatSize(matchedDoc.file_size)} · {dayjs(matchedDoc.uploaded_at).format('DD MMM YYYY')}
                        </p>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400 italic">No file uploaded</span>
                    )}
                  </td>

                  {/* Actions */}
                  <td className="px-4 py-3.5 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5">
                      {/* Download */}
                      {matchedDoc && (
                        <button
                          onClick={() => handleDownload(matchedDoc.id, matchedDoc.file_name)}
                          className="p-1.5 rounded-lg border border-beige-200 text-gray-500 hover:text-saffron-600 hover:bg-beige-100 transition-colors"
                          title="Download Document"
                        >
                          <Download size={14} />
                        </button>
                      )}

                      {/* Approve / Reject (QA/Admin only) */}
                      {matchedDoc && !item.approved && canReview && (
                        <>
                          <button
                            onClick={() => handleApprove(matchedDoc.id)}
                            className="p-1.5 rounded-lg border border-cardamom-200 text-cardamom-600 hover:bg-cardamom-50 transition-colors"
                            title="Approve"
                          >
                            <Check size={14} />
                          </button>
                          <button
                            onClick={() => setRejectingItem(item)}
                            className="p-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 transition-colors"
                            title="Reject"
                          >
                            <X size={14} />
                          </button>
                        </>
                      )}

                      {/* Delete (Admin only) */}
                      {matchedDoc && canDelete && (
                        <button
                          onClick={() => handleDelete(matchedDoc.id, matchedDoc.file_name)}
                          className="p-1.5 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 transition-colors"
                          title="Delete document"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}

                      {/* Upload / Replace (Docs/Admin only) */}
                      {canUpload && (
                        <button
                          onClick={() => handleOpenUpload(item.document_type)}
                          className="flex items-center gap-1 text-[11px] font-medium px-2 py-1 rounded-lg border border-beige-300 text-gray-600 hover:border-saffron-500 hover:text-saffron-600 transition-colors"
                        >
                          <Upload size={12} />
                          {matchedDoc ? 'Replace' : 'Upload'}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Upload Modal */}
      <UploadModal
        isOpen={uploadOpen}
        onClose={() => setUploadOpen(false)}
        orderId={orderId}
        orderCode={orderCode}
        initialTab="document"
        initialDocType={preselectedDocType}
        onSuccess={() => {
          setUploadOpen(false)
          loadChecklistData()
          if (onTimelineUpdate) onTimelineUpdate()
        }}
      />

      {/* Reject Remarks Modal */}
      {rejectingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setRejectingItem(null)} />
          <div className="relative bg-white rounded-xl p-5 w-full max-w-sm mx-4 shadow-xl space-y-4">
            <div>
              <h4 className="font-heading font-semibold text-gray-900 text-base">Reject Document</h4>
              <p className="text-xs text-gray-400 font-body">Provide a reason for rejecting this document</p>
            </div>
            
            <textarea
              className="w-full border border-beige-300 rounded-lg p-2.5 text-sm focus:outline-none focus:border-saffron-400 font-body"
              rows={3}
              placeholder="e.g. Commercial invoice amount mismatch, please upload revised version."
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
            />

            <div className="flex gap-2.5">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => { setRejectingItem(null); setRemarks('') }}
                disabled={submittingReject}
              >
                Cancel
              </Button>
              <Button
                className="flex-1"
                loading={submittingReject}
                onClick={handleRejectSubmit}
              >
                Reject
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
