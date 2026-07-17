import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { api } from '../../lib/api'
import { DataTable } from '../../components/DataTable'
import { StatusBadge } from '../../components/StatusBadge'

export function ReservationsTab({ products, salesOrders, onChange }: {products: any[]; salesOrders: any[]; onChange?: () => void}) {
  const [rows, setRows] = useState<any[]>([]); const [loading, setLoading] = useState(false); const [show, setShow] = useState(false)
  const load = () => { setLoading(true); api.get('/inventory/reservations').then(r => setRows(r.data)).finally(() => setLoading(false)) }
  useEffect(() => { load() }, [])
  const create = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); const f = new FormData(e.currentTarget)
    await api.post('/inventory/reservations', { product_id: Number(f.get('product_id')), sales_order_id: f.get('sales_order_id') ? Number(f.get('sales_order_id')) : null, quantity: Number(f.get('quantity')) })
    setShow(false); load(); onChange?.()
  }
  const action = async (id: number, path: string) => { await api.post(`/inventory/reservations/${id}/${path}`); load(); onChange?.() }
  const productName = (id: number) => products.find(p => p.id === id)?.name || id
  const orderCode = (id: number | null) => salesOrders.find(o => o.id === id)?.code || (id ? id : '—')
  const columns: any = [
    {key:'product_id',label:'Hàng hóa',render:(r:any)=>productName(r.product_id)},
    {key:'quantity',label:'SL giữ'},
    {key:'sales_order_id',label:'Đơn hàng',render:(r:any)=>orderCode(r.sales_order_id)},
    {key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>},
    {key:'actions',label:'',render:(r:any)=><div style={{display:'flex',gap:6}}>
      {r.status==='RESERVED' && <button className="table-btn" onClick={()=>action(r.id,'fulfill')}>Xuất kho</button>}
      {r.status==='RESERVED' && <button className="table-btn" onClick={()=>action(r.id,'release')}>Hủy giữ</button>}
    </div>},
  ]
  return <>
    <div className="toolbar"><span>{rows.length} phiếu giữ hàng</span><button className="primary-btn small" onClick={()=>setShow(true)}><Plus size={15}/> Giữ hàng</button></div>
    {loading ? <div className="loading">Đang tải…</div> : <div className="panel"><DataTable rows={rows} columns={columns}/></div>}
    {show && <div className="modal-backdrop" onMouseDown={()=>setShow(false)}><form className="modal" onSubmit={create} onMouseDown={e=>e.stopPropagation()}>
      <h3>Giữ hàng cho đơn hàng / dự án</h3>
      <div className="form-grid">
        <label>Hàng hóa<select name="product_id" required defaultValue="">
          <option value="" disabled>Chọn hàng hóa</option>
          {products.map(p=><option key={p.id} value={p.id}>{p.sku} — {p.name} (khả dụng {p.quantity_on_hand-p.reserved_quantity})</option>)}
        </select></label>
        <label>Số lượng<input name="quantity" type="number" min="1" required defaultValue={1}/></label>
        <label>Đơn hàng<select name="sales_order_id" defaultValue="">
          <option value="">Không gắn đơn hàng</option>
          {salesOrders.map(o=><option key={o.id} value={o.id}>{o.code}</option>)}
        </select></label>
      </div>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setShow(false)}>Hủy</button><button className="primary-btn">Giữ hàng</button></div>
    </form></div>}
  </>
}
