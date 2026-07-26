import { NavLink, Outlet } from 'react-router-dom'
import { Boxes, Building2, CircleDollarSign, ClipboardList, HandCoins, Headphones, LayoutDashboard, LogOut, ShoppingCart, UsersRound, Wrench, Workflow } from 'lucide-react'
import { useAuth } from './AuthContext'
import { can } from '../lib/permissions'

const nav = [
  ['/', 'Tổng quan', LayoutDashboard, 'dashboard'], ['/order-flow', 'Luồng đơn hàng', Workflow, 'sales:r'], ['/sales', 'CRM & Bán hàng', ShoppingCart, 'sales:r'], ['/tasks', 'Công việc', ClipboardList, 'dashboard'], ['/costs', 'Chi phí & ngân sách', CircleDollarSign, 'cost:r'],
  ['/operations', 'Vận hành kỹ thuật', Wrench, 'operations:r'], ['/inventory', 'Kho hàng', Boxes, 'inventory:r'], ['/finance', 'Công nợ', HandCoins, 'finance:r'],
  ['/support', 'CSKH & bảo hành', Headphones, 'support:r'], ['/organization', 'Tổ chức', UsersRound, 'organization'],
] as const

export function Layout() {
  const { user, logout } = useAuth()
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">VNPRO</div><div><strong>Enterprise Hub</strong><small>Cân điện tử & giải pháp</small></div></div>
      <nav>{nav.filter(([, , , permission])=>can(user?.role,permission)).map(([to, text, Icon]) => <NavLink key={to} to={to} end={to === '/'}><Icon size={19}/><span>{text}</span></NavLink>)}</nav>
      <div className="sidebar-footer"><div className="user-card"><div className="avatar">{user?.full_name?.slice(0,1)}</div><div><strong>{user?.full_name}</strong><small>{user?.department} · {user?.role}</small></div></div><button className="icon-btn" onClick={logout} title="Đăng xuất"><LogOut size={18}/></button></div>
    </aside>
    <main className="main"><header className="topbar"><div><Building2 size={18}/> Công ty Cổ phần Giải pháp và Công nghệ Cân điện tử Pro Việt Nam</div><div className="top-actions"><span className="live-dot"/> Dữ liệu demo đang hoạt động</div></header><div className="content"><Outlet/></div></main>
  </div>
}
