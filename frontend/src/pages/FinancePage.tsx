import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { money, date } from '../lib/format'
import { PageHeader } from '../components/PageHeader'
import { DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'

export function FinancePage(){const[rows,setRows]=useState<any[]>([]);useEffect(()=>{api.get('/finance/receivables').then(r=>setRows(r.data))},[]);const total=rows.reduce((s,r)=>s+Number(r.amount)-Number(r.paid_amount),0);const overdue=rows.filter(r=>new Date(r.due_date)<new Date()&&r.status!=='PAID').reduce((s,r)=>s+Number(r.amount)-Number(r.paid_amount),0)
return <><PageHeader title="Công nợ & tài chính" description="Theo dõi hóa đơn, phải thu, hạn thanh toán và dữ liệu đồng bộ MISA."/><div className="finance-cards"><div><span>Tổng phải thu</span><b>{money(total)}</b></div><div className="danger"><span>Quá hạn</span><b>{money(overdue)}</b></div><div><span>Tỷ lệ thu hồi</span><b>{Math.round(rows.reduce((s,r)=>s+Number(r.paid_amount),0)/Math.max(1,rows.reduce((s,r)=>s+Number(r.amount),0))*100)}%</b></div></div><section className="panel"><DataTable rows={rows} columns={[{key:'invoice_no',label:'Số hóa đơn'},{key:'customer_id',label:'Khách hàng',render:(r:any)=>`KH #${r.customer_id}`},{key:'amount',label:'Giá trị',render:(r:any)=>money(r.amount)},{key:'paid_amount',label:'Đã thu',render:(r:any)=>money(r.paid_amount)},{key:'remaining',label:'Còn lại',render:(r:any)=>money(Number(r.amount)-Number(r.paid_amount))},{key:'due_date',label:'Hạn',render:(r:any)=>date(r.due_date)},{key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>} ]}/></section></>}
