import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { PageHeader } from '../components/PageHeader'
import { DataTable } from '../components/DataTable'
import { LockKeyhole, LockOpen } from 'lucide-react'

const roleName: Record<string,string>={SYSTEM_ADMIN:'Quản trị hệ thống',DIRECTOR:'Ban giám đốc',DIRECTOR_ASSISTANT:'Trợ lý BGĐ',MARKETING:'Marketing',SALES:'Kinh doanh',SALES_ADMIN:'Sales Admin',TECH_SOLUTION:'Kỹ thuật giải pháp',TECH_FIELD:'Kỹ thuật hiện trường',ACCOUNTING:'Kế toán',PURCHASING:'Mua hàng',WAREHOUSE:'Kho',CASHIER:'Quỹ',HCVP:'Hành chính văn phòng',HR:'Nhân sự',CUSTOMER_SERVICE:'Chăm sóc khách hàng'}
export function OrganizationPage(){const[users,setUsers]=useState<any[]>([]);const[error,setError]=useState('');const[busy,setBusy]=useState<number|null>(null)
const load=()=>api.get('/admin/users').then(u=>setUsers(u.data)).catch(e=>setError(e.response?.data?.detail||'Không thể tải danh sách nhân sự'))
useEffect(()=>{load()},[])
const toggle=async(user:any)=>{const action=user.is_active?'khóa':'mở khóa';if(!confirm(`Bạn có chắc muốn ${action} tài khoản ${user.full_name}?`))return;setBusy(user.id);setError('');try{await api.patch(`/admin/users/${user.id}/active`,{is_active:!user.is_active});await load()}catch(e:any){setError(e.response?.data?.detail||`Không thể ${action} tài khoản`)}finally{setBusy(null)}}
return <><PageHeader title="Tổ chức" description="Danh sách nhân sự, phòng ban và trạng thái tài khoản VNPRO."/>
{error&&<div className="error-panel">{error}</div>}<section className="panel"><div className="panel-title"><div><h3>Danh sách nhân sự</h3><p>Khóa tài khoản sẽ ngăn đăng nhập mới và vô hiệu hóa ngay phiên đang hoạt động.</p></div></div><DataTable rows={users} columns={[{key:'full_name',label:'Họ tên'},{key:'email',label:'Email'},{key:'department',label:'Phòng ban'},{key:'role',label:'Vị trí',render:(r:any)=>roleName[r.role]||r.role},{key:'is_active',label:'Trạng thái',render:(r:any)=><span className={`badge ${r.is_active?'badge-active':'badge-rejected'}`}>{r.is_active?'Hoạt động':'Đã khóa'}</span>},{key:'action',label:'Thao tác',render:(r:any)=><button className="table-btn" disabled={busy===r.id} onClick={()=>toggle(r)}>{r.is_active?<><LockKeyhole size={14}/> Khóa</>:<><LockOpen size={14}/> Mở khóa</>}</button>} ]}/></section></>}
