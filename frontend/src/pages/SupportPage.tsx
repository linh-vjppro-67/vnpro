import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { api } from '../lib/api'
import { date } from '../lib/format'
import { PageHeader } from '../components/PageHeader'
import { DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'

export function SupportPage() {
  const [tab, setTab] = useState<'tickets'|'warranties'>('tickets')
  const [rows, setRows] = useState<any[]>([])
  const [warranties, setWarranties] = useState<any[]>([])
  const [customers, setCustomers] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [products, setProducts] = useState<any[]>([])
  const [showTicket, setShowTicket] = useState(false)
  const [showWarranty, setShowWarranty] = useState(false)
  const [acting, setActing] = useState<{ row: any; action: string }>()
  const [error, setError] = useState('')
  const load = () => Promise.all([
    api.get('/support/tickets'), api.get('/production/warranties'), api.get('/sales/customers'),
    api.get('/sales/orders'), api.get('/inventory/products'),
  ]).then(([t, w, c, o, p]) => { setRows(t.data); setWarranties(w.data); setCustomers(c.data); setOrders(o.data); setProducts(p.data) })
  useEffect(() => { load() }, [])
  const fail = (e: any) => setError(e?.response?.data?.detail || 'Không thể xử lý yêu cầu')

  const createTicket = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); const f = new FormData(e.currentTarget)
    try {
      await api.post('/support/tickets', {
        code: f.get('code'), customer_id: Number(f.get('customer_id')), sales_order_id: f.get('sales_order_id') ? Number(f.get('sales_order_id')) : null,
        product_id: f.get('product_id') ? Number(f.get('product_id')) : null, subject: f.get('subject'),
        description: f.get('description') || null, priority: f.get('priority'),
      })
      setShowTicket(false); await load()
    } catch (e) { fail(e) }
  }
  const createWarranty = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); const f = new FormData(e.currentTarget)
    try {
      await api.post('/production/warranties', {
        code: f.get('code'), customer_id: Number(f.get('customer_id')), sales_order_id: Number(f.get('sales_order_id')),
        product_id: f.get('product_id') ? Number(f.get('product_id')) : null, serial_no: f.get('serial_no') || null,
        start_date: f.get('start_date'), end_date: f.get('end_date'), coverage: f.get('coverage'), exclusions: f.get('exclusions') || null,
      })
      setShowWarranty(false); await load()
    } catch (e) { fail(e) }
  }
  const perform = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); if (!acting) return
    const f = new FormData(e.currentTarget)
    try {
      await api.post(`/support/tickets/${acting.row.id}/${acting.action}`, { note: f.get('note') || 'Đã xử lý trên hệ thống' })
      setActing(undefined); await load()
    } catch (e) { fail(e) }
  }
  const customerName = (id: number) => customers.find(c => c.id === id)?.name || `KH #${id}`
  const orderName = (id: number) => orders.find(o => o.id === id)?.code || `SO #${id}`

  return <>
    <PageHeader title="CSKH & bảo hành" description="Quản lý SLA, điều phối xử lý, xác nhận kết quả và hồ sơ bảo hành sau bán."
      actions={<button className="primary-btn small" onClick={() => tab === 'tickets' ? setShowTicket(true) : setShowWarranty(true)}><Plus size={17}/> {tab === 'tickets' ? 'Tạo ticket' : 'Tạo bảo hành'}</button>}/>
    {error && <div className="error-panel">{error}</div>}
    <div className="tabs"><button className={tab === 'tickets' ? 'active' : ''} onClick={() => setTab('tickets')}>Ticket & SLA</button><button className={tab === 'warranties' ? 'active' : ''} onClick={() => setTab('warranties')}>Hồ sơ bảo hành</button></div>
    {tab === 'tickets' && <section className="panel"><DataTable rows={rows} columns={[
      { key: 'code', label: 'Mã phiếu' }, { key: 'subject', label: 'Yêu cầu' },
      { key: 'customer_id', label: 'Khách hàng', render: (r: any) => customerName(r.customer_id) },
      { key: 'warranty_status', label: 'Bảo hành', render: (r: any) => <StatusBadge value={r.warranty_status}/> },
      { key: 'priority', label: 'Ưu tiên', render: (r: any) => <StatusBadge value={r.priority}/> },
      { key: 'sla_due_at', label: 'Hạn SLA', render: (r: any) => date(r.sla_due_at) },
      { key: 'status', label: 'Trạng thái', render: (r: any) => <StatusBadge value={r.status}/> },
      { key: 'actions', label: '', render: (r: any) => <div style={{ display: 'flex', gap: 6 }}>
        {!['RESOLVED','CLOSED'].includes(r.status) && <button className="table-btn" onClick={() => setActing({ row: r, action: 'respond' })}>Phản hồi</button>}
        {!['RESOLVED','CLOSED'].includes(r.status) && <button className="table-btn" onClick={() => setActing({ row: r, action: 'resolve' })}>Hoàn tất</button>}
        {r.status === 'RESOLVED' && <button className="table-btn" onClick={() => setActing({ row: r, action: 'close' })}>KH xác nhận & đóng</button>}
        {r.status === 'CLOSED' && <button className="table-btn" onClick={() => setActing({ row: r, action: 'reopen' })}>Mở lại</button>}
      </div> },
    ]}/></section>}
    {tab === 'warranties' && <section className="panel"><DataTable rows={warranties} columns={[
      { key: 'code', label: 'Mã bảo hành' }, { key: 'customer_id', label: 'Khách hàng', render: (r: any) => customerName(r.customer_id) },
      { key: 'sales_order_id', label: 'Đơn hàng', render: (r: any) => orderName(r.sales_order_id) },
      { key: 'serial_no', label: 'Serial' }, { key: 'start_date', label: 'Từ ngày', render: (r: any) => date(r.start_date) },
      { key: 'end_date', label: 'Đến ngày', render: (r: any) => date(r.end_date) }, { key: 'status', label: 'Trạng thái', render: (r: any) => <StatusBadge value={r.status}/> },
    ]}/></section>}
    {showTicket && <div className="modal-backdrop" onMouseDown={() => setShowTicket(false)}><form className="modal" onSubmit={createTicket} onMouseDown={e => e.stopPropagation()}><h3>Tạo yêu cầu CSKH</h3><div className="form-grid">
      <label>Mã phiếu<input name="code" required placeholder="CS-2026-073"/></label>
      <label>Khách hàng<select name="customer_id" required>{customers.map(c => <option value={c.id} key={c.id}>{c.name}</option>)}</select></label>
      <label>Đơn hàng<select name="sales_order_id" defaultValue=""><option value="">Không liên kết</option>{orders.map(o => <option value={o.id} key={o.id}>{o.code}</option>)}</select></label>
      <label>Sản phẩm<select name="product_id" defaultValue=""><option value="">Không xác định</option>{products.map(p => <option value={p.id} key={p.id}>{p.sku} — {p.name}</option>)}</select></label>
      <label className="full">Tiêu đề<input name="subject" required/></label><label className="full">Mô tả<textarea name="description" required/></label>
      <label>Ưu tiên<select name="priority"><option value="LOW">Thấp · 48 giờ</option><option value="MEDIUM">Trung bình · 24 giờ</option><option value="HIGH">Cao · 4 giờ</option><option value="CRITICAL">Khẩn cấp · 2 giờ</option></select></label>
    </div><div className="modal-actions"><button type="button" className="ghost-btn" onClick={() => setShowTicket(false)}>Hủy</button><button className="primary-btn">Tạo phiếu</button></div></form></div>}
    {showWarranty && <div className="modal-backdrop" onMouseDown={() => setShowWarranty(false)}><form className="modal" onSubmit={createWarranty} onMouseDown={e => e.stopPropagation()}><h3>Tạo hồ sơ bảo hành</h3><div className="form-grid">
      <label>Mã bảo hành<input name="code" required placeholder="BH-2026-001"/></label><label>Khách hàng<select name="customer_id" required>{customers.map(c => <option value={c.id} key={c.id}>{c.name}</option>)}</select></label>
      <label>Đơn hàng<select name="sales_order_id" required>{orders.map(o => <option value={o.id} key={o.id}>{o.code}</option>)}</select></label>
      <label>Sản phẩm<select name="product_id" defaultValue=""><option value="">Toàn bộ đơn</option>{products.map(p => <option value={p.id} key={p.id}>{p.sku} — {p.name}</option>)}</select></label>
      <label>Serial<input name="serial_no"/></label><label>Ngày bắt đầu<input name="start_date" type="date" required/></label><label>Ngày hết hạn<input name="end_date" type="date" required/></label>
      <label className="full">Phạm vi bảo hành<textarea name="coverage" required/></label><label className="full">Điều khoản loại trừ<textarea name="exclusions"/></label>
    </div><div className="modal-actions"><button type="button" className="ghost-btn" onClick={() => setShowWarranty(false)}>Hủy</button><button className="primary-btn">Lưu hồ sơ</button></div></form></div>}
    {acting && <div className="modal-backdrop" onMouseDown={() => setActing(undefined)}><form className="modal" onSubmit={perform} onMouseDown={e => e.stopPropagation()}><h3>Xử lý {acting.row.code}</h3><label>Kết quả/ghi chú<textarea name="note" required autoFocus/></label><div className="modal-actions"><button type="button" className="ghost-btn" onClick={() => setActing(undefined)}>Hủy</button><button className="primary-btn">Xác nhận</button></div></form></div>}
  </>
}
