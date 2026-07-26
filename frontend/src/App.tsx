import { lazy, Suspense, type ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './components/AuthContext'
import { Layout } from './components/Layout'
import { can } from './lib/permissions'

const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })))
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })))
const SalesPage = lazy(() => import('./pages/SalesPage').then(m => ({ default: m.SalesPage })))
const TasksPage = lazy(() => import('./pages/TasksPage').then(m => ({ default: m.TasksPage })))
const CostsPage = lazy(() => import('./pages/CostsPage').then(m => ({ default: m.CostsPage })))
const OrderFlowPage = lazy(() => import('./pages/OrderFlowPage').then(m => ({ default: m.OrderFlowPage })))
const OperationsPage = lazy(() => import('./pages/OperationsPage').then(m => ({ default: m.OperationsPage })))
const InventoryPage = lazy(() => import('./pages/InventoryPage').then(m => ({ default: m.InventoryPage })))
const FinancePage = lazy(() => import('./pages/FinancePage').then(m => ({ default: m.FinancePage })))
const SupportPage = lazy(() => import('./pages/SupportPage').then(m => ({ default: m.SupportPage })))
const OrganizationPage = lazy(() => import('./pages/OrganizationPage').then(m => ({ default: m.OrganizationPage })))

function Protected(){const{user,loading}=useAuth();if(loading)return <div className="loading">Đang xác thực…</div>;return user?<Layout/>:<Navigate to="/login" replace/>}
function Allowed({permission,children}:{permission:string;children:ReactNode}){const{user}=useAuth();return can(user?.role,permission)?children:<Navigate to="/" replace/>}
export default function App(){return <Suspense fallback={<div className="loading">Đang tải ứng dụng…</div>}><Routes><Route path="/login" element={<LoginPage/>}/><Route element={<Protected/>}><Route index element={<DashboardPage/>}/><Route path="order-flow" element={<Allowed permission="sales:r"><OrderFlowPage/></Allowed>}/><Route path="sales" element={<Allowed permission="sales:r"><SalesPage/></Allowed>}/><Route path="tasks" element={<TasksPage/>}/><Route path="costs" element={<Allowed permission="cost:r"><CostsPage/></Allowed>}/><Route path="operations" element={<Allowed permission="operations:r"><OperationsPage/></Allowed>}/><Route path="inventory" element={<Allowed permission="inventory:r"><InventoryPage/></Allowed>}/><Route path="finance" element={<Allowed permission="finance:r"><FinancePage/></Allowed>}/><Route path="support" element={<Allowed permission="support:r"><SupportPage/></Allowed>}/><Route path="organization" element={<Allowed permission="organization"><OrganizationPage/></Allowed>}/></Route><Route path="*" element={<Navigate to="/" replace/>}/></Routes></Suspense>}
