import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { api } from '../../lib/api'
import { DataTable } from '../../components/DataTable'

export function SuppliersTab() {
  const [rows, setRows] = useState<any[]>([]); const [loading, setLoading] = useState(false); const [show, setShow] = useState(false)
  const load = () => { setLoading(true); api.get('/purchasing/suppliers').then(r => setRows(r.data)).finally(() => setLoading(false)) }
  useEffect(() => { load() }, [])
  const create = async (e: React.FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); await api.post('/purchasing/suppliers', Object.fromEntries(f)); setShow(false); load() }
  const columns: any = [
    {key:'code',label:'Mã NCC'}, {key:'name',label:'Tên nhà cung cấp'}, {key:'contact_person',label:'Người liên hệ'}, {key:'phone',label:'Điện thoại'}, {key:'email',label:'Email'},
  ]
  return <>
    <div className="toolbar"><span>{rows.length} nhà cung cấp</span><button className="primary-btn small" onClick={()=>setShow(true)}><Plus size={15}/> Thêm nhà cung cấp</button></div>
    {loading ? <div className="loading">Đang tải…</div> : <div className="panel"><DataTable rows={rows} columns={columns}/></div>}
    {show && <div className="modal-backdrop" onMouseDown={()=>setShow(false)}><form className="modal" onSubmit={create} onMouseDown={e=>e.stopPropagation()}>
      <h3>Thêm nhà cung cấp</h3>
      <div className="form-grid">
        <label>Mã NCC<input name="code" required placeholder="NCC-003"/></label>
        <label>Tên nhà cung cấp<input name="name" required/></label>
        <label>Mã số thuế<input name="tax_code"/></label>
        <label>Người liên hệ<input name="contact_person"/></label>
        <label>Điện thoại<input name="phone"/></label>
        <label>Email<input name="email" type="email"/></label>
        <label className="full">Địa chỉ<input name="address"/></label>
      </div>
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setShow(false)}>Hủy</button><button className="primary-btn">Lưu nhà cung cấp</button></div>
    </form></div>}
  </>
}
