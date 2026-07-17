import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { api } from '../../lib/api'
import { money } from '../../lib/format'
import { DataTable } from '../../components/DataTable'
import { StatusBadge } from '../../components/StatusBadge'
import { useAuth } from '../../components/AuthContext'

type Installment = { description: string; amount: number; due_condition: string }
const emptyInstallment: Installment = { description: '', amount: 0, due_condition: '' }

export function ContractsTab({ customers, quotations }: {customers: any[]; quotations: any[]}) {
  const { user } = useAuth()
  const canApprove = ['DIRECTOR','SYSTEM_ADMIN'].includes(user?.role || '')
  const [rows, setRows] = useState<any[]>([]); const [loading, setLoading] = useState(false); const [show, setShow] = useState(false)
  const [signing, setSigning] = useState<any>(null); const [ordering, setOrdering] = useState<any>(null)
  const [schedule, setSchedule] = useState<Installment[]>([{ ...emptyInstallment }])
  const load = () => { setLoading(true); api.get('/crm/contracts').then(r => setRows(r.data)).finally(() => setLoading(false)) }
  useEffect(() => { load() }, [])
  const updateRow = (idx: number, patch: Partial<Installment>) => setSchedule(schedule.map((s, i) => i === idx ? { ...s, ...patch } : s))
  const create = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); const f = new FormData(e.currentTarget)
    await api.post('/crm/contracts', { code: f.get('code'), customer_id: Number(f.get('customer_id')), quotation_id: f.get('quotation_id') ? Number(f.get('quotation_id')) : null, total_value: Number(f.get('total_value')), warranty_terms: f.get('warranty_terms') || null, payment_schedule: schedule })
    setShow(false); setSchedule([{ ...emptyInstallment }]); load()
  }
  const action = async (id: number, path: string, body: any = {}) => { await api.post(`/crm/contracts/${id}/${path}`, body); load() }
  const sign = async (e: React.FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); await api.post(`/crm/contracts/${signing.id}/sign`, Object.fromEntries(f)); setSigning(null); load() }
  const generateOrder = async (e: React.FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); await api.post(`/crm/contracts/${ordering.id}/generate-sales-order`, Object.fromEntries(f)); setOrdering(null); load() }
  const customerName = (id: number) => customers.find(c => c.id === id)?.name || id
  const columns: any = [
    {key:'code',label:'Mã hợp đồng'},
    {key:'customer_id',label:'Khách hàng',render:(r:any)=>customerName(r.customer_id)},
    {key:'total_value',label:'Giá trị',render:(r:any)=>money(r.total_value)},
    {key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>},
    {key:'sales_order_id',label:'Đơn hàng',render:(r:any)=>r.sales_order_id?`#${r.sales_order_id}`:'—'},
    {key:'actions',label:'',render:(r:any)=><div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
      {r.status==='DRAFT' && <button className="table-btn" onClick={()=>action(r.id,'submit')}>Gửi duyệt</button>}
      {r.status==='INTERNAL_REVIEW' && canApprove && <button className="table-btn" onClick={()=>action(r.id,'approve')}>Duyệt</button>}
      {r.status==='INTERNAL_REVIEW' && canApprove && <button className="table-btn" onClick={()=>action(r.id,'reject')}>Từ chối</button>}
      {r.status==='APPROVED' && <button className="table-btn" onClick={()=>action(r.id,'send-for-signature')}>Gửi ký</button>}
      {r.status==='SENT_FOR_SIGNATURE' && <button className="table-btn" onClick={()=>setSigning(r)}>Xác nhận đã ký</button>}
      {r.status==='SIGNED' && <button className="table-btn" onClick={()=>setOrdering(r)}>Tạo đơn hàng</button>}
    </div>},
  ]
  return <>
    <div className="toolbar"><span>{rows.length} hợp đồng</span><button className="primary-btn small" onClick={()=>setShow(true)}><Plus size={15}/> Tạo hợp đồng</button></div>
    {loading ? <div className="loading">Đang tải…</div> : <div className="panel"><DataTable rows={rows} columns={columns}/></div>}
    {show && <div className="modal-backdrop" onMouseDown={()=>setShow(false)}><form className="modal" onSubmit={create} onMouseDown={e=>e.stopPropagation()}>
      <h3>Tạo hợp đồng</h3>
      <div className="form-grid">
        <label>Mã hợp đồng<input name="code" required placeholder="HD-2026-010"/></label>
        <label>Khách hàng<select name="customer_id" required defaultValue="">
          <option value="" disabled>Chọn khách hàng</option>
          {customers.map(c=><option key={c.id} value={c.id}>{c.code} — {c.name}</option>)}
        </select></label>
        <label>Báo giá liên quan<select name="quotation_id" defaultValue="">
          <option value="">Không có</option>
          {quotations.map(q=><option key={q.id} value={q.id}>{q.code} — {money(q.total_amount)}</option>)}
        </select></label>
        <label>Giá trị hợp đồng<input name="total_value" type="number" min="0" required/></label>
        <label className="full">Bảo hành<input name="warranty_terms"/></label>
      </div>
      <h3>Lịch thanh toán</h3>
      {schedule.map((s,idx)=><div key={idx} className="form-grid" style={{gridTemplateColumns:'2fr 1fr 1fr auto',alignItems:'end'}}>
        <label>Mô tả<input value={s.description} onChange={e=>updateRow(idx,{description:e.target.value})} required/></label>
        <label>Số tiền<input type="number" min={0} value={s.amount} onChange={e=>updateRow(idx,{amount:Number(e.target.value)})}/></label>
        <label>Điều kiện<input value={s.due_condition} onChange={e=>updateRow(idx,{due_condition:e.target.value})} placeholder="Khi ký hợp đồng"/></label>
        <button type="button" className="ghost-btn" onClick={()=>setSchedule(schedule.filter((_,i)=>i!==idx))} disabled={schedule.length===1}><Trash2 size={15}/></button>
      </div>)}
      <button type="button" className="ghost-btn" onClick={()=>setSchedule([...schedule,{...emptyInstallment}])}><Plus size={15}/> Thêm đợt thanh toán</button>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setShow(false)}>Hủy</button><button className="primary-btn">Lưu hợp đồng</button></div>
    </form></div>}
    {signing && <div className="modal-backdrop" onMouseDown={()=>setSigning(null)}><form className="modal" onSubmit={sign} onMouseDown={e=>e.stopPropagation()}>
      <h3>Xác nhận đã ký hợp đồng {signing.code}</h3>
      <div className="form-grid"><label className="full">Người ký<input name="signed_by" required/></label></div>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setSigning(null)}>Hủy</button><button className="primary-btn">Xác nhận</button></div>
    </form></div>}
    {ordering && <div className="modal-backdrop" onMouseDown={()=>setOrdering(null)}><form className="modal" onSubmit={generateOrder} onMouseDown={e=>e.stopPropagation()}>
      <h3>Tạo đơn hàng từ hợp đồng {ordering.code}</h3>
      <div className="form-grid">
        <label>Mã đơn hàng<input name="code" required placeholder="DH-2026-010"/></label>
        <label>Tiêu đề<input name="title" placeholder={`Theo hợp đồng ${ordering.code}`}/></label>
      </div>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setOrdering(null)}>Hủy</button><button className="primary-btn">Tạo đơn hàng</button></div>
    </form></div>}
  </>
}
