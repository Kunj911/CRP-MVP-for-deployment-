import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Shield, ChevronRight } from 'lucide-react'
import Button from '../../components/ui/Button'
import useAuthStore from '../../store/authStore'
import { authApi } from '../../api'
import { toast } from 'sonner'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPwd, setShowPwd] = useState(false)
  const [loading, setLoading] = useState(false)
  
  // MFA challenge state
  const [mfaRequired, setMfaRequired] = useState(false)
  const [mfaUserId, setMfaUserId] = useState(null)
  const [otpCode, setOtpCode] = useState('')
  
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)

  async function handleLogin(e) {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await authApi.login(email, password)
      const data = res.data

      if (data.mfa_required) {
        setMfaRequired(true)
        setMfaUserId(data.user_id)
        toast.info('Please enter your MFA code.')
        return
      }

      login(data.user, data.access_token)
      toast.success(`Welcome, ${data.user?.full_name || 'User'}!`)
      navigate('/')
    } catch (err) {
      const message = err.response?.data?.error?.message || 'Login failed. Please try again.'
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  async function handleMfaVerify(e) {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await authApi.mfaLoginVerify(mfaUserId, otpCode)
      const data = res.data

      login(data.user, data.access_token)
      toast.success(`Welcome! MFA verified.`)
      navigate('/')
    } catch (err) {
      const message = err.response?.data?.error?.message || 'Invalid MFA code.'
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen flex overflow-hidden">
      {/* Video Background */}
      <video
        autoPlay
        loop
        muted
        playsInline
        preload="metadata"
        className="absolute inset-0 w-full h-full object-cover"
      >
        <source src="/farmland.mp4" type="video/mp4" />
      </video>

      {/* Dark gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-forest-900/80 via-forest-800/70 to-black/60" />

      {/* Content */}
      <div className="relative z-10 flex w-full">
        {/* Left panel — branding (desktop) */}
        <div className="hidden lg:flex flex-col justify-between w-[440px] p-12 shrink-0">
          <div className="flex items-center gap-3">
            <img src="/fittree-logo.png" alt="Fittree International LLP" className="h-10 w-auto object-contain" />
            <div>
              <span className="font-heading font-bold text-white text-xl">Live-Trace</span>
              <p className="text-[11px] text-forest-200/70 font-body -mt-0.5">by Fittree International LLP</p>
            </div>
          </div>

          <div>
            <h1 className="font-heading text-4xl font-bold text-white leading-tight mb-4">
              From field<br />to fork —<br />full visibility.
            </h1>
            <p className="text-white/70 text-sm font-body leading-relaxed max-w-sm">
              Track agricultural shipments across the entire supply chain — from procurement to delivery.
            </p>
          </div>

          <div className="space-y-3">
            {[
              { title: '9-stage milestone tracking', desc: 'Real-time shipment progress' },
              { title: 'Document vault', desc: 'Secure export documentation' },
              { title: 'Quality data', desc: 'COAs, lab reports & inspections' },
              { title: 'Customer notifications', desc: 'Automated status updates' },
            ].map((f) => (
              <div key={f.title} className="flex items-start gap-3">
                <div className="w-5 h-5 rounded-full bg-forest-500/30 border border-forest-400/40 flex items-center justify-center shrink-0 mt-0.5">
                  <ChevronRight size={10} className="text-forest-300" />
                </div>
                <div>
                  <p className="text-white/90 text-sm font-medium font-heading">{f.title}</p>
                  <p className="text-white/50 text-xs font-body">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right panel — form */}
        <div className="flex-1 flex items-center justify-center p-4 md:p-8">
          <div className="w-full max-w-sm">
            {/* Mobile brand */}
            <div className="flex items-center gap-2 mb-8 lg:hidden">
              <img src="/fittree-logo.png" alt="Fittree International LLP" className="h-8 w-auto object-contain" />
              <span className="font-heading font-bold text-white text-xl">Live-Trace</span>
            </div>

            {!mfaRequired ? (
              <div className="bg-white/95 backdrop-blur-md rounded-2xl p-7 shadow-2xl border border-white/20">
                <h2 className="font-heading font-bold text-2xl text-slate-900 mb-1">Welcome back</h2>
                <p className="text-sm text-slate-500 font-body mb-6">Sign in to your account to continue.</p>

                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1.5">Email</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@fittree.com"
                      required
                      className="w-full px-3.5 py-2.5 bg-white border border-agri-200 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-700 focus:border-transparent transition font-body"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1.5">Password</label>
                    <div className="relative">
                      <input
                        type={showPwd ? 'text' : 'password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        required
                        className="w-full px-3.5 py-2.5 bg-white border border-agri-200 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-700 focus:border-transparent transition font-body pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPwd(!showPwd)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                      >
                        {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>

                  <Button type="submit" className="w-full" loading={loading}>
                    Sign in
                  </Button>
                </form>
              </div>
            ) : (
              <div className="bg-white/95 backdrop-blur-md rounded-2xl p-7 shadow-2xl border border-white/20">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="w-5 h-5 text-forest-700" />
                  <h2 className="font-heading font-bold text-2xl text-slate-900">MFA Verification</h2>
                </div>
                <p className="text-sm text-slate-500 font-body mb-6">
                  Enter the 6-digit code from your authenticator app.
                </p>

                <form onSubmit={handleMfaVerify} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1.5">Authentication Code</label>
                    <input
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]{6}"
                      maxLength={6}
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                      placeholder="000000"
                      required
                      autoFocus
                      className="w-full px-3.5 py-2.5 bg-white border border-agri-200 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-700 focus:border-transparent transition font-body text-center text-2xl tracking-[0.5em]"
                    />
                  </div>

                  <Button type="submit" className="w-full" loading={loading}>
                    Verify
                  </Button>

                  <button
                    type="button"
                    onClick={() => { setMfaRequired(false); setOtpCode('') }}
                    className="w-full text-sm text-slate-500 hover:text-slate-700 font-body"
                  >
                    ← Back to login
                  </button>
                </form>
              </div>
            )}

            <p className="text-center text-white/50 text-xs font-body mt-4 lg:hidden">
              Live-Trace by Fittree International LLP
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
