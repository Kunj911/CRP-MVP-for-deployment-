import { Check, Circle, Clock } from 'lucide-react'
import dayjs from 'dayjs'

function StageIcon({ status }) {
  if (status === 'COMPLETED')
    return (
      <div className="w-8 h-8 rounded-full bg-forest-600 flex items-center justify-center shadow-sm">
        <Check size={14} strokeWidth={3} className="text-white" />
      </div>
    )
  if (status === 'IN_PROGRESS')
    return (
      <div className="w-8 h-8 rounded-full bg-forest-700 flex items-center justify-center shadow-sm ring-4 ring-forest-100">
        <Clock size={14} className="text-white" />
      </div>
    )
  return (
    <div className="w-8 h-8 rounded-full bg-agri-200 border-2 border-agri-300 flex items-center justify-center">
      <Circle size={10} className="text-agri-400" />
    </div>
  )
}

function Connector({ completed }) {
  return (
    <div className={`w-0.5 h-8 ml-[15px] ${completed ? 'bg-forest-400' : 'bg-agri-200'}`} />
  )
}

export default function MilestoneTimeline({ milestones = [] }) {
  if (!milestones.length) {
    return (
      <p className="text-sm text-slate-400 py-6 text-center font-body">
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
              <div className="flex flex-col items-center shrink-0">
                <StageIcon status={m.status} />
              </div>

              <div className="pb-1 min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <p className={`text-sm font-medium font-heading leading-tight ${
                    m.status === 'COMPLETED' ? 'text-slate-900'
                    : m.status === 'IN_PROGRESS' ? 'text-forest-800'
                    : 'text-slate-400'
                  }`}>
                    {m.stage_label ?? m.stage_name?.replace(/_/g, ' ')}
                  </p>
                  <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
                    m.status === 'COMPLETED' ? 'text-forest-700 bg-forest-50'
                    : m.status === 'IN_PROGRESS' ? 'text-amber-700 bg-amber-50'
                    : 'text-slate-400 bg-gray-100'
                  }`}>
                    {m.status?.replace('_', ' ')}
                  </span>
                </div>

                {m.status === 'COMPLETED' && (
                  <p className="text-[11px] text-slate-400 mt-0.5 font-body">
                    Completed {m.completed_at ? dayjs(m.completed_at).format('DD MMM · HH:mm') : ''}
                    {m.completer?.full_name && ` · by ${m.completer.full_name}`}
                  </p>
                )}
                {m.status === 'IN_PROGRESS' && (
                  <p className="text-[11px] text-forest-600 mt-0.5 font-body">In progress…</p>
                )}

                {m.remarks && (
                  <p className="text-[11px] text-slate-400 mt-1 italic truncate">{m.remarks}</p>
                )}
              </div>
            </div>

            {!isLast && <Connector completed={m.status === 'COMPLETED'} />}
          </div>
        )
      })}
    </div>
  )
}
