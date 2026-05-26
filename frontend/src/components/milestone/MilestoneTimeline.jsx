import { Check, Circle, Clock } from 'lucide-react'
import dayjs from 'dayjs'

/* Icon per status */
function StageIcon({ status }) {
  if (status === 'COMPLETED')
    return (
      <div className="w-8 h-8 rounded-full bg-cardamom-500 flex items-center justify-center shadow-sm">
        <Check size={14} strokeWidth={3} className="text-white" />
      </div>
    )
  if (status === 'IN_PROGRESS')
    return (
      <div className="w-8 h-8 rounded-full bg-saffron-500 flex items-center justify-center shadow-sm ring-4 ring-saffron-100">
        <Clock size={14} className="text-white" />
      </div>
    )
  return (
    <div className="w-8 h-8 rounded-full bg-beige-200 border-2 border-beige-300 flex items-center justify-center">
      <Circle size={10} className="text-beige-400" />
    </div>
  )
}

/* Connector line between nodes */
function Connector({ completed }) {
  return (
    <div className={`w-0.5 h-8 ml-[15px] ${completed ? 'bg-cardamom-400' : 'bg-beige-200'}`} />
  )
}

export default function MilestoneTimeline({ milestones = [] }) {
  if (!milestones.length) {
    return (
      <p className="text-sm text-gray-400 py-6 text-center font-body">
        No milestones initialized for this order.
      </p>
    )
  }

  return (
    <div className="py-2">
      {milestones.map((m, idx) => {
        const isLast = idx === milestones.length - 1
        return (
          <div key={m.id}>
            <div className="flex items-start gap-4">
              {/* Left: icon column */}
              <div className="flex flex-col items-center shrink-0">
                <StageIcon status={m.status} />
              </div>

              {/* Right: content */}
              <div className="pb-1 min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <p className={`text-sm font-medium font-heading leading-tight ${
                    m.status === 'COMPLETED' ? 'text-gray-900'
                    : m.status === 'IN_PROGRESS' ? 'text-saffron-700'
                    : 'text-gray-400'
                  }`}>
                    {m.stage_label ?? m.stage_name?.replace(/_/g, ' ')}
                  </p>
                  <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
                    m.status === 'COMPLETED' ? 'text-cardamom-700 bg-cardamom-50'
                    : m.status === 'IN_PROGRESS' ? 'text-saffron-700 bg-saffron-50'
                    : 'text-gray-400 bg-gray-100'
                  }`}>
                    {m.status?.replace('_', ' ')}
                  </span>
                </div>

                {/* Completer + date */}
                {m.status === 'COMPLETED' && (
                  <p className="text-[11px] text-gray-400 mt-0.5 font-body">
                    Completed {m.completed_at ? dayjs(m.completed_at).format('DD MMM · HH:mm') : ''}
                    {m.completer?.full_name && ` · by ${m.completer.full_name}`}
                  </p>
                )}
                {m.status === 'IN_PROGRESS' && (
                  <p className="text-[11px] text-saffron-500 mt-0.5 font-body">In progress…</p>
                )}

                {/* Remarks */}
                {m.remarks && (
                  <p className="text-[11px] text-gray-400 mt-1 italic truncate">{m.remarks}</p>
                )}
              </div>
            </div>

            {/* Connector (not after last node) */}
            {!isLast && <Connector completed={m.status === 'COMPLETED'} />}
          </div>
        )
      })}
    </div>
  )
}
