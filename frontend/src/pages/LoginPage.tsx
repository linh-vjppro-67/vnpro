import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { LockKeyhole, Scale, ShieldCheck } from 'lucide-react'
import { useAuth } from '../components/AuthContext'

const accounts = [
  ['Ban giám đốc', 'director@proscale.vn'], ['Kinh doanh', 'sales@proscale.vn'], ['Kế toán', 'accounting@proscale.vn'],
  ['Kho', 'warehouse@proscale.vn'], ['Kỹ thuật', 'technical@proscale.vn'], ['Quản trị', 'admin@proscale.vn']
]

export function LoginPage() {
  const { user, login } = useAuth()
  const [email, setEmail] = useState('director@proscale.vn')
  const [password, setPassword] = useState('Demo@123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  if (user) return <Navigate to="/" replace/>
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setLoading(true); setError('')
    try { await login(email, password) } catch (err: any) { setError(err.response?.data?.detail || 'Không thể đăng nhập') } finally { setLoading(false) }
  }
  return <div className="login-page"><section className="login-hero"><div className="hero-logo"><Scale size={32}/><span>PRO Enterprise Hub</span></div><h1>Một nơi để điều hành toàn bộ doanh nghiệp.</h1><p>Theo dõi bán hàng, chi phí, dự án kỹ thuật, kho, công nợ và chăm sóc khách hàng trên cùng một nền tảng.</p><div className="hero-points"><div><ShieldCheck/> Phân quyền theo phòng ban</div><div><LockKeyhole/> Audit log và kiểm soát dữ liệu</div></div></section>
    <section className="login-panel"><form className="login-card" onSubmit={submit}><div><span className="eyebrow">HỆ THỐNG QUẢN TRỊ TỔNG THỂ</span><h2>Đăng nhập</h2><p>Sử dụng tài khoản demo hoặc tài khoản được cấp.</p></div>
      <label>Email<input value={email} onChange={e=>setEmail(e.target.value)} type="email" required/></label><label>Mật khẩu<input value={password} onChange={e=>setPassword(e.target.value)} type="password" required/></label>
      {error && <div className="form-error">{error}</div>}<button className="primary-btn" disabled={loading}>{loading ? 'Đang đăng nhập…' : 'Đăng nhập'}</button>
      <div className="demo-accounts"><strong>Tài khoản demo · Mật khẩu: Demo@123</strong>{accounts.map(([name, mail]) => <button type="button" key={mail} onClick={()=>setEmail(mail)}><span>{name}</span><small>{mail}</small></button>)}</div>
    </form></section></div>
}
