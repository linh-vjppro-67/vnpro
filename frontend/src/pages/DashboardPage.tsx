import { useEffect, useState } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AlertTriangle, Boxes, BriefcaseBusiness, CircleDollarSign, HandCoins, Headphones, TrendingUp, WalletCards } from 'lucide-react'
import { api } from '../lib/api'
import { money, number } from '../lib/format'
import type { Dashboard } from '../types'
import { PageHeader } from '../components/PageHeader'

export function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.get('/dashboard/summary').then(r=>setData(r.data)).catch(e=>setError(e.response?.data?.detail || 'Không tải được dữ liệu')) }, [])
  if (error) return <div className="error-panel">{error}</div>
  if (!data) return <div className="loading">Đang tải dashboard…</div>
  const cards = [
    ['Doanh thu xác nhận', money(data.revenue), TrendingUp, 'Từ đơn đã xác nhận/triển khai'],
    ['Lợi nhuận gộp dự kiến', money(data.gross_profit), CircleDollarSign, 'Doanh thu trừ giá vốn dự kiến'],
    ['Pipeline có trọng số', money(data.pipeline_value), BriefcaseBusiness, 'Giá trị cơ hội × xác suất'],
    ['Công nợ phải thu', money(data.open_receivables), HandCoins, `${money(data.overdue_receivables)} quá hạn`],
    ['Ngân sách đã sử dụng', `${Math.round(data.spent_budget / Math.max(data.approved_budget,1)*100)}%`, WalletCards, `${money(data.spent_budget)} / ${money(data.approved_budget)}`],
    ['Dự án đang hoạt động', number(data.active_projects), BriefcaseBusiness, 'Lập kế hoạch đến chờ nghiệm thu'],
    ['Yêu cầu CSKH mở', number(data.open_tickets), Headphones, 'Theo SLA ưu tiên'],
    ['Sản phẩm thiếu tồn', number(data.low_stock_products), Boxes, 'Dưới hoặc bằng định mức'],
  ] as const
  return <><PageHeader title="Trung tâm điều hành" description="Tổng quan bán hàng, tài chính và vận hành theo thời gian thực."/>
    <div className="kpi-grid">{cards.map(([title,value,Icon,sub])=><div className="kpi-card" key={title}><div className="kpi-icon"><Icon size={21}/></div><div><span>{title}</span><strong>{value}</strong><small>{sub}</small></div></div>)}</div>
    <div className="dashboard-grid"><section className="panel panel-wide"><div className="panel-title"><div><h3>Doanh thu 6 tháng</h3><p>Dữ liệu mẫu để thay bằng doanh thu MISA sau khi kết nối</p></div></div><div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.monthly_revenue}><defs><linearGradient id="rev" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="currentColor" stopOpacity={0.3}/><stop offset="95%" stopColor="currentColor" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="month"/><YAxis tickFormatter={v=>`${v/1e9}tỷ`}/><Tooltip formatter={(v:any)=>money(v)}/><Area type="monotone" dataKey="value" stroke="currentColor" fill="url(#rev)" strokeWidth={3}/></AreaChart></ResponsiveContainer></div></section>
      <section className="panel"><div className="panel-title"><div><h3>Phễu bán hàng</h3><p>Số lượng cơ hội theo giai đoạn</p></div></div><div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.sales_funnel} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false}/><XAxis type="number"/><YAxis dataKey="stage" type="category" width={110} tick={{fontSize:11}}/><Tooltip/><Bar dataKey="count" fill="currentColor" radius={[0,6,6,0]}/></BarChart></ResponsiveContainer></div></section>
    </div>
    <section className="panel"><div className="panel-title"><div><h3>Cảnh báo cần chú ý</h3><p>Các ngoại lệ cần Ban giám đốc và phòng ban xử lý</p></div></div><div className="alert-list">{data.alerts.map((a,i)=><div className={`alert alert-${a.level}`} key={i}><AlertTriangle size={18}/><div><strong>{a.title}</strong><span>{a.message}</span></div></div>)}</div></section>
  </>
}
