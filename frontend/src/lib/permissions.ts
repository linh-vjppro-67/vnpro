const rolePermissions: Record<string, string[]> = {
  SYSTEM_ADMIN: ['*'], DIRECTOR: ['*'],
  DIRECTOR_ASSISTANT: ['dashboard','sales:r','cost:r','operations:r','inventory:r','finance:r','support:r','organization'],
  MARKETING: ['dashboard','sales:r','sales:w'],
  SALES: ['dashboard','sales:r','sales:w','operations:r','inventory:r','finance:r','support:r','support:w'],
  SALES_ADMIN: ['dashboard','sales:r','sales:w','operations:r','operations:w','inventory:r','finance:r','support:r'],
  TECH_SOLUTION: ['dashboard','sales:r','operations:r','operations:w','inventory:r','purchasing:r','purchasing:w','support:r','support:w'],
  TECH_FIELD: ['dashboard','operations:r','operations:w','inventory:r','purchasing:r','support:r','support:w'],
  ACCOUNTING: ['dashboard','sales:r','cost:r','cost:w','operations:r','inventory:r','purchasing:r','finance:r','finance:w'],
  PURCHASING: ['dashboard','sales:r','cost:r','cost:w','operations:r','inventory:r','inventory:w','purchasing:r','purchasing:w'],
  WAREHOUSE: ['dashboard','sales:r','operations:r','inventory:r','inventory:w','purchasing:r','purchasing:w'],
  CASHIER: ['dashboard','cost:r','finance:r','finance:w'],
  HCVP: ['dashboard','cost:r','cost:w','inventory:r','organization'],
  HR: ['dashboard','organization'],
  CUSTOMER_SERVICE: ['dashboard','sales:r','operations:r','support:r','support:w'],
}

export const can = (role: string | undefined, permission: string) => {
  const values = rolePermissions[role || ''] || []
  return values.includes('*') || values.includes(permission)
}
