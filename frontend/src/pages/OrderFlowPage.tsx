import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, Circle, PackageCheck, Plus, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'
import { money, date } from '../lib/format'
import { PageHeader } from '../components/PageHeader'
import { DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'
import '../order-flow.css'
import '../order-status.css'

const stages=['DRAFT','WAITING_INVENTORY','READY_FOR_DELIVERY','IN_IMPLEMENTATION','ACCEPTED','INVOICED','PARTIALLY_PAID','PAID','CLOSED']
const stageLabel:any={DRAFT:'Đơn nháp',WAITING_INVENTORY:'Kiểm tồn',READY_FOR_DELIVERY:'Sẵn sàng xuất',IN_IMPLEMENTATION:'Triển khai',ACCEPTED:'Nghiệm thu',INVOICED:'Đã xuất HĐ',PARTIALLY_PAID:'Thu một phần',PAID:'Thu đủ',CLOSED:'Hoàn tất'}

export function OrderFlowPage(){
  const[orders,setOrders]=useState<any[]>([]),[selected,setSelected]=useState<any>(null),[master,setMaster]=useState<any>({products:[],users:[],opportunities:[]})
  const[tab,setTab]=useState<'orders'|'technical'>('orders'),[surveys,setSurveys]=useState<any[]>([]),[boms,setBoms]=useState<any[]>([])
  const[modal,setModal]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  const fail=(e:any)=>setError(typeof e?.response?.data?.detail==='string'?e.response.data.detail:e?.response?.data?.detail?.message||'Không thể xử lý yêu cầu')
  const load=async()=>{const[o,m,s,b]=await Promise.all([api.get('/order-flow/orders'),api.get('/order-flow/master-data'),api.get('/order-flow/surveys'),api.get('/order-flow/boms')]);setOrders(o.data);setMaster(m.data);setSurveys(s.data);setBoms(b.data)}
  const open=async(id:number)=>{try{setSelected((await api.get(`/order-flow/orders/${id}/workspace`)).data)}catch(e){fail(e)}}
  useEffect(()=>{load().catch(fail)},[])
  const act=async(path:string)=>{setBusy(true);setError('');try{await api.post(path);await load();if(selected)await open(selected.order.id)}catch(e){fail(e)}finally{setBusy(false)}}
  const save=async(e:React.FormEvent<HTMLFormElement>)=>{e.preventDefault();setBusy(true);const x:any=Object.fromEntries(new FormData(e.currentTarget));['product_id','quantity','unit_price','manager_id','opportunity_id','engineer_id','amount_before_vat','vat_amount','receivable_id','amount'].forEach(k=>{if(x[k])x[k]=Number(x[k]);else delete x[k]});try{
    const orderId=selected?.order?.id
    const urls:any={item:`/order-flow/orders/${orderId}/items`,project:`/order-flow/orders/${orderId}/project`,invoice:`/order-flow/orders/${orderId}/invoice`,receipt:`/order-flow/orders/${orderId}/receipts`,survey:'/order-flow/surveys'}
    await api.post(urls[modal],x);setModal('');await load();if(orderId)await open(orderId)
  }catch(e){fail(e)}finally{setBusy(false)}}
  const workflowAction=()=>{
    if(!selected)return null;const o=selected.order
    if(o.status==='DRAFT')return <button onClick={()=>act(`/order-flow/orders/${o.id}/confirm`)}>Xác nhận đơn</button>
    if(o.status==='WAITING_INVENTORY')return selected.inventory_ready?<button onClick={()=>act(`/order-flow/orders/${o.id}/reserve`)}>Giữ hàng</button>:<button onClick={()=>act(`/order-flow/orders/${o.id}/create-purchase-requests`)}>Tạo yêu cầu mua phần thiếu</button>
    if(o.status==='READY_FOR_DELIVERY')return <button onClick={()=>act(`/order-flow/orders/${o.id}/issue`)}>Xuất kho triển khai</button>
    if(o.status==='IN_IMPLEMENTATION')return <button onClick={()=>act(`/order-flow/orders/${o.id}/accept`)}>Xác nhận nghiệm thu</button>
    if(o.status==='ACCEPTED')return <button onClick={()=>setModal('invoice')}>Xuất hóa đơn</button>
    if(['INVOICED','PARTIALLY_PAID'].includes(o.status))return <button onClick={()=>setModal('receipt')}>Ghi nhận thu tiền</button>
    if(o.status==='PAID')return <button onClick={()=>act(`/order-flow/orders/${o.id}/close`)}>Đóng đơn hàng</button>
  }
  return <><PageHeader title="Luồng đơn hàng end-to-end" description="Hợp đồng và Sales Order là xương sống kết nối CRM, kho, mua hàng, kỹ thuật, nghiệm thu và công nợ."
    actions={<button className="ghost-btn" onClick={()=>load()}><RefreshCw size={16}/> Làm mới</button>}/>
    {error&&<div className="error-panel"><AlertTriangle size={17}/>{error}<button onClick={()=>setError('')}>×</button></div>}
    <div className="tabs"><button className={tab==='orders'?'active':''} onClick={()=>setTab('orders')}>Order workspace</button><button className={tab==='technical'?'active':''} onClick={()=>setTab('technical')}>Khảo sát & BOM</button></div>
    {tab==='orders'&&<div className="order-layout"><section className="panel order-list"><div className="panel-title"><div><h3>Sales Orders</h3><p>Chọn đơn để điều hành xuyên suốt</p></div></div>{orders.map(o=><button key={o.id} className={`order-row ${selected?.order.id===o.id?'active':''}`} onClick={()=>open(o.id)}><div><b>{o.code}</b><span>{o.title}</span></div><StatusBadge value={o.status}/><small>{money(o.total_amount)} · {o.item_count} dòng hàng</small></button>)}</section>
      <div>{!selected?<section className="panel empty-workspace"><PackageCheck size={44}/><h3>Chọn một đơn hàng</h3><p>Toàn bộ tồn kho, triển khai và công nợ sẽ hiển thị tại đây.</p></section>:<>
        <section className="panel"><div className="order-head"><div><span>{selected.customer.name}</span><h2>{selected.order.code} · {selected.order.title}</h2><p>{selected.contract?`Hợp đồng ${selected.contract.code}`:'Đơn chưa liên kết hợp đồng'} {selected.project?`· Project ${selected.project.code}`:'· Chưa tạo Project'}</p></div><StatusBadge value={selected.order.status}/></div>
          <div className="flow-steps">{stages.map((s,i)=>{const current=stages.indexOf(selected.order.status),done=i<=current;return <div className={done?'done':''} key={s}>{done?<CheckCircle2/>:<Circle/>}<span>{stageLabel[s]}</span></div>})}</div>
          <div className="workspace-actions">{selected.order.status==='DRAFT'&&<button className="ghost-btn" onClick={()=>setModal('item')}><Plus size={15}/> Dòng hàng</button>}{!selected.project&&selected.order.status!=='DRAFT'&&<button className="ghost-btn" onClick={()=>setModal('project')}><Plus size={15}/> Tạo Project</button>}<span/>{workflowAction()}</div>
        </section>
        <div className="workspace-grid"><section className="panel"><div className="panel-title"><div><h3>Kho & mua hàng</h3><p>{selected.inventory_ready?'Đủ hàng để giữ chỗ':'Có mặt hàng cần mua bổ sung'}</p></div></div><DataTable rows={selected.inventory} columns={[{key:'sku',label:'SKU'},{key:'name',label:'Sản phẩm'},{key:'quantity',label:'SL đơn'},{key:'available',label:'Khả dụng'},{key:'reserved_for_order',label:'Đã giữ'},{key:'shortage',label:'Thiếu',render:(r:any)=><b className={r.shortage?'danger-text':''}>{r.shortage}</b>}]}/></section>
          <section className="panel"><div className="panel-title"><div><h3>Kỹ thuật & nghiệm thu</h3><p>{selected.work_orders.length} work order · {selected.acceptances.length} biên bản</p></div></div>{selected.work_orders.map((w:any)=><div className="mini-record" key={w.id}><div><b>{w.code}</b><span>{w.title}</span></div><StatusBadge value={w.status}/></div>)}{!selected.work_orders.length&&<p className="empty">Chưa có work order</p>}</section>
          <section className="panel"><div className="panel-title"><div><h3>Hóa đơn & công nợ</h3><p>Theo dõi thu tiền theo từng hóa đơn</p></div></div>{selected.receivables.map((r:any)=><div className="debt-row" key={r.id}><div><b>{r.invoice_no}</b><span>Hạn {date(r.due_date)}</span></div><div><b>{money(r.paid_amount)} / {money(r.amount)}</b><StatusBadge value={r.status}/></div></div>)}{!selected.receivables.length&&<p className="empty">Chưa phát hành hóa đơn</p>}</section>
          <section className="panel"><div className="panel-title"><div><h3>Nhật ký đơn hàng</h3><p>Audit trail theo thời gian</p></div></div><div className="timeline">{selected.events.map((e:any)=><div key={e.id}><i/><div><b>{e.title}</b><span>{e.details||e.event_type}</span><small>{new Date(e.created_at).toLocaleString('vi-VN')}</small></div></div>)}</div></section>
        </div></>}</div></div>}
    {tab==='technical'&&<div className="workspace-grid"><section className="panel"><div className="panel-title"><div><h3>Khảo sát kỹ thuật</h3><p>Đầu vào cho giải pháp và báo giá</p></div><button className="primary-btn small" onClick={()=>setModal('survey')}><Plus size={15}/> Khảo sát</button></div><DataTable rows={surveys} columns={[{key:'code',label:'Mã'},{key:'opportunity_id',label:'Opportunity'},{key:'location',label:'Địa điểm'},{key:'requirements',label:'Nhu cầu'},{key:'survey_date',label:'Ngày',render:(r:any)=>date(r.survey_date)},{key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>}]}/></section>
      <section className="panel"><div className="panel-title"><div><h3>BOM / Giải pháp</h3><p>Danh mục vật tư phục vụ báo giá</p></div></div><DataTable rows={boms} columns={[{key:'code',label:'Mã BOM'},{key:'name',label:'Tên giải pháp'},{key:'opportunity_id',label:'Opportunity'},{key:'items',label:'Số dòng',render:(r:any)=>r.items.length},{key:'status',label:'Trạng thái',render:(r:any)=><StatusBadge value={r.status}/>}]}/></section></div>}
    {modal&&<div className="modal-backdrop" onMouseDown={()=>setModal('')}><form className="modal" onSubmit={save} onMouseDown={e=>e.stopPropagation()}><h3>{modal==='item'?'Thêm dòng hàng':modal==='project'?'Tạo Project':modal==='invoice'?'Phát hành hóa đơn':modal==='receipt'?'Ghi nhận thu tiền':'Tạo khảo sát kỹ thuật'}</h3><div className="form-grid">
      {modal==='item'&&<><label className="full">Sản phẩm<select name="product_id" required>{master.products.map((p:any)=><option key={p.id} value={p.id}>{p.sku} · {p.name} · tồn {p.quantity_on_hand}</option>)}</select></label><label>Số lượng<input name="quantity" type="number" min="1" required/></label><label>Đơn giá<input name="unit_price" type="number" min="0" required/></label></>}
      {modal==='project'&&<><label>Mã Project<input name="code" required/></label><label>Quản lý<select name="manager_id"><option value="">Chưa phân công</option>{master.users.map((u:any)=><option value={u.id}>{u.full_name} · {u.role}</option>)}</select></label><label>Ngày bắt đầu<input name="start_date" type="date"/></label><label>Hạn hoàn thành<input name="due_date" type="date"/></label></>}
      {modal==='invoice'&&<><label>Số hóa đơn<input name="invoice_no" required/></label><label>Hạn thanh toán<input name="due_date" type="date" required/></label><label>Trước VAT<input name="amount_before_vat" type="number" min="1" required defaultValue={selected.order.total_amount}/></label><label>VAT<input name="vat_amount" type="number" min="0" defaultValue="0"/></label></>}
      {modal==='receipt'&&<><label>Khoản phải thu<select name="receivable_id" required>{selected.receivables.filter((r:any)=>r.status!=='PAID').map((r:any)=><option value={r.id}>{r.invoice_no} · còn {money(r.amount-r.paid_amount)}</option>)}</select></label><label>Mã phiếu thu<input name="code" required/></label><label>Số tiền<input name="amount" type="number" min="1" required/></label><label>Ngày thu<input name="received_date" type="date" required/></label><label>Phương thức<select name="method"><option value="BANK_TRANSFER">Chuyển khoản</option><option value="CASH">Tiền mặt</option></select></label><label>Mã giao dịch<input name="transaction_ref"/></label></>}
      {modal==='survey'&&<><label>Mã khảo sát<input name="code" required/></label><label>Opportunity<select name="opportunity_id">{master.opportunities.map((o:any)=><option value={o.id}>{o.code} · {o.title}</option>)}</select></label><label className="full">Địa điểm<input name="location"/></label><label className="full">Nhu cầu/hiện trạng<textarea name="requirements" required/></label><label>Ngày khảo sát<input name="survey_date" type="date"/></label><label>Kỹ sư<select name="engineer_id"><option value="">Chưa phân công</option>{master.users.map((u:any)=><option value={u.id}>{u.full_name}</option>)}</select></label></>}
    </div><div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setModal('')}>Hủy</button><button className="primary-btn" disabled={busy}>{busy?'Đang xử lý…':'Lưu'}</button></div></form></div>}
  </>
}
