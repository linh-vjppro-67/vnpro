import { useEffect, useState } from 'react'
import { Plus, Search } from 'lucide-react'
import { api } from '../lib/api'
import { money, date, label } from '../lib/format'
import { PageHeader } from '../components/PageHeader'
import { DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'
import { LeadsTab } from './sales/LeadsTab'
import { QuotationsTab } from './sales/QuotationsTab'
import { ContractsTab } from './sales/ContractsTab'

export function SalesPage() {
  const [tab, setTab] = useState<'leads'|'opportunities'|'customers'|'quotations'|'contracts'|'orders'>('opportunities')
  const [rows, setRows] = useState<any[]>([]); const [loading, setLoading] = useState(false); const [show, setShow] = useState(false)
  const [customers, setCustomers] = useState<any[]>([]); const [opportunities, setOpportunities] = useState<any[]>([]); const [quotations, setQuotations] = useState<any[]>([])
  const [products, setProducts] = useState<any[]>([])
  const simpleTab = tab==='opportunities'||tab==='customers'||tab==='orders'
  const load = async () => {
    setLoading(true)
    try {
      const [c, o, q, p] = await Promise.all([api.get('/sales/customers'), api.get('/sales/opportunities'), api.get('/crm/quotations'), api.get('/inventory/products')])
      setCustomers(c.data); setOpportunities(o.data); setQuotations(q.data); setProducts(p.data)
      if (simpleTab) { const r = await api.get(`/sales/${tab}`); setRows(r.data) }
    } finally { setLoading(false) }
  }
  useEffect(()=>{ load() }, [tab])
  const createCustomer = async (e: React.FormEvent<HTMLFormElement>) => { e.preventDefault(); const f=new FormData(e.currentTarget); await api.post('/sales/customers', Object.fromEntries(f)); setShow(false); load() }
  const columns: any = tab==='customers' ? [
    {key:'code',label:'Mã KH'}, {key:'name',label:'Khách hàng'}, {key:'segment',label:'Phân khúc'}, {key:'phone',label:'Điện thoại'}, {key:'email',label:'Email'}
  ] : tab==='orders' ? [
    {key:'code',label:'Mã đơn'}, {key:'title',label:'Nội dung'}, {key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>}, {key:'total_amount',label:'Doanh thu',render:(r:any)=>money(r.total_amount)}, {key:'cost_estimate',label:'Giá vốn',render:(r:any)=>money(r.cost_estimate)}, {key:'due_date',label:'Hạn',render:(r:any)=>date(r.due_date)}
  ] : [
    {key:'code',label:'Mã cơ hội'}, {key:'title',label:'Cơ hội'}, {key:'stage',label:'Giai đoạn',render:(r:any)=><StatusBadge value={r.stage}/>}, {key:'expected_value',label:'Giá trị',render:(r:any)=>money(r.expected_value)}, {key:'probability',label:'Xác suất',render:(r:any)=>`${r.probability}%`}, {key:'expected_close_date',label:'Dự kiến chốt',render:(r:any)=>date(r.expected_close_date)}
  ]
  return <><PageHeader title="Bán hàng & CRM" description="Quản lý khách hàng từ tìm kiếm, tư vấn, báo giá, hợp đồng đến theo dõi công nợ." actions={<button className="primary-btn small" onClick={()=>setShow(true)}><Plus size={17}/> Thêm khách hàng</button>}/>
    <div className="tabs">
      <button className={tab==='leads'?'active':''} onClick={()=>setTab('leads')}>Lead</button>
      <button className={tab==='opportunities'?'active':''} onClick={()=>setTab('opportunities')}>Cơ hội</button>
      <button className={tab==='customers'?'active':''} onClick={()=>setTab('customers')}>Khách hàng</button>
      <button className={tab==='quotations'?'active':''} onClick={()=>setTab('quotations')}>Báo giá</button>
      <button className={tab==='contracts'?'active':''} onClick={()=>setTab('contracts')}>Hợp đồng</button>
      <button className={tab==='orders'?'active':''} onClick={()=>setTab('orders')}>Đơn hàng</button>
    </div>
    {tab==='leads' && <LeadsTab/>}
    {tab==='quotations' && <QuotationsTab opportunities={opportunities} customers={customers} products={products}/>}
    {tab==='contracts' && <ContractsTab customers={customers} quotations={quotations}/>}
    {simpleTab && <section className="panel"><div className="toolbar"><div className="search"><Search size={17}/><input placeholder="Tìm theo mã hoặc tên…"/></div><span>{rows.length} bản ghi</span></div>{loading?<div className="loading">Đang tải…</div>:<DataTable rows={rows} columns={columns}/>}</section>}
    {show && <div className="modal-backdrop" onMouseDown={()=>setShow(false)}><form className="modal" onSubmit={createCustomer} onMouseDown={e=>e.stopPropagation()}><h3>Thêm khách hàng</h3><div className="form-grid"><label>Mã khách hàng<input name="code" required placeholder="KH-005"/></label><label>Tên khách hàng<input name="name" required/></label><label>Mã số thuế<input name="tax_code"/></label><label>Phân khúc<select name="segment"><option>Doanh nghiệp</option><option>Sản xuất</option><option>Dược phẩm</option><option>Logistics</option><option>Bán lẻ</option></select></label><label>Điện thoại<input name="phone"/></label><label>Email<input name="email" type="email"/></label><label className="full">Địa chỉ<input name="address"/></label></div><div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setShow(false)}>Hủy</button><button className="primary-btn">Lưu khách hàng</button></div></form></div>}
  </>
}
