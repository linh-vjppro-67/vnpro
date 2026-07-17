import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { api } from '../../lib/api'
import { DataTable } from '../../components/DataTable'
import { StatusBadge } from '../../components/StatusBadge'
import { useAuth } from '../../components/AuthContext'

export function AcceptanceRecordsTab({ workOrders }: {workOrders: any[]}) {
  const { user } = useAuth()
  const canApprove = ['TECH_SOLUTION','DIRECTOR','SYSTEM_ADMIN'].includes(user?.role || '')
  const [rows, setRows] = useState<any[]>([]); const [loading, setLoading] = useState(false); const [show, setShow] = useState(false)
  const doneWorkOrders = workOrders.filter(w => w.status === 'DONE')
  const load = () => { setLoading(true); api.get('/operations/acceptance-records').then(r => setRows(r.data)).finally(() => setLoading(false)) }
  useEffect(() => { load() }, [])
  const create = async (e: React.FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); await api.post('/operations/acceptance-records', Object.fromEntries(f)); setShow(false); load() }
  const action = async (id: number, path: string, body: any = {}) => { await api.post(`/operations/acceptance-records/${id}/${path}`, body); load() }
  const woCode = (id: number) => workOrders.find(w => w.id === id)?.code || id
  const columns: any = [
    {key:'code',label:'Mã biên bản'},
    {key:'work_order_id',label:'Work order',render:(r:any)=>woCode(r.work_order_id)},
    {key:'customer_signed_by',label:'KH xác nhận'},
    {key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>},
    {key:'actions',label:'',render:(r:any)=><div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
      {r.status==='DRAFT' && <button className="table-btn" onClick={()=>action(r.id,'submit')}>Gửi duyệt</button>}
      {r.status==='SUBMITTED' && canApprove && <button className="table-btn" onClick={()=>action(r.id,'approve')}>Duyệt</button>}
      {r.status==='SUBMITTED' && canApprove && <button className="table-btn" onClick={()=>action(r.id,'reject')}>Từ chối</button>}
    </div>},
  ]
  return <>
    <div className="toolbar"><span>{rows.length} biên bản nghiệm thu</span><button className="primary-btn small" onClick={()=>setShow(true)} disabled={doneWorkOrders.length===0}><Plus size={15}/> Lập biên bản</button></div>
    {loading ? <div className="loading">Đang tải…</div> : <div className="panel"><DataTable rows={rows} columns={columns}/></div>}
    {show && <div className="modal-backdrop" onMouseDown={()=>setShow(false)}><form className="modal" onSubmit={create} onMouseDown={e=>e.stopPropagation()}>
      <h3>Lập biên bản nghiệm thu</h3>
      <div className="form-grid">
        <label>Mã biên bản<input name="code" required placeholder="NT-2026-030"/></label>
        <label>Work order<select name="work_order_id" required defaultValue="">
          <option value="" disabled>Chọn work order đã hoàn thành</option>
          {doneWorkOrders.map(w=><option key={w.id} value={w.id}>{w.code} — {w.title}</option>)}
        </select></label>
        <label className="full">Nội dung nghiệm thu<input name="summary"/></label>
        <label className="full">Người xác nhận (khách hàng)<input name="customer_signed_by"/></label>
      </div>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setShow(false)}>Hủy</button><button className="primary-btn">Lưu biên bản</button></div>
    </form></div>}
  </>
}
