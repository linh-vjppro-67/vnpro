import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { api } from '../lib/api'
import { money, date } from '../lib/format'
import { PageHeader } from '../components/PageHeader'
import { DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'

export function CostsPage() {
  const [budgets,setBudgets]=useState<any[]>([]); const [expenses,setExpenses]=useState<any[]>([]); const [show,setShow]=useState(false)
  const load=()=>Promise.all([api.get('/costs/budgets'),api.get('/costs/expenses')]).then(([b,e])=>{setBudgets(b.data);setExpenses(e.data)})
  useEffect(()=>{load()},[])
  const submit=async(e:React.FormEvent<HTMLFormElement>)=>{e.preventDefault();const f=new FormData(e.currentTarget);await api.post('/costs/expenses',Object.fromEntries(f));setShow(false);load()}
  return <><PageHeader title="Quản lý chi phí" description="Kiểm soát ngân sách, chi phí thực tế, đề nghị thanh toán và phê duyệt." actions={<button className="primary-btn small" onClick={()=>setShow(true)}><Plus size={17}/> Tạo chi phí</button>}/>
    <div className="budget-grid">{budgets.map(b=><div className="budget-card" key={b.id}><div><span>{b.department}</span><strong>{b.name}</strong></div><div className="budget-values"><b>{money(b.spent_amount)}</b><span>/ {money(b.amount)}</span></div><div className="progress"><i style={{width:`${Math.min(100,Number(b.spent_amount)/Number(b.amount)*100)}%`}}/></div><small>{Math.round(Number(b.spent_amount)/Number(b.amount)*100)}% đã sử dụng · {b.period}</small></div>)}</div>
    <section className="panel"><div className="panel-title"><div><h3>Danh sách chi phí</h3><p>Chi phí chờ duyệt, đã duyệt và từ chối</p></div></div><DataTable rows={expenses} columns={[
      {key:'code',label:'Mã'}, {key:'description',label:'Nội dung'}, {key:'department',label:'Phòng ban'}, {key:'category',label:'Nhóm'}, {key:'expense_date',label:'Ngày',render:(r:any)=>date(r.expense_date)}, {key:'amount',label:'Số tiền',render:(r:any)=>money(r.amount)}, {key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>}
    ]}/></section>
    {show&&<div className="modal-backdrop" onMouseDown={()=>setShow(false)}><form className="modal" onSubmit={submit} onMouseDown={e=>e.stopPropagation()}><h3>Tạo đề nghị chi phí</h3><div className="form-grid"><label>Mã chi phí<input name="code" required placeholder="CP-00085"/></label><label>Số tiền<input name="amount" required type="number" min="1"/></label><label className="full">Nội dung<input name="description" required/></label><label>Phòng ban<select name="department"><option>Kinh doanh</option><option>Kỹ thuật</option><option>Kế toán</option><option>Kho</option><option>HCVP</option></select></label><label>Nhóm chi phí<select name="category"><option>Vật tư</option><option>Vận chuyển</option><option>Marketing</option><option>Vận hành</option><option>Công tác</option></select></label><label>Ngày chi<input name="expense_date" type="date" required defaultValue={new Date().toISOString().slice(0,10)}/></label></div><div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setShow(false)}>Hủy</button><button className="primary-btn">Gửi chờ duyệt</button></div></form></div>}
  </>
}
