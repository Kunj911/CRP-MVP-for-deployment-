const STATUS_STYLES = {
  // Order statuses
  CREATED:              'bg-gray-100 text-gray-600',
  PROCUREMENT:          'bg-amber-100 text-amber-700',
  QA_TESTING:           'bg-blue-100 text-blue-700',
  PACKAGING:            'bg-purple-100 text-purple-700',
  DOCUMENTATION:        'bg-indigo-100 text-indigo-700',
  SHIPMENT_DISPATCHED:  'bg-saffron-100 text-saffron-700',
  DELIVERED:            'bg-cardamom-100 text-cardamom-700',
  CANCELLED:            'bg-red-100 text-red-600',
  // Milestone statuses
  PENDING:              'bg-gray-100 text-gray-500',
  IN_PROGRESS:          'bg-saffron-100 text-saffron-700',
  COMPLETED:            'bg-cardamom-100 text-cardamom-700',
  FAILED:               'bg-red-100 text-red-600',
  // Delivery statuses
  SENT:                 'bg-cardamom-100 text-cardamom-700',
}

const STATUS_LABELS = {
  SHIPMENT_DISPATCHED: 'Dispatched',
  QA_TESTING: 'QA Testing',
  IN_PROGRESS: 'In Progress',
}

export default function Badge({ status, size = 'sm' }) {
  const style = STATUS_STYLES[status] ?? 'bg-gray-100 text-gray-500'
  const label = STATUS_LABELS[status] ?? status?.replace(/_/g, ' ')
  const sizeClass = size === 'sm' ? 'text-[11px] px-2 py-0.5' : 'text-xs px-2.5 py-1'
  return (
    <span className={`inline-flex items-center font-medium rounded-full ${sizeClass} ${style}`}>
      {label}
    </span>
  )
}
