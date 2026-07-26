import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { money, date } from '../lib/format'
import { PageHeader } from '../components/PageHeader'
import { DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'

export function FinancePage() {
  const [rows, setRows] = useState<any[]>([])
  const [customers, setCustomers] = useState<any[]>([])
  const [collections, setCollections] = useState<any[]>([])
  const [selected, setSelected] = useState<any>()
  const [mode, setMode] = useState<'collect'|'payment'>('collect')
  const [error, setError] = useState('')
  const load = () => Promise.all([api.get('/finance/receivables'), api.get('/production/collections'), api.get('/sales/customers')])
    .then(([r, c, customers]) => { setRows(r.data); setCollections(c.data); setCustomers(customers.data) })
  useEffect(() => { load() }, [])
  const total = rows.reduce((s, r) => s + Number(r.amount) - Number(r.paid_amount), 0)
  const overdue = rows.filter(r => new Date(r.due_date) < new Date() && r.status !== 'PAID').reduce((s, r) => s + Number(r.amount) - Number(r.paid_amount), 0)
  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); const f = new FormData(e.currentTarget)
    try {
      if (mode === 'payment') await api.patch(`/finance/receivables/${selected.id}/payment`, {
        paid_amount: Number(f.get('paid_amount')), code: f.get('code'), received_date: f.get('received_date'),
        method: f.get('method'), transaction_ref: f.get('transaction_ref') || null,
      })
      else await api.post(`/production/receivables/${selected.id}/collections`, {
        channel: f.get('channel'), result: f.get('result'), promised_date: f.get('promised_date') || null,
        promised_amount: f.get('promised_amount') ? Number(f.get('promised_amount')) : null, next_follow_up: f.get('next_follow_up') || null,
      })
      setSelected(undefined); await load()
    } catch (e: any) { setError(e?.response?.data?.detail || 'Không thể ghi nhận') }
  }
  const customerName = (id: number) => customers.find(c => c.id === id)?.name || `KH #${id}`
  return <>
    <PageHeader title="Công nợ & tài chính" description="Theo dõi hóa đơn, phải thu, lịch nhắc nợ, cam kết và thu tiền."/>
    {error && <div className="error-panel">{error}</div>}
    <div className="finance-cards"><div><span>Tổng phải thu</span><b>{money(total)}</b></div><div className="danger"><span>Quá hạn</span><b>{money(overdue)}</b></div><div><span>Tỷ lệ thu hồi</span><b>{Math.round(rows.reduce((s,r)=>s+Number(r.paid_amount),0)/Math.max(1,rows.reduce((s,r)=>s+Number(r.amount),0))*100)}%</b></div></div>
    <section className="panel"><DataTable rows={rows} columns={[
      { key: 'invoice_no', label: 'Số hóa đơn' }, { key: 'customer_id', label: 'Khách hàng', render: (r: any) => customerName(r.customer_id) },
      { key: 'amount', label: 'Giá trị', render: (r: any) => money(r.amount) }, { key: 'paid_amount', label: 'Đã thu', render: (r: any) => money(r.paid_amount) },
      { key: 'remaining', label: 'Còn lại', render: (r: any) => money(Number(r.amount) - Number(r.paid_amount)) },
      { key: 'due_date', label: 'Hạn', render: (r: any) => date(r.due_date) }, { key: 'status', label: 'Trạng thái', render: (r: any) => <StatusBadge value={r.status}/> },
      { key: 'actions', label: '', render: (r: any) => r.status !== 'PAID' && <div style={{ display: 'flex', gap: 6 }}><button className="table-btn" onClick={() => { setSelected(r); setMode('collect') }}>Nhắc nợ</button><button className="table-btn" onClick={() => { setSelected(r); setMode('payment') }}>Thu tiền</button></div> },
    ]}/></section>
    <section className="panel"><div className="panel-title"><div><h3>Nhật ký thu hồi công nợ</h3><p>Lịch sử liên hệ và cam kết thanh toán</p></div></div><DataTable rows={collections} columns={[
      { key: 'receivable_id', label: 'Khoản phải thu', render: (r: any) => rows.find(x => x.id === r.receivable_id)?.invoice_no || `#${r.receivable_id}` },
      { key: 'activity_date', label: 'Ngày liên hệ', render: (r: any) => date(r.activity_date) }, { key: 'channel', label: 'Kênh' },
      { key: 'result', label: 'Kết quả' }, { key: 'promised_date', label: 'Ngày cam kết', render: (r: any) => date(r.promised_date) },
      { key: 'promised_amount', label: 'Số cam kết', render: (r: any) => r.promised_amount ? money(r.promised_amount) : '—' },
      { key: 'next_follow_up', label: 'Nhắc tiếp', render: (r: any) => date(r.next_follow_up) },
    ]}/></section>
    {selected && <div className="modal-backdrop" onMouseDown={() => setSelected(undefined)}><form className="modal" onSubmit={submit} onMouseDown={e => e.stopPropagation()}><h3>{mode === 'payment' ? 'Ghi nhận thu tiền' : 'Cập nhật nhắc nợ'} · {selected.invoice_no}</h3>
      {mode === 'payment' ? <div className="form-grid"><label>Mã phiếu thu<input name="code" required placeholder="PT-2026-001"/></label><label>Ngày thu<input name="received_date" type="date" required defaultValue={new Date().toISOString().slice(0,10)}/></label><label>Số tiền thu<input name="paid_amount" type="number" min="1" max={Number(selected.amount)-Number(selected.paid_amount)} required/></label><label>Phương thức<select name="method"><option value="BANK_TRANSFER">Chuyển khoản</option><option value="CASH">Tiền mặt</option></select></label><label className="full">Mã giao dịch<input name="transaction_ref"/></label></div> :
      <div className="form-grid"><label>Kênh liên hệ<select name="channel"><option>Điện thoại</option><option>Email</option><option>Zalo</option><option>Đối chiếu trực tiếp</option></select></label>
        <label className="full">Kết quả<textarea name="result" required/></label><label>Ngày khách cam kết<input name="promised_date" type="date"/></label>
        <label>Số tiền cam kết<input name="promised_amount" type="number" min="0"/></label><label>Ngày liên hệ tiếp<input name="next_follow_up" type="date"/></label></div>}
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={() => setSelected(undefined)}>Hủy</button><button className="primary-btn">Ghi nhận</button></div>
    </form></div>}
  </>
}
