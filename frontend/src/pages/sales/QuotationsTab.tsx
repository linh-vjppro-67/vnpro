import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { api } from '../../lib/api'
import { money } from '../../lib/format'
import { DataTable } from '../../components/DataTable'
import { StatusBadge } from '../../components/StatusBadge'
import { useAuth } from '../../components/AuthContext'

type Item = { product_id?: number; name: string; quantity: number; unit: string; unit_price: number; discount_percent: number; tax_rate: number; estimated_cost: number }
const emptyItem: Item = { name: '', quantity: 1, unit: 'Cái', unit_price: 0, discount_percent: 0, tax_rate: 10, estimated_cost: 0 }

export function QuotationsTab({ opportunities, customers, products }: {opportunities: any[]; customers: any[]; products: any[]}) {
  const { user } = useAuth()
  const canApprove = ['DIRECTOR','SYSTEM_ADMIN','SALES_ADMIN'].includes(user?.role || '')
  const [rows, setRows] = useState<any[]>([]); const [loading, setLoading] = useState(false); const [show, setShow] = useState(false)
  const [items, setItems] = useState<Item[]>([{ ...emptyItem }])
  const load = () => { setLoading(true); api.get('/crm/quotations').then(r => setRows(r.data)).finally(() => setLoading(false)) }
  useEffect(() => { load() }, [])
  const total = items.reduce((s, i) => s + i.quantity * i.unit_price * (1 - i.discount_percent / 100) * (1+i.tax_rate/100), 0)
  const cost = items.reduce((s,i)=>s+i.quantity*i.estimated_cost,0)
  const updateItem = (idx: number, patch: Partial<Item>) => setItems(items.map((it, i) => i === idx ? { ...it, ...patch } : it))
  const create = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); const f = new FormData(e.currentTarget)
    await api.post('/crm/quotations', { code: f.get('code'), opportunity_id: Number(f.get('opportunity_id')), customer_id: Number(f.get('customer_id')), valid_until:f.get('valid_until'), payment_terms: f.get('payment_terms') || null, warranty_terms: f.get('warranty_terms') || null, delivery_terms: f.get('delivery_terms') || null, items })
    setShow(false); setItems([{ ...emptyItem }]); load()
  }
  const action = async (id: number, path: string, body: any = {}) => { await api.post(`/crm/quotations/${id}/${path}`, body); load() }
  const customerName = (id: number) => customers.find(c => c.id === id)?.name || id
  const columns: any = [
    {key:'code',label:'Mã báo giá'},
    {key:'version_no',label:'Version',render:(r:any)=>`V${r.version_no}`},
    {key:'customer_id',label:'Khách hàng',render:(r:any)=>customerName(r.customer_id)},
    {key:'total_amount',label:'Giá trị',render:(r:any)=>money(r.total_amount)},
    {key:'margin_percent',label:'Margin',render:(r:any)=>`${Number(r.margin_percent).toFixed(1)}%`},
    {key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>},
    {key:'actions',label:'',render:(r:any)=><div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
      {r.status==='DRAFT' && <button className="table-btn" onClick={()=>action(r.id,'submit')}>Gửi duyệt</button>}
      {r.status==='SUBMITTED' && canApprove && <button className="table-btn" onClick={()=>action(r.id,'approve')}>Duyệt</button>}
      {r.status==='SUBMITTED' && canApprove && <button className="table-btn" onClick={()=>action(r.id,'reject')}>Từ chối</button>}
      {r.status==='APPROVED' && <button className="table-btn" onClick={()=>action(r.id,'send')}>Gửi khách hàng</button>}
      {r.status==='SENT_TO_CUSTOMER' && <button className="table-btn" onClick={()=>action(r.id,'convert-to-contract')}>Tạo hợp đồng</button>}
      {r.status!=='DRAFT' && <button className="table-btn" onClick={()=>action(r.id,'clone')}>Tạo version mới</button>}
    </div>},
  ]
  return <>
    <div className="toolbar"><span>{rows.length} báo giá</span><button className="primary-btn small" onClick={()=>setShow(true)}><Plus size={15}/> Tạo báo giá</button></div>
    {loading ? <div className="loading">Đang tải…</div> : <div className="panel"><DataTable rows={rows} columns={columns}/></div>}
    {show && <div className="modal-backdrop" onMouseDown={()=>setShow(false)}><form className="modal" onSubmit={create} onMouseDown={e=>e.stopPropagation()}>
      <h3>Tạo báo giá</h3>
      <div className="form-grid">
        <label>Mã báo giá<input name="code" required placeholder="BG-2026-010"/></label>
        <label>Cơ hội<select name="opportunity_id" required defaultValue="">
          <option value="" disabled>Chọn cơ hội</option>
          {opportunities.map(o=><option key={o.id} value={o.id}>{o.code} — {o.title}</option>)}
        </select></label>
        <label>Khách hàng<select name="customer_id" required defaultValue="">
          <option value="" disabled>Chọn khách hàng</option>
          {customers.map(c=><option key={c.id} value={c.id}>{c.code} — {c.name}</option>)}
        </select></label>
        <label>Hiệu lực đến<input name="valid_until" type="date" required/></label>
        <label>Điều khoản thanh toán<input name="payment_terms"/></label>
        <label>Bảo hành<input name="warranty_terms"/></label>
        <label>Giao hàng<input name="delivery_terms"/></label>
      </div>
      <h3>Hạng mục</h3>
      {items.map((it,idx)=><div key={idx} className="form-grid" style={{gridTemplateColumns:'2fr 1fr 1fr 1fr 1fr auto',alignItems:'end'}}>
        <label>Sản phẩm<select value={it.product_id||''} required onChange={e=>{const p=products.find(x=>x.id===Number(e.target.value));updateItem(idx,{product_id:p.id,name:p.name,unit:p.unit,unit_price:Number(p.sale_price),estimated_cost:Number(p.cost_price)})}}><option value="">Chọn hàng</option>{products.map(p=><option value={p.id} key={p.id}>{p.sku} · {p.name}</option>)}</select></label>
        <label>SL<input type="number" min={1} value={it.quantity} onChange={e=>updateItem(idx,{quantity:Number(e.target.value)})}/></label>
        <label>Đơn giá<input type="number" min={0} value={it.unit_price} onChange={e=>updateItem(idx,{unit_price:Number(e.target.value)})}/></label>
        <label>Giá vốn<input type="number" min={0} value={it.estimated_cost} onChange={e=>updateItem(idx,{estimated_cost:Number(e.target.value)})}/></label>
        <label>Chiết khấu %<input type="number" min={0} max={100} value={it.discount_percent} onChange={e=>updateItem(idx,{discount_percent:Number(e.target.value)})}/></label>
        <label>VAT %<input type="number" min={0} max={100} value={it.tax_rate} onChange={e=>updateItem(idx,{tax_rate:Number(e.target.value)})}/></label>
        <button type="button" className="ghost-btn" onClick={()=>setItems(items.filter((_,i)=>i!==idx))} disabled={items.length===1}><Trash2 size={15}/></button>
      </div>)}
      <button type="button" className="ghost-btn" onClick={()=>setItems([...items,{...emptyItem}])}><Plus size={15}/> Thêm hạng mục</button>
      <p>Tổng sau thuế: <strong>{money(total)}</strong> · Giá vốn: <strong>{money(cost)}</strong> · Margin: <strong>{total?((total-cost)/total*100).toFixed(1):0}%</strong></p>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setShow(false)}>Hủy</button><button className="primary-btn">Lưu báo giá</button></div>
    </form></div>}
  </>
}
