import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { api } from '../../lib/api'
import { DataTable } from '../../components/DataTable'
import { StatusBadge } from '../../components/StatusBadge'

export function LeadsTab() {
  const [rows, setRows] = useState<any[]>([]); const [loading, setLoading] = useState(false)
  const [show, setShow] = useState(false); const [convertLead, setConvertLead] = useState<any>(null)
  const load = () => { setLoading(true); api.get('/crm/leads').then(r => setRows(r.data)).finally(() => setLoading(false)) }
  useEffect(() => { load() }, [])
  const create = async (e: React.FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); await api.post('/crm/leads', Object.fromEntries(f)); setShow(false); load() }
  const setStatus = async (lead: any, status: string) => { await api.patch(`/crm/leads/${lead.id}/status`, { status }); load() }
  const convert = async (e: React.FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); await api.post(`/crm/leads/${convertLead.id}/convert`, Object.fromEntries(f)); setConvertLead(null); load() }
  const columns: any = [
    {key:'code',label:'Mã lead'}, {key:'company_name',label:'Công ty'}, {key:'contact_name',label:'Người liên hệ'}, {key:'phone',label:'Điện thoại'},
    {key:'potential_level',label:'Tiềm năng',render:(r:any)=><StatusBadge value={r.potential_level}/>},
    {key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>},
    {key:'actions',label:'',render:(r:any)=><div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
      {r.status==='NEW' && <button className="table-btn" onClick={()=>setStatus(r,'CONTACTED')}>Đã liên hệ</button>}
      {r.status==='CONTACTED' && <button className="table-btn" onClick={()=>setStatus(r,'QUALIFIED')}>Đủ điều kiện</button>}
      {r.status==='QUALIFIED' && <button className="table-btn" onClick={()=>setConvertLead(r)}>Chuyển thành cơ hội</button>}
    </div>},
  ]
  return <>
    <div className="toolbar"><span>{rows.length} lead</span><button className="primary-btn small" onClick={()=>setShow(true)}><Plus size={15}/> Thêm lead</button></div>
    {loading ? <div className="loading">Đang tải…</div> : <div className="panel"><DataTable rows={rows} columns={columns}/></div>}
    {show && <div className="modal-backdrop" onMouseDown={()=>setShow(false)}><form className="modal" onSubmit={create} onMouseDown={e=>e.stopPropagation()}>
      <h3>Thêm lead</h3>
      <div className="form-grid">
        <label>Mã lead<input name="code" required placeholder="LD-2026-010"/></label>
        <label>Nguồn<select name="source" defaultValue="WEBSITE"><option value="WEBSITE">Website</option><option value="REFERRAL">Giới thiệu</option><option value="FAIR">Hội chợ</option><option value="COLD_CALL">Gọi lạnh</option><option value="OTHER">Khác</option></select></label>
        <label>Công ty<input name="company_name" required/></label>
        <label>Người liên hệ<input name="contact_name" required/></label>
        <label>Điện thoại<input name="phone"/></label>
        <label>Email<input name="email" type="email"/></label>
        <label>Mức độ tiềm năng<select name="potential_level" defaultValue="MEDIUM"><option value="LOW">Thấp</option><option value="MEDIUM">Trung bình</option><option value="HIGH">Cao</option></select></label>
        <label className="full">Nhu cầu<input name="need_summary"/></label>
      </div>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setShow(false)}>Hủy</button><button className="primary-btn">Lưu lead</button></div>
    </form></div>}
    {convertLead && <div className="modal-backdrop" onMouseDown={()=>setConvertLead(null)}><form className="modal" onSubmit={convert} onMouseDown={e=>e.stopPropagation()}>
      <h3>Chuyển lead thành cơ hội</h3>
      <p>{convertLead.company_name}</p>
      <div className="form-grid">
        <label>Mã cơ hội<input name="opportunity_code" required placeholder="CH-2026-010"/></label>
        <label>Tên cơ hội<input name="opportunity_title" required defaultValue={convertLead.need_summary || ''}/></label>
        <label>Giá trị dự kiến<input name="expected_value" type="number" min="0" step="1000000" defaultValue={0}/></label>
        <label>Xác suất (%)<input name="probability" type="number" min="0" max="100" defaultValue={20}/></label>
      </div>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setConvertLead(null)}>Hủy</button><button className="primary-btn">Chuyển đổi</button></div>
    </form></div>}
  </>
}
