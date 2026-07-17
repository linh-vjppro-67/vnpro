import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { api } from '../../lib/api'
import { DataTable } from '../../components/DataTable'
import { StatusBadge } from '../../components/StatusBadge'
import { useAuth } from '../../components/AuthContext'

export function PurchaseRequestsTab({ products, suppliers, onChange }: {products: any[]; suppliers: any[]; onChange?: () => void}) {
  const { user } = useAuth()
  const canApprove = ['DIRECTOR','SYSTEM_ADMIN'].includes(user?.role || '')
  const [rows, setRows] = useState<any[]>([]); const [loading, setLoading] = useState(false); const [show, setShow] = useState(false)
  const [converting, setConverting] = useState<any>(null)
  const load = () => { setLoading(true); api.get('/purchasing/requests').then(r => setRows(r.data)).finally(() => setLoading(false)) }
  useEffect(() => { load() }, [])
  const create = async (e: React.FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); await api.post('/purchasing/requests', Object.fromEntries(f)); setShow(false); load() }
  const action = async (id: number, path: string, body: any = {}) => { await api.post(`/purchasing/requests/${id}/${path}`, body); load(); onChange?.() }
  const convert = async (e: React.FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); await api.post(`/purchasing/requests/${converting.id}/convert-to-order`, { code: f.get('code'), supplier_id: Number(f.get('supplier_id')) }); setConverting(null); load(); onChange?.() }
  const productName = (id: number) => products.find(p => p.id === id)?.name || id
  const columns: any = [
    {key:'code',label:'Mã YCM'},
    {key:'product_id',label:'Hàng hóa',render:(r:any)=>productName(r.product_id)},
    {key:'quantity',label:'SL'},
    {key:'department',label:'Phòng ban'},
    {key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>},
    {key:'actions',label:'',render:(r:any)=><div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
      {r.status==='DRAFT' && <button className="table-btn" onClick={()=>action(r.id,'submit')}>Gửi duyệt</button>}
      {r.status==='SUBMITTED' && canApprove && <button className="table-btn" onClick={()=>action(r.id,'approve')}>Duyệt</button>}
      {r.status==='SUBMITTED' && canApprove && <button className="table-btn" onClick={()=>action(r.id,'reject')}>Từ chối</button>}
      {r.status==='APPROVED' && <button className="table-btn" onClick={()=>setConverting(r)}>Tạo đơn mua hàng</button>}
    </div>},
  ]
  return <>
    <div className="toolbar"><span>{rows.length} yêu cầu mua hàng</span><button className="primary-btn small" onClick={()=>setShow(true)}><Plus size={15}/> Tạo yêu cầu mua hàng</button></div>
    {loading ? <div className="loading">Đang tải…</div> : <div className="panel"><DataTable rows={rows} columns={columns}/></div>}
    {show && <div className="modal-backdrop" onMouseDown={()=>setShow(false)}><form className="modal" onSubmit={create} onMouseDown={e=>e.stopPropagation()}>
      <h3>Tạo yêu cầu mua hàng</h3>
      <div className="form-grid">
        <label>Mã YCM<input name="code" required placeholder="YCM-2026-010"/></label>
        <label>Phòng ban<select name="department"><option>Kho</option><option>Kỹ thuật</option><option>Kinh doanh</option><option>HCVP</option></select></label>
        <label>Hàng hóa<select name="product_id" required defaultValue="">
          <option value="" disabled>Chọn hàng hóa</option>
          {products.map(p=><option key={p.id} value={p.id}>{p.sku} — {p.name}</option>)}
        </select></label>
        <label>Số lượng<input name="quantity" type="number" min="1" required defaultValue={1}/></label>
        <label className="full">Lý do<input name="reason"/></label>
      </div>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setShow(false)}>Hủy</button><button className="primary-btn">Lưu yêu cầu</button></div>
    </form></div>}
    {converting && <div className="modal-backdrop" onMouseDown={()=>setConverting(null)}><form className="modal" onSubmit={convert} onMouseDown={e=>e.stopPropagation()}>
      <h3>Tạo đơn mua hàng từ {converting.code}</h3>
      <div className="form-grid">
        <label>Mã đơn mua hàng<input name="code" required placeholder="PO-2026-020"/></label>
        <label>Nhà cung cấp<select name="supplier_id" required defaultValue="">
          <option value="" disabled>Chọn nhà cung cấp</option>
          {suppliers.map(s=><option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
        </select></label>
      </div>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setConverting(null)}>Hủy</button><button className="primary-btn">Tạo đơn mua hàng</button></div>
    </form></div>}
  </>
}
