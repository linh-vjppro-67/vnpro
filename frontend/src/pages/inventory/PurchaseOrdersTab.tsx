import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { api } from '../../lib/api'
import { money, date } from '../../lib/format'
import { DataTable } from '../../components/DataTable'
import { StatusBadge } from '../../components/StatusBadge'

type Item = { product_id: number | ''; quantity: number; unit_price: number }
const emptyItem: Item = { product_id: '', quantity: 1, unit_price: 0 }

export function PurchaseOrdersTab({ products, suppliers, onChange }: {products: any[]; suppliers: any[]; onChange?: () => void}) {
  const [rows, setRows] = useState<any[]>([]); const [loading, setLoading] = useState(false); const [show, setShow] = useState(false)
  const [items, setItems] = useState<Item[]>([{ ...emptyItem }])
  const load = () => { setLoading(true); api.get('/purchasing/orders').then(r => setRows(r.data)).finally(() => setLoading(false)) }
  useEffect(() => { load() }, [])
  const updateItem = (idx: number, patch: Partial<Item>) => setItems(items.map((it, i) => i === idx ? { ...it, ...patch } : it))
  const create = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); const f = new FormData(e.currentTarget)
    await api.post('/purchasing/orders', { code: f.get('code'), supplier_id: Number(f.get('supplier_id')), expected_delivery_date: f.get('expected_delivery_date') || null, items: items.map(i=>({...i, product_id: Number(i.product_id)})) })
    setShow(false); setItems([{ ...emptyItem }]); load()
  }
  const action = async (id: number, path: string) => { await api.post(`/purchasing/orders/${id}/${path}`); load(); onChange?.() }
  const supplierName = (id: number) => suppliers.find(s => s.id === id)?.name || id
  const columns: any = [
    {key:'code',label:'Mã đơn mua'},
    {key:'supplier_id',label:'Nhà cung cấp',render:(r:any)=>supplierName(r.supplier_id)},
    {key:'total_amount',label:'Giá trị',render:(r:any)=>money(r.total_amount)},
    {key:'expected_delivery_date',label:'Ngày giao dự kiến',render:(r:any)=>date(r.expected_delivery_date)},
    {key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>},
    {key:'actions',label:'',render:(r:any)=><div style={{display:'flex',gap:6}}>
      {r.status==='DRAFT' && <button className="table-btn" onClick={()=>action(r.id,'place')}>Đặt hàng</button>}
      {r.status==='ORDERED' && <button className="table-btn" onClick={()=>action(r.id,'receive')}>Nhập kho</button>}
    </div>},
  ]
  return <>
    <div className="toolbar"><span>{rows.length} đơn mua hàng</span><button className="primary-btn small" onClick={()=>setShow(true)}><Plus size={15}/> Tạo đơn mua hàng</button></div>
    {loading ? <div className="loading">Đang tải…</div> : <div className="panel"><DataTable rows={rows} columns={columns}/></div>}
    {show && <div className="modal-backdrop" onMouseDown={()=>setShow(false)}><form className="modal" onSubmit={create} onMouseDown={e=>e.stopPropagation()}>
      <h3>Tạo đơn mua hàng</h3>
      <div className="form-grid">
        <label>Mã đơn mua hàng<input name="code" required placeholder="PO-2026-020"/></label>
        <label>Nhà cung cấp<select name="supplier_id" required defaultValue="">
          <option value="" disabled>Chọn nhà cung cấp</option>
          {suppliers.map(s=><option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
        </select></label>
        <label>Ngày giao dự kiến<input name="expected_delivery_date" type="date"/></label>
      </div>
      <h3>Hạng mục</h3>
      {items.map((it,idx)=><div key={idx} className="form-grid" style={{gridTemplateColumns:'2fr 1fr 1fr auto',alignItems:'end'}}>
        <label>Hàng hóa<select value={it.product_id} onChange={e=>updateItem(idx,{product_id:Number(e.target.value)})} required>
          <option value="" disabled>Chọn hàng hóa</option>
          {products.map(p=><option key={p.id} value={p.id}>{p.sku} — {p.name}</option>)}
        </select></label>
        <label>SL<input type="number" min={1} value={it.quantity} onChange={e=>updateItem(idx,{quantity:Number(e.target.value)})}/></label>
        <label>Đơn giá<input type="number" min={0} value={it.unit_price} onChange={e=>updateItem(idx,{unit_price:Number(e.target.value)})}/></label>
        <button type="button" className="ghost-btn" onClick={()=>setItems(items.filter((_,i)=>i!==idx))} disabled={items.length===1}><Trash2 size={15}/></button>
      </div>)}
      <button type="button" className="ghost-btn" onClick={()=>setItems([...items,{...emptyItem}])}><Plus size={15}/> Thêm hạng mục</button>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setShow(false)}>Hủy</button><button className="primary-btn">Lưu đơn mua hàng</button></div>
    </form></div>}
  </>
}
