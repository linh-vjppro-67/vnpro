import { useEffect, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { api } from '../lib/api'
import { money, number } from '../lib/format'
import { PageHeader } from '../components/PageHeader'
import { DataTable } from '../components/DataTable'
import { SuppliersTab } from './inventory/SuppliersTab'
import { PurchaseRequestsTab } from './inventory/PurchaseRequestsTab'
import { PurchaseOrdersTab } from './inventory/PurchaseOrdersTab'
import { ReservationsTab } from './inventory/ReservationsTab'
import { GoodsReceiptsTab } from './inventory/GoodsReceiptsTab'

export function InventoryPage(){
  const [tab,setTab]=useState<'stock'|'suppliers'|'requests'|'orders'|'receipts'|'reservations'>('stock')
  const [rows,setRows]=useState<any[]>([]); const [suppliers,setSuppliers]=useState<any[]>([]); const [salesOrders,setSalesOrders]=useState<any[]>([])
  const [selected,setSelected]=useState<any|null>(null)
  const load=()=>api.get('/inventory/products').then(r=>setRows(r.data))
  const loadShared=()=>{ load(); api.get('/purchasing/suppliers').then(r=>setSuppliers(r.data)); api.get('/sales/orders').then(r=>setSalesOrders(r.data)) }
  useEffect(()=>{loadShared()},[])
  const move=async(e:React.FormEvent<HTMLFormElement>)=>{e.preventDefault();const f=new FormData(e.currentTarget);await api.post('/inventory/movements',{product_id:selected.id,movement_type:f.get('movement_type'),quantity:Number(f.get('quantity')),reference:f.get('reference'),note:f.get('note')});setSelected(null);load()}
  return <><PageHeader title="Quản lý kho" description="Kiểm soát nhập, xuất, tồn, mua hàng và giữ hàng theo định mức."/>
    <div className="tabs">
      <button className={tab==='stock'?'active':''} onClick={()=>setTab('stock')}>Tồn kho</button>
      <button className={tab==='suppliers'?'active':''} onClick={()=>setTab('suppliers')}>Nhà cung cấp</button>
      <button className={tab==='requests'?'active':''} onClick={()=>setTab('requests')}>Yêu cầu mua hàng</button>
      <button className={tab==='orders'?'active':''} onClick={()=>setTab('orders')}>Đơn mua hàng</button>
      <button className={tab==='receipts'?'active':''} onClick={()=>setTab('receipts')}>Kiểm nhận & nhập kho</button>
      <button className={tab==='reservations'?'active':''} onClick={()=>setTab('reservations')}>Giữ hàng</button>
    </div>
    {tab==='stock' && <>
      <div className="inventory-summary"><div><b>{rows.length}</b><span>Mã sản phẩm</span></div><div><b>{number(rows.reduce((s,r)=>s+r.quantity_on_hand,0))}</b><span>Tổng số lượng tồn</span></div><div className="warn"><b>{rows.filter(r=>r.quantity_on_hand<=r.min_stock).length}</b><span>Dưới định mức</span></div></div>
      <section className="panel"><DataTable rows={rows} columns={[
        {key:'sku',label:'SKU'}, {key:'name',label:'Tên hàng'}, {key:'category',label:'Nhóm'}, {key:'quantity_on_hand',label:'Tồn kho',render:(r:any)=><span className={r.quantity_on_hand<=r.min_stock?'stock-low':''}>{r.quantity_on_hand} {r.unit}{r.quantity_on_hand<=r.min_stock&&<AlertTriangle size={15}/>}</span>}, {key:'reserved_quantity',label:'Đã giữ'}, {key:'min_stock',label:'Định mức'}, {key:'cost_price',label:'Giá vốn',render:(r:any)=>money(r.cost_price)}, {key:'action',label:'Thao tác',render:(r:any)=><button className="table-btn" onClick={()=>setSelected(r)}>Nhập/Xuất</button>}
      ]}/></section>
    </>}
    {tab==='suppliers' && <SuppliersTab/>}
    {tab==='requests' && <PurchaseRequestsTab products={rows} suppliers={suppliers} onChange={load}/>}
    {tab==='orders' && <PurchaseOrdersTab products={rows} suppliers={suppliers} onChange={load}/>}
    {tab==='receipts' && <GoodsReceiptsTab products={rows} onChange={loadShared}/>}
    {tab==='reservations' && <ReservationsTab products={rows} salesOrders={salesOrders} onChange={load}/>}
    {selected&&<div className="modal-backdrop" onMouseDown={()=>setSelected(null)}><form className="modal" onSubmit={move} onMouseDown={e=>e.stopPropagation()}><h3>Điều chỉnh kho · {selected.sku}</h3><p>{selected.name} · Hiện có <b>{selected.quantity_on_hand}</b> {selected.unit}</p><div className="form-grid"><label>Loại giao dịch<select name="movement_type"><option value="IN">Nhập kho</option><option value="OUT">Xuất kho</option><option value="ADJUST">Kiểm kê/Điều chỉnh</option></select></label><label>Số lượng<input name="quantity" type="number" min="1" required/></label><label>Mã tham chiếu<input name="reference" placeholder="DH-2026-041"/></label><label className="full">Ghi chú<input name="note"/></label></div><div className="modal-actions"><button type="button" className="ghost-btn" onClick={()=>setSelected(null)}>Hủy</button><button className="primary-btn">Cập nhật tồn kho</button></div></form></div>}
  </>
}
