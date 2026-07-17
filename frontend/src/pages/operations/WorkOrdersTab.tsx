import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { api } from '../../lib/api'
import { date } from '../../lib/format'
import { DataTable } from '../../components/DataTable'
import { StatusBadge } from '../../components/StatusBadge'

export function WorkOrdersTab({ projects, onChange }: {projects: any[]; onChange?: () => void}) {
  const [rows, setRows] = useState<any[]>([]); const [loading, setLoading] = useState(false); const [show, setShow] = useState(false)
  const load = () => { setLoading(true); api.get('/operations/work-orders').then(r => setRows(r.data)).finally(() => setLoading(false)) }
  useEffect(() => { load() }, [])
  const create = async (e: React.FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); await api.post('/operations/work-orders', Object.fromEntries(f)); setShow(false); load() }
  const action = async (id: number, path: string) => { await api.post(`/operations/work-orders/${id}/${path}`); load(); onChange?.() }
  const projectName = (id: number) => projects.find(p => p.id === id)?.name || id
  const columns: any = [
    {key:'code',label:'Mã WO'},
    {key:'project_id',label:'Dự án',render:(r:any)=>projectName(r.project_id)},
    {key:'title',label:'Nội dung'},
    {key:'scheduled_date',label:'Ngày dự kiến',render:(r:any)=>date(r.scheduled_date)},
    {key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>},
    {key:'actions',label:'',render:(r:any)=><div style={{display:'flex',gap:6}}>
      {r.status==='PLANNED' && <button className="table-btn" onClick={()=>action(r.id,'start')}>Bắt đầu</button>}
      {r.status==='IN_PROGRESS' && <button className="table-btn" onClick={()=>action(r.id,'complete')}>Hoàn thành</button>}
    </div>},
  ]
  return <>
    <div className="toolbar"><span>{rows.length} work order</span><button className="primary-btn small" onClick={()=>setShow(true)}><Plus size={15}/> Tạo work order</button></div>
    {loading ? <div className="loading">Đang tải…</div> : <div className="panel"><DataTable rows={rows} columns={columns}/></div>}
    {show && <div className="modal-backdrop" onMouseDown={()=>setShow(false)}><form className="modal" onSubmit={create} onMouseDown={e=>e.stopPropagation()}>
      <h3>Tạo work order</h3>
      <div className="form-grid">
        <label>Mã WO<input name="code" required placeholder="WO-2026-030"/></label>
        <label>Dự án<select name="project_id" required defaultValue="">
          <option value="" disabled>Chọn dự án</option>
          {projects.map(p=><option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
        </select></label>
        <label className="full">Nội dung<input name="title" required/></label>
        <label>Địa điểm<input name="location"/></label>
        <label>Ngày dự kiến<input name="scheduled_date" type="date"/></label>
        <label className="full">Vật tư cần dùng<input name="materials_needed"/></label>
        <label className="full">Checklist<input name="checklist"/></label>
      </div>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setShow(false)}>Hủy</button><button className="primary-btn">Lưu work order</button></div>
    </form></div>}
  </>
}
