import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Truck, Eye, EyeOff, Shield } from 'lucide-react'
import Button from '../../components/ui/Button'
import useAuthStore from '../../store/authStore'
import { authApi } from '../../api'
import { toast } from 'sonner'

// Demo credentials helper (pre-fills form only — actual auth goes through backend)
const DEMO = [
  { label: 'Admin',     email: 'admin@livetrace.com',     password: 'Admin@123',    role: 'ADMIN'     },
  { label: 'Customer',  email: 'client1@spiceworld.com',   password: 'Admin@123',    role: 'CUSTOMER'  },
  { label: 'Warehouse', email: 'warehouse@livetrace.com',  password: 'Admin@123',    role: 'WAREHOUSE' },
]

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

      // Check if MFA is required
      if (data.mfa_required) {
        setMfaRequired(true)
        setMfaUserId(data.user_id)
        toast.info('Please enter your MFA code.')
        return
      }

      // Successful login — access token in response, refresh token in cookie
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
    <div className="min-h-screen bg-beige-100 flex">
      {/* Left panel — branding */}
      <div className="hidden lg:flex flex-col justify-between w-[420px] bg-gradient-to-br from-cinnamon-700 via-saffron-700 to-saffron-500 p-12 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
            <Truck className="w-5 h-5 text-white" />
          </div>
          <span className="font-heading font-bold text-white text-xl">Live-Trace</span>
        </div>

        <div>
          <h1 className="font-heading text-4xl font-bold text-white leading-tight mb-4">
            Track every<br />spice shipment<br />in real time.
          </h1>
          <p className="text-white/70 text-sm font-body leading-relaxed">
            From procurement to delivery — complete visibility for your export operations.
          </p>
        </div>

        <div className="space-y-3">
          {['9-stage milestone tracking', 'Document vault', 'QA reports & quality data', 'Customer notifications'].map((f) => (
            <div key={f} className="flex items-center gap-2 text-white/80 text-sm font-body">
              <div className="w-1.5 h-1.5 rounded-full bg-saffron-200" />
              {f}
            </div>
          ))}
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          {/* Mobile brand */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-9 h-9 rounded-xl bg-saffron-500 flex items-center justify-center">
              <Truck className="w-5 h-5 text-white" />
            </div>
            <span className="font-heading font-bold text-gray-900 text-xl">Live-Trace</span>
          </div>

          {!mfaRequired ? (
            <>
              <h2 className="font-heading font-bold text-2xl text-gray-900 mb-1">Sign in</h2>
              <p className="text-sm text-gray-500 font-body mb-7">Enter your credentials to continue.</p>

              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Email address</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@live-trace.com"
                    required
                    className="w-full px-3.5 py-2.5 bg-white border border-beige-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-saffron-500 focus:border-transparent transition font-body"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Password</label>
                  <div className="relative">
                    <input
                      type={showPwd ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="w-full px-3.5 py-2.5 bg-white border border-beige-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-saffron-500 focus:border-transparent transition font-body pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPwd(!showPwd)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <Button type="submit" className="w-full" loading={loading}>
                  Sign in
                </Button>
              </form>

              {/* Demo quick-fill */}
              <div className="mt-6 pt-5 border-t border-beige-200">
                <p className="text-[11px] text-gray-400 mb-2 text-center font-body uppercase tracking-wide">Demo credentials</p>
                <div className="flex gap-2 flex-wrap justify-center">
                  {DEMO.map((d) => (
                    <button
                      key={d.role}
                      onClick={() => { setEmail(d.email); setPassword(d.password) }}
                      className="text-[11px] px-2.5 py-1 rounded-full bg-beige-100 text-gray-600 hover:bg-saffron-50 hover:text-saffron-700 border border-beige-200 font-body transition-colors"
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <>
              {/* MFA Challenge */}
              <div className="flex items-center gap-2 mb-2">
                <Shield className="w-5 h-5 text-saffron-600" />
                <h2 className="font-heading font-bold text-2xl text-gray-900">MFA Verification</h2>
              </div>
              <p className="text-sm text-gray-500 font-body mb-7">
                Enter the 6-digit code from your authenticator app.
              </p>

              <form onSubmit={handleMfaVerify} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Authentication Code</label>
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
                    className="w-full px-3.5 py-2.5 bg-white border border-beige-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-saffron-500 focus:border-transparent transition font-body text-center text-2xl tracking-[0.5em]"
                  />
                </div>

                <Button type="submit" className="w-full" loading={loading}>
                  Verify
                </Button>

                <button
                  type="button"
                  onClick={() => { setMfaRequired(false); setOtpCode('') }}
                  className="w-full text-sm text-gray-500 hover:text-gray-700 font-body"
                >
                  ← Back to login
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
