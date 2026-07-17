import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './components/AuthContext'
import { Layout } from './components/Layout'

const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })))
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })))
const SalesPage = lazy(() => import('./pages/SalesPage').then(m => ({ default: m.SalesPage })))
const TasksPage = lazy(() => import('./pages/TasksPage').then(m => ({ default: m.TasksPage })))
const CostsPage = lazy(() => import('./pages/CostsPage').then(m => ({ default: m.CostsPage })))
const OperationsPage = lazy(() => import('./pages/OperationsPage').then(m => ({ default: m.OperationsPage })))
const InventoryPage = lazy(() => import('./pages/InventoryPage').then(m => ({ default: m.InventoryPage })))
const FinancePage = lazy(() => import('./pages/FinancePage').then(m => ({ default: m.FinancePage })))
const SupportPage = lazy(() => import('./pages/SupportPage').then(m => ({ default: m.SupportPage })))
const OrganizationPage = lazy(() => import('./pages/OrganizationPage').then(m => ({ default: m.OrganizationPage })))

function Protected(){const{user}=useAuth();return user?<Layout/>:<Navigate to="/login" replace/>}
export default function App(){return <Suspense fallback={<div className="loading">Đang tải ứng dụng…</div>}><Routes><Route path="/login" element={<LoginPage/>}/><Route element={<Protected/>}><Route index element={<DashboardPage/>}/><Route path="sales" element={<SalesPage/>}/><Route path="tasks" element={<TasksPage/>}/><Route path="costs" element={<CostsPage/>}/><Route path="operations" element={<OperationsPage/>}/><Route path="inventory" element={<InventoryPage/>}/><Route path="finance" element={<FinancePage/>}/><Route path="support" element={<SupportPage/>}/><Route path="organization" element={<OrganizationPage/>}/></Route><Route path="*" element={<Navigate to="/" replace/>}/></Routes></Suspense>}
