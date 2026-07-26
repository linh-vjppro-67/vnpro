import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { money, date } from '../lib/format'
import { PageHeader } from '../components/PageHeader'
import { StatusBadge } from '../components/StatusBadge'
import { WorkOrdersTab } from './operations/WorkOrdersTab'
import { AcceptanceRecordsTab } from './operations/AcceptanceRecordsTab'
import { TechnicalRequestsTab } from './operations/TechnicalRequestsTab'
import { BomsTab } from './operations/BomsTab'

export function OperationsPage(){
  const [tab,setTab]=useState<'technical-requests'|'boms'|'projects'|'work-orders'|'acceptance'>('technical-requests')
  const [rows,setRows]=useState<any[]>([]); const [workOrders,setWorkOrders]=useState<any[]>([])
  const loadProjects = () => api.get('/operations/projects').then(r=>setRows(r.data))
  const loadWorkOrders = () => api.get('/operations/work-orders').then(r=>setWorkOrders(r.data))
  useEffect(()=>{ loadProjects(); loadWorkOrders() },[])
  return <><PageHeader title="Vận hành kỹ thuật" description="Theo dõi khảo sát, thiết kế, lắp đặt, nghiệm thu và hồ sơ kỹ thuật theo từng dự án."/>
    <div className="tabs">
      <button className={tab==='technical-requests'?'active':''} onClick={()=>setTab('technical-requests')}>Yêu cầu kỹ thuật</button>
      <button className={tab==='boms'?'active':''} onClick={()=>setTab('boms')}>BOM / Giải pháp</button>
      <button className={tab==='projects'?'active':''} onClick={()=>setTab('projects')}>Dự án</button>
      <button className={tab==='work-orders'?'active':''} onClick={()=>setTab('work-orders')}>Work order</button>
      <button className={tab==='acceptance'?'active':''} onClick={()=>setTab('acceptance')}>Nghiệm thu</button>
    </div>
    {tab==='technical-requests' && <TechnicalRequestsTab/>}
    {tab==='boms' && <BomsTab/>}
    {tab==='projects' && <div className="project-grid">{rows.map(p=><article className="project-card" key={p.id}><div className="project-head"><div><span>{p.code}</span><h3>{p.name}</h3></div><StatusBadge value={p.status}/></div><div className="project-meta"><span>Bắt đầu <b>{date(p.start_date)}</b></span><span>Hạn hoàn thành <b>{date(p.due_date)}</b></span></div><div className="project-progress"><div><span>Tiến độ</span><b>{p.progress}%</b></div><div className="progress"><i style={{width:`${p.progress}%`}}/></div></div><div className="project-finance"><div><span>Ngân sách</span><b>{money(p.budget_amount)}</b></div><div><span>Chi phí thực tế</span><b>{money(p.actual_cost)}</b></div><div><span>Còn lại</span><b>{money(Number(p.budget_amount)-Number(p.actual_cost))}</b></div></div></article>)}</div>}
    {tab==='work-orders' && <WorkOrdersTab projects={rows} onChange={loadWorkOrders}/>}
    {tab==='acceptance' && <AcceptanceRecordsTab workOrders={workOrders}/>}
  </>
}
