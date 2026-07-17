import { NavLink, Outlet } from 'react-router-dom'
import { BarChart3, Boxes, Building2, CircleDollarSign, ClipboardList, HandCoins, Headphones, LayoutDashboard, LogOut, RefreshCw, Settings, ShoppingCart, UsersRound, Wrench } from 'lucide-react'
import { useAuth } from './AuthContext'

const nav = [
  ['/', 'Tổng quan', LayoutDashboard], ['/sales', 'Bán hàng & CRM', ShoppingCart], ['/tasks', 'Công việc', ClipboardList], ['/costs', 'Chi phí & ngân sách', CircleDollarSign],
  ['/operations', 'Vận hành kỹ thuật', Wrench], ['/inventory', 'Kho hàng', Boxes], ['/finance', 'Công nợ', HandCoins],
  ['/support', 'CSKH & bảo hành', Headphones], ['/organization', 'Tổ chức & phân quyền', UsersRound],
] as const

export function Layout() {
  const { user, logout } = useAuth()
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">PRO</div><div><strong>Enterprise Hub</strong><small>Cân điện tử & giải pháp</small></div></div>
      <nav>{nav.map(([to, text, Icon]) => <NavLink key={to} to={to} end={to === '/'}><Icon size={19}/><span>{text}</span></NavLink>)}</nav>
      <div className="sidebar-footer"><div className="user-card"><div className="avatar">{user?.full_name?.slice(0,1)}</div><div><strong>{user?.full_name}</strong><small>{user?.department} · {user?.role}</small></div></div><button className="icon-btn" onClick={logout} title="Đăng xuất"><LogOut size={18}/></button></div>
    </aside>
    <main className="main"><header className="topbar"><div><Building2 size={18}/> Công ty TNHH Cân Điện Tử Pro Việt Nam</div><div className="top-actions"><span className="live-dot"/> Dữ liệu demo đang hoạt động</div></header><div className="content"><Outlet/></div></main>
  </div>
}
