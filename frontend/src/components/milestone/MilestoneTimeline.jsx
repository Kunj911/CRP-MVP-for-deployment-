import { useState } from 'react'
import { Check, Circle, Clock, ChevronRight } from 'lucide-react'
import dayjs from 'dayjs'
import { milestonesApi } from '../../api'
import useAuthStore from '../../store/authStore'

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

export default function MilestoneTimeline({ milestones = [], orderId, onStageComplete }) {
  const [completing, setCompleting] = useState(null)
  const user = useAuthStore((s) => s.user)
  const canProgress = user && ['SUPER_ADMIN', 'ADMIN', 'WAREHOUSE'].includes(user.role)

  const handleComplete = async (milestoneId) => {
    setCompleting(milestoneId)
    try {
      await milestonesApi.completeStage(orderId)
      if (onStageComplete) onStageComplete()
    } catch (err) {
      console.error('Failed to complete stage:', err)
      alert(err.response?.data?.error?.message || 'Failed to complete stage.')
    } finally {
      setCompleting(null)
    }
  }

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
        const isActive = m.status === 'IN_PROGRESS'
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
                    : isActive ? 'text-forest-800'
                    : 'text-slate-400'
                  }`}>
                    {m.stage_label ?? m.stage_name?.replace(/_/g, ' ')}
                  </p>
                  <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
                    m.status === 'COMPLETED' ? 'text-forest-700 bg-forest-50'
                    : isActive ? 'text-amber-700 bg-amber-50'
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
                {isActive && (
                  <p className="text-[11px] text-forest-600 mt-0.5 font-body">In progress…</p>
                )}

                {m.remarks && (
                  <p className="text-[11px] text-slate-400 mt-1 italic truncate">{m.remarks}</p>
                )}

                {isActive && canProgress && (
                  <button
                    onClick={() => handleComplete(m.id)}
                    disabled={completing === m.id}
                    className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-white bg-forest-700 hover:bg-forest-800 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg px-3 py-1.5 transition-colors"
                  >
                    {completing === m.id ? (
                      <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <ChevronRight size={13} />
                    )}
                    {completing === m.id ? 'Completing…' : 'Mark Stage Complete'}
                  </button>
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
