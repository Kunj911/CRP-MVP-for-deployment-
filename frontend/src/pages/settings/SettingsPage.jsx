import { useState, useEffect } from 'react'
import { Shield, Key, Laptop, Globe, LogOut, Trash2, CheckCircle, AlertTriangle } from 'lucide-react'
import Button from '../../components/ui/Button'
import apiClient from '../../api/client'
import useAuthStore from '../../store/authStore'
import { toast } from 'sonner'

export default function SettingsPage() {
  const { user, logout } = useAuthStore()
  const [sessions, setSessions] = useState([])
  const [loadingSessions, setLoadingSessions] = useState(true)
  const [revokingId, setRevokingId] = useState(null)
  const [revokingOthers, setRevokingOthers] = useState(false)

  // MFA Setup State
  const [mfaEnabled, setMfaEnabled] = useState(user?.mfa_enabled || false)
  const [mfaStep, setMfaStep] = useState('status') // 'status' | 'setup' | 'verify'
  const [mfaSecret, setMfaSecret] = useState('')
  const [mfaQrUri, setMfaQrUri] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [loadingMfa, setLoadingMfa] = useState(false)

  // Fetch active sessions
  const fetchSessions = async () => {
    try {
      setLoadingSessions(true)
      const res = await apiClient.get('/auth/sessions')
      setSessions(res.data)
    } catch (err) {
      toast.error('Failed to load active sessions')
    } finally {
      setLoadingSessions(false)
    }
  }

  useEffect(() => {
    fetchSessions()
  }, [])

  // Revoke specific session
  const handleRevokeSession = async (sessionId, isCurrent) => {
    try {
      setRevokingId(sessionId)
      await apiClient.post('/auth/sessions/revoke', { session_id: sessionId })
      toast.success('Session revoked successfully')
      
      if (isCurrent) {
        // If current session is revoked, log out the user
        logout()
      } else {
        fetchSessions()
      }
    } catch (err) {
      toast.error('Failed to revoke session')
    } finally {
      setRevokingId(null)
    }
  }

  // Revoke all other sessions
  const handleRevokeOthers = async () => {
    try {
      setRevokingOthers(true)
      await apiClient.post('/auth/sessions/revoke-others')
      toast.success('Other sessions revoked successfully')
      fetchSessions()
    } catch (err) {
      toast.error('Failed to revoke other sessions')
    } finally {
      setRevokingOthers(false)
    }
  }

  // Initiate MFA setup
  const handleStartMfaSetup = async () => {
    try {
      setLoadingMfa(true)
      const res = await apiClient.post('/auth/mfa/setup')
      setMfaSecret(res.data.secret)
      setMfaQrUri(res.data.provisioning_uri)
      setMfaStep('setup')
    } catch (err) {
      toast.error('Failed to initiate MFA setup')
    } finally {
      setLoadingMfa(false)
    }
  }

  // Verify MFA code
  const handleVerifyMfa = async (e) => {
    e.preventDefault()
    if (otpCode.length !== 6) {
      toast.error('Code must be 6 digits')
      return
    }
    try {
      setLoadingMfa(true)
      await apiClient.post('/auth/mfa/verify', { otp_code: otpCode })
      toast.success('MFA enabled successfully!')
      setMfaEnabled(true)
      setMfaStep('status')
      
      // Update store user object state
      if (user) {
        user.mfa_enabled = true
      }
    } catch (err) {
      toast.error(err.response?.data?.error?.message || 'Verification failed. Try again.')
    } finally {
      setLoadingMfa(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-bold text-slate-900">Settings & Security</h1>
        <p className="text-sm text-slate-500 font-body">Manage your account credentials, multi-factor authentication, and active sessions.</p>
      </div>

      {/* MFA Card */}
      <div className="bg-white border border-agri-200 rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-agri-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-forest-50 text-forest-600 rounded-lg">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-heading font-semibold text-slate-900">Two-Factor Authentication (2FA)</h2>
              <p className="text-xs text-slate-500 font-body font-normal">Add an extra layer of security to your account.</p>
            </div>
          </div>
          {mfaEnabled ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold bg-emerald-50 text-emerald-700 rounded-full border border-emerald-200">
              <CheckCircle className="w-3.5 h-3.5" />
              Enabled
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold bg-amber-50 text-amber-700 rounded-full border border-amber-200">
              <AlertTriangle className="w-3.5 h-3.5" />
              Not Setup
            </span>
          )}
        </div>

        <div className="p-6">
          {mfaStep === 'status' && (
            <div className="space-y-4">
              <p className="text-sm text-slate-600 font-body">
                Two-Factor Authentication (MFA) requires you to enter a 6-digit verification code from your authenticator app (like Google Authenticator, Authy, or Microsoft Authenticator) whenever you sign in. This protects your account even if someone learns your password.
              </p>
              {!mfaEnabled ? (
                <Button variant="primary" loading={loadingMfa} onClick={handleStartMfaSetup}>
                  Set Up Two-Factor Authentication
                </Button>
              ) : (
                <div className="text-sm text-slate-500 font-body flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  Your account is protected with 2FA. If you need to disable it, contact a Super Administrator.
                </div>
              )}
            </div>
          )}

          {mfaStep === 'setup' && (
            <div className="space-y-6">
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-800">1. Scan the QR Code</h3>
                <p className="text-xs text-slate-600">Scan this QR code with your Authenticator application, or copy the manual code below.</p>
              </div>

              {/* QR Code Layout */}
              <div className="flex flex-col items-center p-6 border border-agri-200 rounded-xl bg-agri-50 max-w-sm mx-auto">
                <div className="w-48 h-48 bg-white border border-agri-300 rounded-lg flex items-center justify-center shadow-inner relative overflow-hidden">
                  {/* Clean SVG Placeholder simulating a real QR code since we don't have a dynamic frontend QR library */}
                  <svg className="w-40 h-40 text-slate-900" viewBox="0 0 100 100">
                    <rect x="0" y="0" width="30" height="30" fill="currentColor"/>
                    <rect x="5" y="5" width="20" height="20" fill="white"/>
                    <rect x="10" y="10" width="10" height="10" fill="currentColor"/>
                    
                    <rect x="70" y="0" width="30" height="30" fill="currentColor"/>
                    <rect x="75" y="5" width="20" height="20" fill="white"/>
                    <rect x="80" y="10" width="10" height="10" fill="currentColor"/>

                    <rect x="0" y="70" width="30" height="30" fill="currentColor"/>
                    <rect x="5" y="75" width="20" height="20" fill="white"/>
                    <rect x="10" y="80" width="10" height="10" fill="currentColor"/>

                    <rect x="40" y="40" width="20" height="20" fill="currentColor"/>
                    <rect x="45" y="45" width="10" height="10" fill="white"/>

                    {/* Simulating random data blocks */}
                    <rect x="40" y="10" width="10" height="20" fill="currentColor"/>
                    <rect x="55" y="0" width="10" height="10" fill="currentColor"/>
                    <rect x="0" y="40" width="20" height="10" fill="currentColor"/>
                    <rect x="90" y="40" width="10" height="40" fill="currentColor"/>
                    <rect x="40" y="70" width="20" height="10" fill="currentColor"/>
                    <rect x="70" y="80" width="10" height="10" fill="currentColor"/>
                  </svg>
                </div>
                
                <div className="mt-4 w-full text-center space-y-1">
                  <p className="text-[10px] text-slate-400 uppercase font-semibold">Secret Key</p>
                  <code className="text-xs bg-white px-3 py-1.5 border border-agri-300 rounded font-mono select-all block break-all text-slate-700">
                    {mfaSecret}
                  </code>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-agri-200">
                <Button variant="outline" onClick={() => setMfaStep('status')}>Cancel</Button>
                <Button variant="primary" onClick={() => setMfaStep('verify')}>Next: Verify Code</Button>
              </div>
            </div>
          )}

          {mfaStep === 'verify' && (
            <form onSubmit={handleVerifyMfa} className="space-y-4">
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-800">2. Enter Verification Code</h3>
                <p className="text-xs text-slate-600">Enter the 6-digit code displayed in your authenticator app to complete setup.</p>
              </div>

              <div className="max-w-xs">
                <input
                  type="text"
                  maxLength={6}
                  placeholder="000000"
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                  className="w-full text-center tracking-[1em] text-2xl font-mono px-4 py-3 border border-agri-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-forest-500 focus:border-transparent text-slate-800"
                  required
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-agri-200">
                <Button variant="outline" onClick={() => setMfaStep('setup')}>Back</Button>
                <Button variant="primary" type="submit" loading={loadingMfa}>
                  Enable MFA
                </Button>
              </div>
            </form>
          )}
        </div>
      </div>

      {/* Active Sessions Card */}
      <div className="bg-white border border-agri-200 rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-agri-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-forest-50 text-forest-600 rounded-lg">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-heading font-semibold text-slate-900">Active Login Sessions</h2>
              <p className="text-xs text-slate-500 font-body font-normal">Audit and revoke active login sessions across all your devices.</p>
            </div>
          </div>
          {sessions.length > 1 && (
            <Button
              variant="outline"
              size="sm"
              loading={revokingOthers}
              onClick={handleRevokeOthers}
              className="text-xs font-semibold text-red-600 hover:bg-red-50 hover:border-red-200 hover:text-red-700"
            >
              Log Out Other Devices
            </Button>
          )}
        </div>

        <div className="p-6">
          {loadingSessions ? (
            <div className="flex flex-col items-center py-10 gap-3">
              <div className="w-8 h-8 border-2 border-forest-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-slate-500 font-body">Loading active sessions...</p>
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-10 text-slate-500 text-sm font-body">
              No active sessions found.
            </div>
          ) : (
            <div className="divide-y divide-agri-100">
              {sessions.map((s) => {
                const isMobile = s.user_agent.toLowerCase().includes('mobile') || s.user_agent.toLowerCase().includes('android') || s.user_agent.toLowerCase().includes('iphone')
                const browser = s.user_agent.includes('Chrome') ? 'Google Chrome' :
                                s.user_agent.includes('Safari') && !s.user_agent.includes('Chrome') ? 'Apple Safari' :
                                s.user_agent.includes('Firefox') ? 'Mozilla Firefox' : 'Web Browser'
                
                return (
                  <div key={s.session_id} className="py-4 first:pt-0 last:pb-0 flex items-center justify-between gap-4">
                    <div className="flex items-start gap-4 min-w-0">
                      <div className="p-2.5 bg-agri-50 border border-agri-200 text-slate-600 rounded-lg shrink-0">
                        {isMobile ? <Globe className="w-5 h-5" /> : <Laptop className="w-5 h-5" />}
                      </div>
                      <div className="min-w-0 space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-sm font-semibold text-slate-800 truncate">
                            {browser} on {isMobile ? 'Mobile Device' : 'Desktop computer'}
                          </p>
                          {s.is_current && (
                            <span className="inline-flex px-2 py-0.5 text-[10px] font-bold bg-forest-100 text-forest-800 border border-forest-200 rounded-full">
                              This Device
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-slate-400 font-body flex-wrap">
                          <span>IP Address: <span className="text-slate-600 font-medium">{s.ip_address}</span></span>
                          <span className="w-1.5 h-1.5 rounded-full bg-agri-300" />
                          <span>Logged in: <span className="text-slate-600 font-medium">{new Date(s.login_time).toLocaleString()}</span></span>
                        </div>
                      </div>
                    </div>
                    <Button
                      variant={s.is_current ? 'outline' : 'danger'}
                      size="sm"
                      icon={s.is_current ? LogOut : Trash2}
                      loading={revokingId === s.session_id}
                      onClick={() => handleRevokeSession(s.session_id, s.is_current)}
                      className={s.is_current ? 'text-xs text-slate-600 border-agri-300 hover:bg-agri-50' : 'text-xs bg-red-500 hover:bg-red-600 text-white'}
                    >
                      {s.is_current ? 'Log Out' : 'Revoke'}
                    </Button>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
