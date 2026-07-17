import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { api } from '../lib/api'
import { date } from '../lib/format'
import { PageHeader } from '../components/PageHeader'
import { DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'
import { useAuth } from '../components/AuthContext'

export function TasksPage() {
  const { user } = useAuth()
  const [mineOnly, setMineOnly] = useState(true)
  const [rows, setRows] = useState<any[]>([]); const [loading, setLoading] = useState(false); const [show, setShow] = useState(false)
  const [users, setUsers] = useState<any[]>([]); const [submitting, setSubmitting] = useState<any>(null); const [rejecting, setRejecting] = useState<any>(null)
  const load = () => { setLoading(true); api.get(`/tasks${mineOnly ? '?mine=true' : ''}`).then(r => setRows(r.data)).finally(() => setLoading(false)) }
  useEffect(() => { load() }, [mineOnly])
  useEffect(() => { api.get('/tasks/assignees').then(r => setUsers(r.data)) }, [])
  const create = async (e: React.FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); await api.post('/tasks', { ...Object.fromEntries(f), assigned_to: Number(f.get('assigned_to')) }); setShow(false); load() }
  const action = async (id: number, path: string, body: any = {}) => { await api.post(`/tasks/${id}/${path}`, body); load() }
  const submitProgress = async (e: React.FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); await action(submitting.id, 'submit', { note: f.get('note') }); setSubmitting(null) }
  const rejectWithNote = async (e: React.FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); await action(rejecting.id, 'reject', { note: f.get('note') }); setRejecting(null) }
  const userName = (id: number) => users.find(u => u.id === id)?.full_name || id
  const columns: any = [
    {key:'code',label:'Mã CV'}, {key:'title',label:'Nội dung'}, {key:'department',label:'Phòng ban'},
    {key:'assigned_to',label:'Người thực hiện',render:(r:any)=>userName(r.assigned_to)},
    {key:'assigned_by',label:'Người giao',render:(r:any)=>userName(r.assigned_by)},
    {key:'priority',label:'Ưu tiên',render:(r:any)=><StatusBadge value={r.priority}/>},
    {key:'due_date',label:'Hạn',render:(r:any)=>date(r.due_date)},
    {key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>},
    {key:'actions',label:'',render:(r:any)=><div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
      {r.status==='NEW' && r.assigned_to===user?.id && <button className="table-btn" onClick={()=>action(r.id,'start')}>Bắt đầu</button>}
      {r.status==='IN_PROGRESS' && r.assigned_to===user?.id && <button className="table-btn" onClick={()=>setSubmitting(r)}>Xác nhận hoàn thành</button>}
      {r.status==='DONE_PENDING_REVIEW' && r.assigned_by===user?.id && <button className="table-btn" onClick={()=>action(r.id,'confirm')}>Duyệt kết quả</button>}
      {r.status==='DONE_PENDING_REVIEW' && r.assigned_by===user?.id && <button className="table-btn" onClick={()=>setRejecting(r)}>Yêu cầu làm lại</button>}
      {(r.status==='NEW'||r.status==='IN_PROGRESS') && (r.assigned_to===user?.id||r.assigned_by===user?.id) && <button className="table-btn" onClick={()=>action(r.id,'cancel')}>Hủy</button>}
    </div>},
  ]
  return <><PageHeader title="Quản lý công việc" description="Giao việc, theo dõi tiến độ và xác nhận hoàn thành theo từng cá nhân, phòng ban." actions={<button className="primary-btn small" onClick={()=>setShow(true)}><Plus size={17}/> Giao việc</button>}/>
    <div className="toolbar"><label style={{display:'flex',alignItems:'center',gap:6}}><input type="checkbox" checked={mineOnly} onChange={e=>setMineOnly(e.target.checked)}/> Chỉ việc của tôi</label><span>{rows.length} công việc</span></div>
    {loading ? <div className="loading">Đang tải…</div> : <section className="panel"><DataTable rows={rows} columns={columns}/></section>}
    {show && <div className="modal-backdrop" onMouseDown={()=>setShow(false)}><form className="modal" onSubmit={create} onMouseDown={e=>e.stopPropagation()}>
      <h3>Giao việc</h3>
      <div className="form-grid">
        <label>Mã công việc<input name="code" required placeholder="CV-2026-110"/></label>
        <label>Phòng ban<select name="department"><option>Kinh doanh</option><option>Kỹ thuật</option><option>Kế toán</option><option>Kho</option><option>HCVP</option><option>CSKH</option></select></label>
        <label className="full">Nội dung công việc<input name="title" required/></label>
        <label>Người thực hiện<select name="assigned_to" required defaultValue="">
          <option value="" disabled>Chọn người thực hiện</option>
          {users.map(u=><option key={u.id} value={u.id}>{u.full_name} — {u.department}</option>)}
        </select></label>
        <label>Mức độ ưu tiên<select name="priority" defaultValue="MEDIUM"><option value="LOW">Thấp</option><option value="MEDIUM">Trung bình</option><option value="HIGH">Cao</option></select></label>
        <label>Hạn hoàn thành<input name="due_date" type="date" defaultValue={new Date(Date.now()+7*86400000).toISOString().slice(0,10)}/></label>
        <label className="full">Mô tả chi tiết<input name="description"/></label>
      </div>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setShow(false)}>Hủy</button><button className="primary-btn">Giao việc</button></div>
    </form></div>}
    {submitting && <div className="modal-backdrop" onMouseDown={()=>setSubmitting(null)}><form className="modal" onSubmit={submitProgress} onMouseDown={e=>e.stopPropagation()}>
      <h3>Xác nhận hoàn thành · {submitting.code}</h3>
      <div className="form-grid"><label className="full">Kết quả thực hiện<input name="note" placeholder="Mô tả kết quả đã làm"/></label></div>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setSubmitting(null)}>Hủy</button><button className="primary-btn">Gửi xác nhận</button></div>
    </form></div>}
    {rejecting && <div className="modal-backdrop" onMouseDown={()=>setRejecting(null)}><form className="modal" onSubmit={rejectWithNote} onMouseDown={e=>e.stopPropagation()}>
      <h3>Yêu cầu làm lại · {rejecting.code}</h3>
      <div className="form-grid"><label className="full">Lý do / yêu cầu bổ sung<input name="note" required/></label></div>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setRejecting(null)}>Hủy</button><button className="primary-btn">Gửi yêu cầu làm lại</button></div>
    </form></div>}
  </>
}
