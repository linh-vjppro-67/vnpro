export type User = {
  id: number; email: string; full_name: string; role: string; department: string; is_active: boolean
}
export type Dashboard = {
  revenue: number; gross_profit: number; pipeline_value: number; open_receivables: number; overdue_receivables: number;
  approved_budget: number; spent_budget: number; active_projects: number; open_tickets: number; low_stock_products: number;
  monthly_revenue: {month: string; value: number}[];
  sales_funnel: {stage: string; count: number; value: number}[];
  expense_by_category: {category: string; value: number}[];
  alerts: {level: string; title: string; message: string}[];
}
